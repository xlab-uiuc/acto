import sys
import logging
from deepdiff import DeepDiff
import re
import copy
import operator
from functools import reduce

from common import *
from compare import CompareMethods
from snapshot import EmptySnapshot, Snapshot
from parse_log.parse_log import parse_log


class Checker(object):

    def __init__(self, context: dict, trial_dir: str) -> None:
        self.context = context
        self.namespace = context['namespace']
        self.compare_method = CompareMethods()
        self.trial_dir = trial_dir

        # logging.debug(self.context['analysis_result']['paths'])

    def check(self, snapshot: Snapshot, prev_snapshot: Snapshot, generation: int) -> RunResult:
        '''Use acto oracles against the results to check for any errors

        Args:        
            result: includes the path to result files

        Returns:
            RunResult of the checking
        '''
        if snapshot.system_state == {}:
            return InvalidInputResult()
            
        self.delta_log_path = "%s/delta-%d.log" % (self.trial_dir, generation)

        input_result = self.check_input(snapshot)
        if not isinstance(input_result, PassResult):
            return input_result

        state_result = self.check_resources(snapshot, prev_snapshot)
        log_result = self.check_operator_log(snapshot, prev_snapshot)

        if isinstance(log_result, InvalidInputResult):
            logging.info('Invalid input, skip this case')
            return log_result
        if isinstance(state_result, ErrorResult):
            logging.info('Report error from system state oracle')
            return state_result
        elif isinstance(log_result, ErrorResult):
            logging.info('Report error from operator log oracle')
            return log_result

        return PassResult()

    def check_input(self, snapshot: Snapshot) -> RunResult:
        stdout, stderr = snapshot.cli_result['stdout'], snapshot.cli_result['stderr']

        if stderr.find('connection refused') != -1:
            return ConnectionRefusedResult()

        elif stdout.find('error') != -1 or stderr.find('error') != -1 or stderr.find(
                'invalid') != -1:
            logging.info('Invalid input, reject mutation')
            logging.info('STDOUT: ' + stdout)
            logging.info('STDERR: ' + stderr)
            return InvalidInputResult()

        if stdout.find('unchanged') != -1 or stderr.find('unchanged') != -1:
            logging.info('CR unchanged, continue')
            return UnchangedInputResult()

        return PassResult()

    def check_resources(self, snapshot: Snapshot, prev_snapshot: Snapshot) -> RunResult:
        '''
        System state oracle

        For each delta in the input, find the longest matching fields in the system state.
        Then compare the the delta values (prev, curr).

        Args:
            result - includes the path to delta log files

        Returns:
            RunResult of the checking
        '''
        input_delta, system_delta = self.get_deltas(snapshot, prev_snapshot)

        with open(self.delta_log_path, 'w') as f:
            f.write('---------- INPUT DELTA  ----------\n')
            f.write(json.dumps(input_delta, cls=ActoEncoder, indent=6))
            f.write('\n---------- SYSTEM DELTA ----------\n')
            f.write(json.dumps(system_delta, cls=ActoEncoder, indent=6))

        # cr_spec_diff is same as input delta, so it is excluded
        system_delta_without_cr = copy.deepcopy(system_delta)
        system_delta_without_cr.pop('custom_resource_spec')

        for delta_list in input_delta.values():
            for delta in delta_list.values():
                if self.compare_method.input_compare(delta.prev, delta.curr):
                    # if the input delta is considered as equivalent, skip
                    continue

                if self.context['enable_analysis'] and self.should_skip_input_delta(delta, snapshot):
                    continue

                # Find the longest matching field, compare the delta change
                match_deltas = self._list_matched_fields(delta.path, system_delta_without_cr)

                # TODO: should the delta match be inclusive?
                for match_delta in match_deltas:
                    logging.debug('Input delta [%s] matched with [%s]' %
                                  (delta.path, match_delta.path))
                    if not self.compare_method.compare(delta.prev, delta.curr, match_delta.prev,
                                                       match_delta.curr):
                        logging.error('Matched delta inconsistent with input delta')
                        logging.error('Input delta: %s -> %s' % (delta.prev, delta.curr))
                        logging.error('Matched delta: %s -> %s' %
                                      (match_delta.prev, match_delta.curr))
                        return ErrorResult(Oracle.SYSTEM_STATE,
                                           'Matched delta inconsistent with input delta', delta,
                                           match_delta)

                if len(match_deltas) == 0:
                    # if prev and curr of the delta are the same, also consider it as a match
                    found = False
                    for resource_delta_list in system_delta_without_cr.values():
                        for type_delta_list in resource_delta_list.values():
                            for state_delta in type_delta_list.values():
                                if self.compare_method.compare(delta.prev, delta.curr,
                                                               state_delta.prev, state_delta.curr):
                                    found = True
                    if found:
                        continue
                    logging.error('Found no matching fields for input delta')
                    logging.error('Input delta [%s]' % delta.path)
                    return ErrorResult(Oracle.SYSTEM_STATE, 'Found no matching fields for input',
                                       delta)
        return PassResult()

    def should_skip_input_delta(self, input_delta: Diff, snapshot: Snapshot) -> bool:
        '''Determines if the input delta should be skipped or not
        
        Args:
            input_delta
            
        Returns:
            if the arg input_delta should be skipped in oracle
        '''

        if 'analysis_result' not in self.context:
            return False

        control_flow_fields = self.context['analysis_result']['control_flow_fields']
        for control_flow_field in control_flow_fields:
            if len(input_delta.path) == len(control_flow_field):
                not_match = False
                for i in range(len(input_delta.path)):
                    if control_flow_field[i] == 'INDEX' and re.match(r"^\d$",
                                                                     str(input_delta.path[i])):
                        continue
                    elif input_delta.path[i] != control_flow_field[i]:
                        not_match = True
                        break
                if not_match:
                    continue
                else:
                    return True

        # dependency checking
        field_conditions_map = self.context['analysis_result']['field_conditions_map']
        encoded_path = json.dumps(input_delta.path)
        if encoded_path in field_conditions_map:
            conditions = field_conditions_map[encoded_path]
            for condition in conditions:
                if not self.check_condition(snapshot.input, condition):
                    # if one condition does not satisfy, skip this testcase
                    return True

        return False

    def check_condition(self, input: dict, condition: dict) -> bool:
        path = condition['field']

        try:
            value = reduce(operator.getitem, path, input)
        except KeyError as e:
            if translate_op(condition['op']) == operator.eq and condition['value'] == None:
                return True
            else:
                return False

        return translate_op(condition['op'])(value, condition['value'])

    def check_operator_log(self, snapshot: Snapshot, prev_snapshot: Snapshot) -> RunResult:
        '''Check the operator log for error msg
        
        Args:
            result - includes the path to delta log files

        Returns:
            RunResult of the checking
        '''
        input_delta, _ = self.get_deltas(snapshot, prev_snapshot)
        log = snapshot.operator_log

        for line in log:
            # We do not check the log line if it is not an error/fatal message

            parsed_log = parse_log(line)
            if parsed_log == {} or parsed_log['level'] != 'error' and parsed_log['level'] != 'fatal':
                continue
            
            # List all the values in parsed_log
            for value in list(parsed_log.values()):
                if type(value) != str or value == '':
                    continue
                if invalid_input_message(value, input_delta):
                    return InvalidInputResult()

            skip = False
            for regex in EXCLUDE_ERROR_REGEX:
                if re.search(regex, line, re.IGNORECASE):
                    skip = True
                    break
            if skip:
                continue

            # logging.error('Found error in operator log')
            # return ErrorResult(Oracle.ERROR_LOG, line)
        return PassResult()

    def check_health(self) -> RunResult:
        '''System health oracle'''
        # TODO: Add other resources, e.g. deployment
        for sts in self.resources['stateful_set'].values():
            desired_replicas = sts['status']['replicas']
            if 'ready_replicas' not in sts['status']:
                logging.error('StatefulSet unhealthy ready replicas None')
                return None  # TODO
            available_replicas = sts['status']['ready_replicas']
            if desired_replicas != available_replicas:
                logging.error(
                    'StatefulSet unhealthy desired replicas [%s] available replicas [%s]' %
                    (desired_replicas, available_replicas))
                return None  # TODO
        return PassResult()

    def check_events_log(self, snapshot: Snapshot) -> RunResult:
        pass

    def _list_matched_fields(self, path: list, delta_dict: dict) -> list:
        '''Search through the entire system delta to find longest matching field
        
        Args:
            path: path of input delta as list
            delta_dict: dict of system delta

        Returns:
            list of system delta with longest matching field path with input delta
        '''
        # if the name of the field is generic, don't match using the path
        for regex in GENERIC_FIELDS:
            if re.search(regex, str(path[-1])):
                return []

        results = []
        max_match = 0
        for resource_delta_list in delta_dict.values():
            for type_delta_list in resource_delta_list.values():
                for delta in type_delta_list.values():
                    position = 0
                    while canonicalize(path[-position - 1]) == canonicalize(delta.path[-position -
                                                                                       1]):
                        position += 1
                        if position == min(len(path), len(delta.path)):
                            break
                    if position == max_match and position != 0:
                        results.append(delta)
                    elif position > max_match:
                        results = [delta]
                        max_match = position
                    else:
                        pass

        return results

    def get_deltas(self, snapshot: Snapshot, prev_snapshot: Snapshot):
        curr_input, curr_system_state = snapshot.input, snapshot.system_state
        prev_input, prev_system_state = prev_snapshot.input, prev_snapshot.system_state

        input_delta = postprocess_diff(
            DeepDiff(prev_input, curr_input, ignore_order=True, report_repetition=True,
                     view='tree'))

        system_state_delta = {}
        for resource in curr_system_state:
            if resource not in prev_system_state:
                prev_system_state[resource] = {}
            system_state_delta[resource] = postprocess_diff(
                DeepDiff(prev_system_state[resource],
                         curr_system_state[resource],
                         exclude_regex_paths=EXCLUDE_PATH_REGEX,
                         report_repetition=True,
                         view='tree'))

        return input_delta, system_state_delta


