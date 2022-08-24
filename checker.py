from builtins import TypeError
import sys
import logging
from deepdiff import DeepDiff
import re
import copy
import operator
from functools import reduce

from common import *
from compare import CompareMethods
from input import InputModel
from snapshot import EmptySnapshot, Snapshot
from parse_log.parse_log import parse_log


class Checker(object):

    def __init__(self, context: dict, trial_dir: str, input_model: InputModel) -> None:
        self.context = context
        self.namespace = context['namespace']
        self.compare_method = CompareMethods()
        self.trial_dir = trial_dir
        self.input_model = input_model

        # logging.debug(self.context['analysis_result']['paths'])

    def check(self, snapshot: Snapshot, prev_snapshot: Snapshot, generation: int) -> RunResult:
        '''Use acto oracles against the results to check for any errors

        Args:        
            result: includes the path to result files

        Returns:
            RunResult of the checking
        '''
        if snapshot.system_state == {}:
            return InvalidInputResult(None)

        self.delta_log_path = "%s/delta-%d.log" % (self.trial_dir, generation)
        input_delta, system_delta = self.get_deltas(snapshot, prev_snapshot)
        flattened_system_state = flatten_dict(snapshot.system_state, [])

        num_delta = 0
        for resource_delta_list in system_delta.values():
            for type_delta_list in resource_delta_list.values():
                for state_delta in type_delta_list.values():
                    num_delta += 1
        logging.info('Number of system state fields: [%d] Number of delta: [%d]' %
                     (len(flattened_system_state), num_delta))

        input_result = self.check_input(snapshot, input_delta)
        if not isinstance(input_result, PassResult):
            return input_result

        state_result = self.check_resources(snapshot, prev_snapshot)
        log_result = self.check_operator_log(snapshot, prev_snapshot)

        # XXX: disable health check for now
        # health_result = self.check_health(snapshot)
        health_result = PassResult()

        if isinstance(log_result, InvalidInputResult):
            logging.info('Invalid input, skip this case')
            return log_result

        if isinstance(health_result, ErrorResult):
            logging.info('Report error from system health oracle')
            return health_result
        elif isinstance(state_result, ErrorResult):
            logging.info('Report error from system state oracle')
            return state_result
        elif isinstance(log_result, ErrorResult):
            logging.info('Report error from operator log oracle')
            return log_result

        return PassResult()

    def check_input(self, snapshot: Snapshot, input_delta) -> RunResult:
        stdout, stderr = snapshot.cli_result['stdout'], snapshot.cli_result['stderr']

        if stderr.find('connection refused') != -1:
            return ConnectionRefusedResult()

        is_invalid, reponsible_field_path = invalid_input_message(
            stderr, input_delta)

        # the stderr should indicate the invalid input
        if len(stderr) > 0:
            is_invalid = True

        if is_invalid:
            logging.info('Invalid input, reject mutation')
            logging.info('STDOUT: ' + stdout)
            logging.info('STDERR: ' + stderr)
            return InvalidInputResult(reponsible_field_path)

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

                if self.should_skip_input_delta(delta, snapshot):
                    continue

                # Find the longest matching field, compare the delta change
                match_deltas = self._list_matched_fields(
                    delta.path, system_delta_without_cr)

                # TODO: should the delta match be inclusive?
                for match_delta in match_deltas:
                    logging.debug('Input delta [%s] matched with [%s]' %
                                  (delta.path, match_delta.path))
                    if not self.compare_method.compare(delta.prev, delta.curr, match_delta.prev,
                                                       match_delta.curr):
                        logging.error(
                            'Matched delta inconsistent with input delta')
                        logging.error('Input delta: %s -> %s' %
                                      (delta.prev, delta.curr))
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
        try:
            default_value = self.input_model.get_schema_by_path(
                input_delta.path).default
            if input_delta.prev == default_value and (input_delta.curr == None or isinstance(input_delta.curr, NotPresent)):
                return True
            elif input_delta.curr == default_value and (input_delta.prev == None or isinstance(input_delta.prev, NotPresent)):
                return True
        except Exception as e:
            # print error message
            logging.warn(f"{e} happened when trying to fetch default value")

        if not self.context['enable_analysis']:
            return False

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
                    logging.info(
                        'Field precondition does not satisfy, skip this testcase')
                    return True

        return False

    def check_condition(self, input: dict, condition: dict) -> bool:
        path = condition['field']

        # hack: convert 'INDEX' to int 0
        for i in range(len(path)):
            if path[i] == 'INDEX':
                path[i] = 0

        try:
            value = reduce(operator.getitem, path, input)
        except (KeyError, TypeError) as e:
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
            if parsed_log == {} or parsed_log['level'].lower() != 'error' and parsed_log['level'].lower() != 'fatal':
                continue

            # List all the values in parsed_log
            for value in list(parsed_log.values()):
                if type(value) != str or value == '':
                    continue
                is_invalid, reponsible_field_path = invalid_input_message(
                    value, input_delta)
                if is_invalid:
                    return InvalidInputResult(reponsible_field_path)

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

    def check_health(self, snapshot: Snapshot) -> RunResult:
        '''System health oracle'''

        system_state = snapshot.system_state
        unhealthy_resources = {}

        # check Health of Statefulsets
        unhealthy_resources['statefulset'] = []
        for sfs in system_state['stateful_set'].values():
            if sfs['spec']['replicas'] == sfs['status']['replicas'] and \
                    sfs['status']['replicas'] == sfs['status']['ready_replicas'] and \
                    sfs['status']['current_revision'] == sfs['status']['update_revision']:
                continue
            unhealthy_resources['statefulset'].append(sfs['metadata']['name'])

        # check Health of Deployments
        unhealthy_resources['deployment'] = []
        for dp in system_state['deployment'].values():
            if dp['spec']['replicas'] == 0:
                continue

            if dp['spec']['replicas'] == dp['status']['replicas'] and \
                    dp['status']['replicas'] == dp['status']['ready_replicas'] and \
                    dp['status']['ready_replicas'] == dp['status']['updated_replicas']:
                continue
            unhealthy_resources['deployment'].append(dp['metadata']['name'])

        # check Health of Pods
        unhealthy_resources['pod'] = []
        for pod in system_state['pod'].values():
            if pod['status']['phase'] in ['Running', 'Completed', 'Succeeded']:
                continue
            unhealthy_resources['pod'].append(pod['metadata']['name'])

        error_msg = ''
        for kind, resources in unhealthy_resources.items():
            if len(resources) != 0:
                error_msg += f"{kind}: {', '.join(resources)}\n"
                logging.error(
                    f"Found {kind}: {', '.join(resources)} with unhealthy status")

        if error_msg != '':
            return ErrorResult(Oracle.SYSTEM_HEALTH, error_msg)

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
    from types import SimpleNamespace

    parser = argparse.ArgumentParser(description='Standalone checker for Acto')
    parser.add_argument(
        '--testrun-dir', help='Directory to check', required=True)
    parser.add_argument('--config', help='Path to config file', required=True)

    args = parser.parse_args()

    with open(args.config, 'r') as config_file:
        config = json.load(
            config_file, object_hook=lambda d: SimpleNamespace(**d))
    testrun_dir = args.testrun_dir
    context_cache = os.path.join(os.path.dirname(
        config.seed_custom_resource), 'context.json')

    logging.basicConfig(
        filename=os.path.join('.', 'test.log'),
        level=logging.DEBUG,
        filemode='w',
        format='%(asctime)s %(threadName)-11s %(levelname)-7s, %(name)s, %(filename)-9s:%(lineno)d, %(message)s'
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

    trial_dirs = glob.glob(testrun_dir + '/*')
    with open(context_cache, 'r') as context_fin:
        context = json.load(context_fin)
        context['preload_images'] = set(context['preload_images'])

    for path in context['analysis_result']['control_flow_fields']:
        path.pop(0)

    context['enable_analysis'] = True

    with open(config.seed_custom_resource, 'r') as seed_file:
        seed = yaml.load(seed_file, Loader=yaml.FullLoader)

    num_alarms = 0

    for trial_dir in sorted(trial_dirs):
        print(trial_dir)
        checker = Checker(context=context, trial_dir=trial_dir)
        snapshots = []
        snapshots.append(EmptySnapshot(seed))

        alarm = False
        for generation in range(0, 20):
            mutated_filename = '%s/mutated-%d.yaml' % (trial_dir, generation)
            operator_log_path = "%s/operator-%d.log" % (trial_dir, generation)
            system_state_path = "%s/system-state-%03d.json" % (
                trial_dir, generation)
            events_log_path = "%s/events.log" % (trial_dir)
            cli_output_path = "%s/cli-output-%d.log" % (trial_dir, generation)
            field_val_dict_path = "%s/field-val-dict-%d.json" % (
                trial_dir, generation)

            if not os.path.exists(mutated_filename):
                break

            if not os.path.exists(operator_log_path):
                continue

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
                snapshot = Snapshot(input, cli_result,
                                    system_state, operator_log)

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