if __name__ == "__main__":
    import glob
    import os
    import yaml
    import traceback
    import argparse

    parser = argparse.ArgumentParser(description='Standalone checker for Acto')

    parser.add_argument('--context', dest='context', required=True)
    parser.add_argument('--testrun-dir', dest='testrun_dir', required=True)
    parser.add_argument('--seed', dest='seed', required=True)
    args = parser.parse_args()

    logging.basicConfig(
        filename=os.path.join('.', 'test.log'),
        level=logging.DEBUG,
        filemode='w',
        format=
        '%(asctime)s %(threadName)-11s %(levelname)-7s, %(name)s, %(filename)-9s:%(lineno)d, %(message)s'
    )

    def handle_excepthook(type, message, stack):
        '''Custom exception handler

        Print detailed stack information with local variables
        '''
        if issubclass(type, KeyboardInterrupt):
            sys.__excepthook__(type, message, stack)
            return

        stack_info = traceback.StackSummary.extract(traceback.walk_tb(stack),
                                                    capture_locals=True).format()
        logging.critical(f'An exception occured: {type}: {message}.')
        for i in stack_info:
            logging.critical(i.encode().decode('unicode-escape'))
        return

    sys.excepthook = handle_excepthook

    trial_dirs = glob.glob(args.testrun_dir + '/*')
    with open(args.context, 'r') as context_fin:
        context = json.load(context_fin)
        context['preload_images'] = set(context['preload_images'])

    # for path in context['analysis_result']['control_flow_fields']:
    #     path.pop(0)

    context['enable_analysis'] = False

    with open(args.seed, 'r') as seed_file:
        seed = yaml.load(seed_file, Loader=yaml.FullLoader)

    num_alarms = 0

    for trial_dir in sorted(trial_dirs):
        print(trial_dir)
        checker = Checker(context=context, trial_dir=trial_dir)
        snapshots = []
        snapshots.append(EmptySnapshot(seed))

        alarm = False
        for generation in range(0, 10):
            mutated_filename = '%s/mutated-%d.yaml' % (trial_dir, generation)
            operator_log_path = "%s/operator-%d.log" % (trial_dir, generation)
            system_state_path = "%s/system-state-%03d.json" % (trial_dir, generation)
            events_log_path = "%s/events.log" % (trial_dir)
            cli_output_path = "%s/cli-output-%d.log" % (trial_dir, generation)
            field_val_dict_path = "%s/field-val-dict-%d.json" % (trial_dir, generation)

            if not os.path.exists(operator_log_path):
                break

            with open(mutated_filename, 'r') as input_file, \
                open(operator_log_path, 'r') as operator_log, \
                open(system_state_path, 'r') as system_state, \
                open(events_log_path, 'r') as events_log, \
                open(cli_output_path, 'r') as cli_output:
                input = yaml.load(input_file, Loader=yaml.FullLoader)
                cli_result = json.load(cli_output)
                logging.info(cli_result)
                system_state = json.load(system_state)
                operator_log = operator_log.read().splitlines()
                snapshot = Snapshot(input, cli_result, system_state, operator_log)

                result = checker.check(snapshot=snapshot,
                                       prev_snapshot=snapshots[-1],
                                       generation=generation)
                snapshots.append(snapshot)

                if isinstance(result, ConnectionRefusedResult):
                    snapshots.pop()
                    continue
                if isinstance(result, InvalidInputResult):
                    snapshots.pop()
                    continue
                elif isinstance(result, UnchangedInputResult):
                    continue
                elif isinstance(result, ErrorResult):
                    logging.info('%s reports an alarm' % system_state_path)
                    save_result(trial_dir, result, generation, None)
                    num_alarms += 1
                    alarm = True
                elif isinstance(result, PassResult):
                    pass
                else:
                    logging.error('Unknown return value, abort')
                    quit()

        if not alarm:
            logging.info('%s does not report an alarm' % system_state_path)

    logging.info('Number of alarms: %d', num_alarms)

# check file testing
# if __name__ == "__main__":
#     import subprocess
#     import kubernetes

#     testrun_folder = "../testrun-2022-06-02-14-13/"
#     not_present_trial = testrun_folder + "trial-0013"
#     context = {"namespace": "default", \
#         "crd": {"group": "redis.redis.opstreelabs.in", "plural": "redisclusters", "version": "v1beta1"}}
#     cmd = ["ls", "trial-0005"]

#     # Populate the Result, Runner and Checker classes
#     runner = Runner(context)
#     checker = Checker(context)
#     result_0 = Result(context, None, subprocess.run(cmd, capture_output=True, text=True))
#     result_0.setup_path_by_generation(not_present_trial, 0)

#     print("cli functionality test")
#     result_0.collect_cli_output()
#     assert(result_0.get_cli_result()[0] == subprocess.run(cmd, capture_output=True, text=True).stdout)
#     assert(result_0.get_cli_result()[1] == subprocess.run(cmd, capture_output=True, text=True).stderr)
#     # test operator log retrieval
#     print(result_0.get_operator_log())
#     print("cli functionality test passed\n")

#     # test delta retrieval for result without previous result
#     print("delta retrieval test")
#     input_delta, sys_delta = result_0.get_deltas()
#     assert(input_delta == {})

#     result_0.collect_delta()
#     delta_generated = ""
#     delta_original = ""
#     with open("%s/delta-%d.log" % (not_present_trial, 0), 'r') as f:
#         delta_generated = f.readlines()
#     with open("%s/delta-%d-original.log" % (not_present_trial, 0), 'r') as f:
#         delta_original = f.readlines()
#     print(DeepDiff(delta_generated, delta_original))
#     print("delta retrieval test passed\n")

#     print("checker test")
#     # result without previous result should always pass check
#     assert(isinstance(checker.check_resources(result_0), PassResult))
#     assert(isinstance(checker.check_operator_log(result_0), PassResult))
#     assert(isinstance(checker.check_input(result_0), PassResult))
#     assert(isinstance(checker.check(result_0), PassResult))

#     result_1 = Result(context, result_0, subprocess.run(cmd, capture_output=True, text=True))
#     result_1.setup_path_by_generation(not_present_trial, 1)
#     result_1.collect_cli_output()

#     # result for the last trial should pass as well
#     assert(isinstance(checker.check_resources(result_1), PassResult))
#     assert(isinstance(checker.check_operator_log(result_1), PassResult))
#     assert(isinstance(checker.check_input(result_1), PassResult))
#     assert(isinstance(checker.check(result_1), PassResult))

#     print("checker test passed, not present works")

#     # print(result_1.get_deltas())
#     result_1.collect_delta()

#     print("Mimicking Acto run")

#     subprocess.run(["kind", "delete", "cluster"])
#     subprocess.run(["kind", "create", "cluster", "--image", "kindest/node:v1.22.9"])
#     time.sleep(5)
#     subprocess.run(["kubectl", "apply", "-f", "data/redis-ot-container-kit-operator/bundle_f1c547e.yaml"])
#     kubernetes.config.load_kube_config()
#     # time.sleep(25)

#     result_run = Result(context, result_0, runner.run(["kubectl", "apply", "-f", "mutated-1.yaml"]))
#     result_run.setup_path_by_generation(not_present_trial, 1)
#     result_run.collect_cli_output()
#     result_run.collect_events()
#     result_run.collect_system_state()
#     result_run.collect_delta()
#     # result_run.collect_all_result()
#     assert(isinstance(checker.check(result_run), PassResult))
#     print("Mimicking Acto run Passed")
