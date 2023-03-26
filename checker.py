from builtins import TypeError
from copy import deepcopy
import sys
import logging
from typing import Dict, List
from deepdiff import DeepDiff
from deepdiff.model import DiffLevel
from deepdiff.operator import BaseOperator
from deepdiff.helper import CannotCompare
import re
import copy
import operator
from functools import reduce

from common import *
from compare import CompareMethods
from input import InputModel
from schema import ArraySchema, BooleanSchema, ObjectSchema
from snapshot import EmptySnapshot, Snapshot
from thread_logger import get_thread_logger
from parse_log.parse_log import parse_log


class Checker(object):

    def __init__(self, context: dict, trial_dir: str, input_model: InputModel,
                 custom_oracle: List[callable], feature_gate: FeatureGate) -> None:
        self.context = context
        self.namespace = context['namespace']
        self.compare_method = CompareMethods(feature_gate)
        self.trial_dir = trial_dir
        self.input_model = input_model
        self.custom_oracle = custom_oracle

        self.feature_gate = feature_gate

        self.control_flow_fields = self.context['analysis_result']['control_flow_fields']

        self.field_conditions_map = {}
        self.field_conditions_map = self.context['analysis_result']['field_conditions_map']
        self.helper(self.input_model.get_root_schema())
        # logging.info('Field condition map: %s' %
        #              json.dumps(self.field_conditions_map, indent=6))
        # logging.debug(self.context['analysis_result']['paths'])

    def helper(self, schema: ObjectSchema):
        if not isinstance(schema, ObjectSchema):
            return
        for key, value in schema.get_properties().items():
            if key == 'enabled':
                self.encode_dependency(schema.path, schema.path + [key])
            if isinstance(value, ObjectSchema):
                self.helper(value)
            elif isinstance(value, ArraySchema):
                self.helper(value.get_item_schema())

    def encode_dependency(self, depender: list, dependee: list):
        '''Encode dependency of dependant on dependee

        Args:
            depender: path of the depender
            dependee: path of the dependee
        '''
        logger = get_thread_logger(with_prefix=True)

        logger.info('Encode dependency of %s on %s' % (depender, dependee))
        encoded_path = json.dumps(depender)
        if encoded_path not in self.field_conditions_map:
            self.field_conditions_map[encoded_path] = {'conditions': [], 'type': 'AND'}

        # Add dependency to the subfields, idealy we should have a B tree for this
        for key, value in self.field_conditions_map.items():
            path = json.loads(key)
            if is_subfield(path, depender):
                logger.debug('Add dependency of %s on %s' % (path, dependee))
                value['conditions'].append({
                    'type': 'OR',
                    'conditions': [{
                        'field': dependee,
                        'op': '==',
                        'value': True
                    }]
                })

    def check(self, snapshot: Snapshot, prev_snapshot: Snapshot, revert: bool, generation: int,
              testcase_signature: dict) -> RunResult:
        '''Use acto oracles against the results to check for any errors

        Args:        
            result: includes the path to result files

        Returns:
            RunResult of the checking
        '''
        logger = get_thread_logger(with_prefix=True)
        runResult = RunResult(revert, generation, self.feature_gate, testcase_signature)

        stdout, stderr = snapshot.cli_result['stdout'], snapshot.cli_result['stderr']

        if stderr.find('connection refused') != -1 or stderr.find('deadline exceeded') != -1:
            logger.info('Connection refused, reject mutation')
            runResult.input_result = ConnectionRefusedResult()
            return runResult

        if snapshot.operator_log != None and 'Bug!' in snapshot.operator_log:
            runResult.crash_result = ErrorResult(Oracle.CRASH, snapshot.operator_log)
            return runResult

        if snapshot.system_state == {}:
            runResult.misc_result = InvalidInputResult(None)
            return runResult

        self.delta_log_path = "%s/delta-%d.log" % (self.trial_dir, generation)
        input_delta, system_delta = self.get_deltas(snapshot, prev_snapshot)
        flattened_system_state = flatten_dict(snapshot.system_state, [])

        crash_result = self.check_crash(snapshot)
        runResult.crash_result = crash_result

        input_result = self.check_input(snapshot, input_delta)
        runResult.input_result = input_result

        runResult.state_result = self.check_resources(snapshot, prev_snapshot)
        runResult.log_result = self.check_operator_log(snapshot, prev_snapshot)

        if len(input_delta) > 0:
            num_delta = 0
            for resource_delta_list in system_delta.values():
                for type_delta_list in resource_delta_list.values():
                    for state_delta in type_delta_list.values():
                        num_delta += 1
            logger.info('Number of system state fields: [%d] Number of delta: [%d]' %
                        (len(flattened_system_state), num_delta))

        # XXX: disable health check for now
        runResult.health_result = self.check_health(snapshot, prev_snapshot)
        # health_result = PassResult()

        if self.custom_oracle != None:
            # This custom_oracle field needs be None when Checker is used in post run
            # because the custom oracle may need runtime information which is not available in the
            # post run
            for oracle in self.custom_oracle:
                custom_result = oracle()
                if not isinstance(custom_result, PassResult):
                    runResult.custom_result = custom_result

        if self.feature_gate.write_result_each_generation_enabled():
            generation_result_path = os.path.join(self.trial_dir,
                                                  'generation-%d-runtime.json' % generation)
            with open(generation_result_path, 'w') as f:
                json.dump(runResult.to_dict(), f, cls=ActoEncoder, indent=4)

        return runResult

    def check_crash(self, snapshot: Snapshot) -> RunResult:
        pods = snapshot.system_state['pod']
        deployment_pods = snapshot.system_state['deployment_pods']

        for pod_name, pod in pods.items():
            container_statuses = pod['status']['container_statuses']
            if container_statuses is None:
                continue
            for container_status in container_statuses:
                if 'state' in container_status:
                    if 'terminated' in container_status[
                            'state'] and container_status['state']['terminated'] != None:
                        if container_status['state']['terminated']['reason'] == 'Error':
                            return ErrorResult(Oracle.CRASH, 'Pod %s crashed' % pod_name)
                    elif 'waiting' in container_status[
                            'state'] and container_status['state']['waiting'] != None:
                        if container_status['state']['waiting']['reason'] == 'CrashLoopBackOff':
                            return ErrorResult(Oracle.CRASH, 'Pod %s crashed' % pod_name)

        for deployment_name, deployment in deployment_pods.items():
            for pod in deployment:
                container_statuses = pod['status']['container_statuses']
                if container_statuses is None:
                    continue
                for container_status in container_statuses:
                    if 'state' in container_status:
                        if 'terminated' in container_status[
                                'state'] and container_status['state']['terminated'] != None:
                            if container_status['state']['terminated']['reason'] == 'Error':
                                return ErrorResult(Oracle.CRASH,
                                                   'Pod %s crashed' % pod['metadata']['name'])
                        elif 'waiting' in container_status[
                                'state'] and container_status['state']['waiting'] != None:
                            if container_status['state']['waiting']['reason'] == 'CrashLoopBackOff':
                                return ErrorResult(Oracle.CRASH,
                                                   'Pod %s crashed' % pod['metadata']['name'])

        return PassResult()

    def check_input(self, snapshot: Snapshot, input_delta) -> OracleResult:
        logger = get_thread_logger(with_prefix=True)

        stdout, stderr = snapshot.cli_result['stdout'], snapshot.cli_result['stderr']

        if stderr.find('connection refused') != -1 or stderr.find('deadline exceeded') != -1:
            logger.info('Connection refused, reject mutation')
            return ConnectionRefusedResult()

        is_invalid, reponsible_field_path = invalid_input_message(stderr, input_delta)

        # the stderr should indicate the invalid input
        if len(stderr) > 0:
            is_invalid = True

        if is_invalid:
            logger.info('Invalid input, reject mutation')
            logger.info('STDOUT: ' + stdout)
            logger.info('STDERR: ' + stderr)
            return InvalidInputResult(reponsible_field_path)

        if stdout.find('unchanged') != -1 or stderr.find('unchanged') != -1:
            logger.info('CR unchanged, continue')
            return UnchangedInputResult()

        return PassResult()

    def check_resources(self, snapshot: Snapshot, prev_snapshot: Snapshot) -> OracleResult:
        '''
        System state oracle

        For each delta in the input, find the longest matching fields in the system state.
        Then compare the the delta values (prev, curr).

        Args:
            result - includes the path to delta log files

        Returns:
            RunResult of the checking
        '''
        logger = get_thread_logger(with_prefix=True)

        input_delta, system_delta = self.get_deltas(snapshot, prev_snapshot)

        with open(self.delta_log_path, 'w') as f:
            f.write('---------- INPUT DELTA  ----------\n')
            f.write(json.dumps(input_delta, cls=ActoEncoder, indent=6))
            f.write('\n---------- SYSTEM DELTA ----------\n')
            f.write(json.dumps(system_delta, cls=ActoEncoder, indent=6))

        status_delta = system_delta['custom_resource_status']
        if status_delta is not None:
            for delta_list in status_delta.values():
                for delta in delta_list.values():
                    if len(delta.path) == 3 and delta.path[0] == 'conditions' and delta.path[
                            2] == 'message' and isinstance(delta.curr, str):
                        is_invalid, responsible_path = invalid_input_message(
                            delta.curr, input_delta)
                        if is_invalid:
                            logger.info('Invalid input from status message: %s' % delta.curr)
                            return PassResult()

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
                match_deltas = self._list_matched_fields(delta.path, system_delta_without_cr)

                # TODO: should the delta match be inclusive?
                # Policy: pass if any of the matched deltas is equivalent
                for match_delta in match_deltas:
                    logger.debug('Input delta [%s] matched with [%s]' %
                                 (delta.path, match_delta.path))
                    if not self.compare_method.compare(delta.prev, delta.curr, match_delta.prev,
                                                       match_delta.curr):
                        logger.error('Matched delta inconsistent with input delta')
                        logger.error('Input delta: %s -> %s' % (delta.prev, delta.curr))
                        logger.error('Matched delta: %s -> %s' %
                                     (match_delta.prev, match_delta.curr))
                        return StateResult(Oracle.SYSTEM_STATE,
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
                    logger.error('Found no matching fields for input delta')
                    logger.error('Input delta [%s]' % delta.path)
                    return StateResult(Oracle.SYSTEM_STATE, 'Found no matching fields for input',
                                       delta)
        return PassResult()

    def check_condition_group(self, input: dict, condition_group: dict,
                              input_delta_path: list) -> bool:
        if 'type' in condition_group:
            typ = condition_group['type']
            if typ == 'AND':
                for condition in condition_group['conditions']:
                    if not self.check_condition_group(input, condition, input_delta_path):
                        return False
                return True
            elif typ == 'OR':
                for condition in condition_group['conditions']:
                    if self.check_condition_group(input, condition, input_delta_path):
                        return True
                return False
        else:
            return self.check_condition(input, condition_group, input_delta_path)

    def should_skip_input_delta(self, input_delta: Diff, snapshot: Snapshot) -> bool:
        '''Determines if the input delta should be skipped or not

        Args:
            input_delta: Diff
            snapshot: current snapshot of the system state

        Returns:
            if the arg input_delta should be skipped in oracle
        '''
        logger = get_thread_logger(with_prefix=True)

        if self.feature_gate.default_value_comparison_enabled():
            try:
                default_value = self.input_model.get_schema_by_path(input_delta.path).default
                if input_delta.prev == default_value and (input_delta.curr == None or
                                                          isinstance(input_delta.curr, NotPresent)):
                    return True
                elif input_delta.curr == default_value and (input_delta.prev == None or isinstance(
                        input_delta.prev, NotPresent)):
                    return True
            except Exception as e:
                # print error message
                logger.warning(f"{e} happened when trying to fetch default value")

        if self.feature_gate.dependency_analysis_enabled():
            # dependency checking
            field_conditions_map = self.field_conditions_map
            encoded_path = json.dumps(input_delta.path)
            if encoded_path in field_conditions_map:
                condition_group = field_conditions_map[encoded_path]
                if not self.check_condition_group(snapshot.input, condition_group,
                                                  input_delta.path):
                    # if one condition does not satisfy, skip this testcase
                    logger.info('Field precondition %s does not satisfy, skip this testcase' %
                                condition_group)
                    return True
            else:
                # if no exact match, try find parent field
                parent = Checker.find_nearest_parent(input_delta.path, field_conditions_map.keys())
                if parent is not None:
                    condition_group = field_conditions_map[json.dumps(parent)]
                    if not self.check_condition_group(snapshot.input, condition_group,
                                                      input_delta.path):
                        # if one condition does not satisfy, skip this testcase
                        logger.info('Field precondition %s does not satisfy, skip this testcase' %
                                    condition_group)
                        return True

        if self.feature_gate.taint_analysis_enabled():
            for control_flow_field in self.control_flow_fields:
                if len(input_delta.path) == len(control_flow_field):
                    not_match = False
                    for i in range(len(input_delta.path)):
                        if control_flow_field[i] == 'INDEX' and re.match(
                                r"^\d$", str(input_delta.path[i])):
                            continue
                        elif input_delta.path[i] != control_flow_field[i]:
                            not_match = True
                            break
                    if not_match:
                        continue
                    else:
                        return True

        return False

    def find_nearest_parent(path: list, encoded_path_list: list) -> list:
        length = 0
        ret = None
        for encoded_path in encoded_path_list:
            p = json.loads(encoded_path)
            if len(p) > len(path):
                continue

            different = False
            for i in range(len(p)):
                if p[i] != path[i]:
                    different = True
                    break

            if different:
                continue
            elif len(p) > length:
                ret = p
        return ret

    def check_condition(self, input: dict, condition: dict, input_delta_path: list) -> bool:
        path = condition['field']

        # corner case: skip if condition is simply checking if the path is not nil
        if is_subfield(input_delta_path,
                       path) and condition['op'] == '!=' and condition['value'] == None:
            return True

        # hack: convert 'INDEX' to int 0
        for i in range(len(path)):
            if path[i] == 'INDEX':
                path[i] = 0

        try:
            value = reduce(operator.getitem, path, input)
        except (KeyError, TypeError, IndexError) as e:
            if translate_op(condition['op']) == operator.eq and condition['value'] == None:
                return True
            else:
                return False

        # the condition_value is stored as string in the json file
        condition_value = condition['value']
        if isinstance(value, int):
            condition_value = int(condition_value) if condition_value != None else None
        elif isinstance(value, float):
            condition_value = float(condition_value) if condition_value != None else None
        try:
            if translate_op(condition['op'])(value, condition_value):
                return True
        except TypeError as e:
            return False

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
            # We do not check the log line if it is not an warn/error/fatal message

            parsed_log = parse_log(line)
            if parsed_log == {} or parsed_log['level'].lower() != 'warn' and parsed_log[
                    'level'].lower() != 'error' and parsed_log['level'].lower() != 'fatal':
                continue

            # List all the values in parsed_log
            for value in list(parsed_log.values()):
                if type(value) != str or value == '':
                    continue
                is_invalid, reponsible_field_path = invalid_input_message(value, input_delta)
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

    def check_health(self, snapshot: Snapshot, prev_snapshot: Snapshot) -> OracleResult:
        '''System health oracle'''
        logger = get_thread_logger(with_prefix=True)

        system_state = snapshot.system_state
        unhealthy_resources = {}

        # check Health of Statefulsets
        unhealthy_resources['statefulset'] = []
        for sfs in system_state['stateful_set'].values():
            if sfs['status']['ready_replicas'] == None and sfs['status']['replicas'] == 0:
                # replicas could be 0
                continue
            if sfs['status']['replicas'] != sfs['status']['ready_replicas']:
                unhealthy_resources['statefulset'].append(
                    '%s replicas [%s] ready_replicas [%s]' %
                    (sfs['metadata']['name'], sfs['status']['replicas'],
                     sfs['status']['ready_replicas']))

        # check Health of Deployments
        unhealthy_resources['deployment'] = []
        for dp in system_state['deployment'].values():
            if dp['spec']['replicas'] == 0:
                continue

            if dp['status']['replicas'] != dp['status']['ready_replicas']:
                unhealthy_resources['deployment'].append(
                    '%s replicas [%s] ready_replicas [%s]' %
                    (dp['metadata']['name'], dp['status']['replicas'],
                     dp['status']['ready_replicas']))

            for condition in dp['status']['conditions']:
                if condition['type'] == 'Available' and condition['status'] != 'True':
                    unhealthy_resources['deployment'].append(
                        '%s condition [%s] status [%s] message [%s]' %
                        (dp['metadata']['name'], condition['type'], condition['status'],
                         condition['message']))
                elif condition['type'] == 'Progressing' and condition['status'] != 'True':
                    unhealthy_resources['deployment'].append(
                        '%s condition [%s] status [%s] message [%s]' %
                        (dp['metadata']['name'], condition['type'], condition['status'],
                         condition['message']))

        # check Health of Pods
        unhealthy_resources['pod'] = []
        for pod in system_state['pod'].values():
            if pod['status']['phase'] in ['Running', 'Completed', 'Succeeded']:
                continue
            unhealthy_resources['pod'].append(pod['metadata']['name'])

        # check Health of CRs
        unhealthy_resources['cr'] = []
        if system_state['custom_resource_status'] != None and 'conditions' in system_state[
                'custom_resource_status']:
            for condition in system_state['custom_resource_status']['conditions']:
                if condition['type'] == 'Ready' and condition['status'] != 'True':
                    unhealthy_resources['cr'].append('%s condition [%s] status [%s] message [%s]' %
                                                     ('CR status unhealthy', condition['type'],
                                                      condition['status'], condition['message']))

        error_msg = ''
        for kind, resources in unhealthy_resources.items():
            if len(resources) != 0:
                error_msg += f"{kind}: {', '.join(resources)}\n"
                logger.error(f"Found {kind}: {', '.join(resources)} with unhealthy status")

        if error_msg != '':
            return UnhealthyResult(Oracle.SYSTEM_HEALTH, error_msg)

        return PassResult()

    def check_events_log(self, snapshot: Snapshot) -> RunResult:
        pass

    def count_num_fields(self, snapshot: Snapshot, prev_snapshot: Snapshot):
        input_delta, system_delta = self.get_deltas(snapshot, prev_snapshot)
        flattened_system_state = flatten_dict(snapshot.system_state, [])

        input_result = self.check_input(snapshot, input_delta)
        if not isinstance(input_result, PassResult):
            return None

        if len(input_delta) > 0:
            num_delta = 0
            for resource_delta_list in system_delta.values():
                for type_delta_list in resource_delta_list.values():
                    for state_delta in type_delta_list.values():
                        num_delta += 1
            return len(flattened_system_state), num_delta

        return None

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

        input_delta = postprocess_diff(DeepDiff(prev_input, curr_input, view='tree'))

        system_state_delta = {}
        for resource in curr_system_state:
            if resource not in prev_system_state:
                prev_system_state[resource] = {}
            system_state_delta[resource] = postprocess_diff(
                DeepDiff(prev_system_state[resource],
                         curr_system_state[resource],
                         exclude_regex_paths=EXCLUDE_PATH_REGEX,
                         view='tree'))

        return input_delta, system_state_delta

    def check_state_equality(self, snapshot: Snapshot, prev_snapshot: Snapshot) -> OracleResult:
        '''Check whether two system state are semantically equivalent

        Args:
            - snapshot: a reference to a system state
            - prev_snapshot: a reference to another system state

        Return value:
            - a dict of diff results, empty if no diff found
        '''
        logger = get_thread_logger(with_prefix=True)

        curr_system_state = deepcopy(snapshot.system_state)
        prev_system_state = deepcopy(prev_snapshot.system_state)

        del curr_system_state['endpoints']
        del prev_system_state['endpoints']
        del curr_system_state['job']
        del prev_system_state['job']

        # remove pods that belong to jobs from both states to avoid observability problem
        curr_pods = curr_system_state['pod']
        prev_pods = prev_system_state['pod']
        curr_system_state['pod'] = {
            k: v
            for k, v in curr_pods.items()
            if v['metadata']['owner_references'][0]['kind'] != 'Job'
        }
        prev_system_state['pod'] = {
            k: v
            for k, v in prev_pods.items()
            if v['metadata']['owner_references'][0]['kind'] != 'Job'
        }

        for name, obj in prev_system_state['secret'].items():
            if 'data' in obj and obj['data'] != None:
                for key, data in obj['data'].items():
                    try:
                        obj['data'][key] = json.loads(data)
                    except:
                        pass

        for name, obj in curr_system_state['secret'].items():
            if 'data' in obj and obj['data'] != None:
                for key, data in obj['data'].items():
                    try:
                        obj['data'][key] = json.loads(data)
                    except:
                        pass

        # remove custom resource from both states
        curr_system_state.pop('custom_resource_spec', None)
        prev_system_state.pop('custom_resource_spec', None)
        curr_system_state.pop('custom_resource_status', None)
        prev_system_state.pop('custom_resource_status', None)

        # remove fields that are not deterministic
        exclude_paths = [
            r".*\['metadata'\]\['managed_fields'\]",
            r".*\['metadata'\]\['creation_timestamp'\]",
            r".*\['metadata'\]\['resource_version'\]",
            r".*\['metadata'\].*\['uid'\]",
            r".*\['metadata'\]\['generation'\]",
            r".*\['metadata'\]\['annotations'\]",
            r".*\['metadata'\]\['annotations'\]\['.*last-applied.*'\]",
            r".*\['metadata'\]\['annotations'\]\['.*\.kubernetes\.io.*'\]",
            r".*\['metadata'\]\['labels'\]\['.*revision.*'\]",
            r".*\['metadata'\]\['labels'\]\['owner-rv'\]",
            r".*\['status'\]",
            r".*\['spec'\]\['init_containers'\]\[.*\]\['volume_mounts'\]\[.*\]\['name'\]",
            r".*\['spec'\]\['containers'\]\[.*\]\['volume_mounts'\]\[.*\]\['name'\]",
            r".*\['spec'\]\['volumes'\]\[.*\]\['name'\]",
            r".*\[.*\]\['node_name'\]",
            r".*\['version'\]",
            r".*\['endpoints'\]\[.*\]\['addresses'\]\[.*\]\['target_ref'\]\['uid'\]",
            r".*\['endpoints'\]\[.*\]\['addresses'\]\[.*\]\['target_ref'\]\['resource_version'\]",
            r".*\['endpoints'\]\[.*\]\['addresses'\]\[.*\]\['ip'\]",
            r".*\['cluster_ip'\]",
            r".*\['cluster_i_ps'\].*",
            r".*\['deployment_pods'\].*\['metadata'\]\['name'\]",
        ]

        diff = DeepDiff(prev_system_state, curr_system_state, exclude_regex_paths=exclude_paths)

        if diff:
            logger.debug(f"failed attempt recovering to seed state - system state diff: {diff}")
            return RecoveryResult(delta=diff, from_=prev_system_state, to_=curr_system_state)

        return PassResult()


def compare_system_equality(curr_system_state: Dict,
                            prev_system_state: Dict,
                            additional_exclude_paths: List[str] = []):
    curr_system_state = deepcopy(curr_system_state)
    prev_system_state = deepcopy(prev_system_state)

    try:
        del curr_system_state['endpoints']
        del prev_system_state['endpoints']
        del curr_system_state['job']
        del prev_system_state['job']
    except:
        return PassResult()

    # remove pods that belong to jobs from both states to avoid observability problem
    curr_pods = curr_system_state['pod']
    prev_pods = prev_system_state['pod']

    new_pods = {}
    for k, v in curr_pods.items():
        if 'metadata' in v and 'owner_references' in v[
                'metadata'] and v['metadata']['owner_references'] != None and v['metadata'][
                    'owner_references'][0]['kind'] != 'Job':
            new_pods[k] = v
    curr_system_state['pod'] = new_pods

    new_pods = {}
    for k, v in prev_pods.items():
        if 'metadata' in v and 'owner_references' in v[
                'metadata'] and v['metadata']['owner_references'] != None and v['metadata'][
                    'owner_references'][0]['kind'] != 'Job':
            new_pods[k] = v
    prev_system_state['pod'] = new_pods

    for name, obj in prev_system_state['secret'].items():
        if 'data' in obj and obj['data'] != None:
            for key, data in obj['data'].items():
                try:
                    obj['data'][key] = json.loads(data)
                except:
                    pass

    for name, obj in curr_system_state['secret'].items():
        if 'data' in obj and obj['data'] != None:
            for key, data in obj['data'].items():
                try:
                    obj['data'][key] = json.loads(data)
                except:
                    pass

    # remove custom resource from both states
    curr_system_state.pop('custom_resource_spec', None)
    prev_system_state.pop('custom_resource_spec', None)
    curr_system_state.pop('custom_resource_status', None)
    prev_system_state.pop('custom_resource_status', None)
    curr_system_state.pop('pvc', None)
    prev_system_state.pop('pvc', None)

    # remove fields that are not deterministic
    exclude_paths = [
        r".*\['metadata'\]\['managed_fields'\]", r".*\['metadata'\]\['cluster_name'\]",
        r".*\['metadata'\]\['creation_timestamp'\]", r".*\['metadata'\]\['resource_version'\]",
        r".*\['metadata'\].*\['uid'\]", r".*\['metadata'\]\['generation'\]$",
        r".*\['metadata'\]\['annotations'\]",
        r".*\['metadata'\]\['annotations'\]\['.*last-applied.*'\]",
        r".*\['metadata'\]\['annotations'\]\['.*\.kubernetes\.io.*'\]",
        r".*\['metadata'\]\['labels'\]\['.*revision.*'\]",
        r".*\['metadata'\]\['labels'\]\['owner-rv'\]", r".*\['status'\]",
        r".*\['spec'\]\['init_containers'\]\[.*\]\['volume_mounts'\]\[.*\]\['name'\]$",
        r".*\['spec'\]\['containers'\]\[.*\]\['volume_mounts'\]\[.*\]\['name'\]$",
        r".*\['spec'\]\['volumes'\]\[.*\]\['name'\]$", r".*\[.*\]\['node_name'\]$",
        r".*\[\'spec\'\]\[\'host_users\'\]$", r".*\[\'spec\'\]\[\'os\'\]$", r".*\[\'grpc\'\]$",
        r".*\[\'spec\'\]\[\'volume_name\'\]$", r".*\['version'\]$",
        r".*\['endpoints'\]\[.*\]\['addresses'\]\[.*\]\['target_ref'\]\['uid'\]$",
        r".*\['endpoints'\]\[.*\]\['addresses'\]\[.*\]\['target_ref'\]\['resource_version'\]$",
        r".*\['endpoints'\]\[.*\]\['addresses'\]\[.*\]\['ip'\]", r".*\['cluster_ip'\]$",
        r".*\['cluster_i_ps'\].*$", r".*\['deployment_pods'\].*\['metadata'\]\['name'\]$",
        r"\[\'config_map\'\]\[\'kube\-root\-ca\.crt\'\]\[\'data\'\]\[\'ca\.crt\'\]$",
        r".*\['secret'\].*$", r"\['secrets'\]\[.*\]\['name'\]"
    ]

    exclude_paths.extend(additional_exclude_paths)

    diff = DeepDiff(prev_system_state,
                    curr_system_state,
                    exclude_regex_paths=exclude_paths,
                    iterable_compare_func=compare_func,
                    custom_operators=[NameOperator(r".*\['name'\]$")])

    if 'dictionary_item_removed' in diff:
        new_removed_items = []
        for removed_item in diff['dictionary_item_removed']:
            if removed_item.startswith("root['pvc']"):
                logger.debug(f"ignoring removed pod {removed_item}")
            else:
                new_removed_items.append(removed_item)
        if len(new_removed_items) == 0:
            del diff['dictionary_item_removed']
        else:
            diff['dictionary_item_removed'] = new_removed_items

    if diff:
        logger.debug(f"failed attempt recovering to seed state - system state diff: {diff}")
        return RecoveryResult(delta=diff, from_=prev_system_state, to_=curr_system_state)

    return PassResult()


def compare_func(x, y, level: DiffLevel = None):
    try:
        if 'name' not in x or 'name' not in y:
            return x['key'] == y['key'] and x['operator'] == y['operator']
        x_name = x['name']
        y_name = y['name']
        if len(x_name) < 5 or len(y_name) < 5:
            return x_name == y_name
        else:
            return x_name[:5] == y_name[:5]
    except:
        raise CannotCompare() from None


class NameOperator(BaseOperator):

    def give_up_diffing(self, level, diff_instance):
        x_name = level.t1
        y_name = level.t2
        if x_name == None or y_name == None:
            return False
        if re.search(r"^.+-([A-Za-z0-9]{5})$", x_name) and re.search(r"^.+-([A-Za-z0-9]{5})$",
                                                                     y_name):
            return x_name[:5] == y_name[:5]
        return False


class BlackBoxChecker(Checker):

    def __init__(self, context: dict, trial_dir: str, input_model: InputModel,
                 custom_oracle: List[callable], feature_gate: FeatureGate) -> None:
        self.context = context
        self.namespace = context['namespace']
        self.compare_method = CompareMethods(feature_gate)
        self.trial_dir = trial_dir
        self.input_model = input_model
        self.custom_oracle = custom_oracle

        self.feature_gate = feature_gate

        self.field_conditions_map = {}
        self.helper(self.input_model.get_root_schema())

        schemas_tuple = input_model.get_all_schemas()
        all_schemas = schemas_tuple[0] + schemas_tuple[1] + schemas_tuple[2]
        self.control_flow_fields = [
            schema.get_path() for schema in all_schemas if isinstance(schema, BooleanSchema)
        ]


if __name__ == "__main__":
    import glob
    import os
    import yaml
    import traceback
    import argparse
    from types import SimpleNamespace
    import typing
    import pandas
    import multiprocessing
    import queue

    def checker_save_result(trial_dir: str, original_result: dict, runResult: RunResult,
                            alarm: bool, mode: str):

        result_dict = {}
        result_dict['alarm'] = alarm
        result_dict['original_result'] = original_result
        post_result = {}
        result_dict['post_result'] = post_result
        try:
            trial_num = '-'.join(trial_dir.split('-')[-2:])
            post_result['trial_num'] = trial_num + '-%d' % runResult.generation
        except:
            post_result['trial_num'] = trial_dir
        post_result['error'] = runResult.to_dict()
        result_path = os.path.join(trial_dir,
                                   'post-result-%d-%s.json' % (runResult.generation, mode))
        with open(result_path, 'w') as result_file:
            json.dump(result_dict, result_file, cls=ActoEncoder, indent=6)

    def check_trial_worker(workqueue: multiprocessing.Queue, checker_class: type,
                           num_system_fields_list: multiprocessing.Array,
                           num_delta_fields_list: multiprocessing.Array, mode: str,
                           feature_gate: FeatureGate):
        while True:
            try:
                trial_dir = workqueue.get(block=False)
            except queue.Empty:
                break

            print(trial_dir)
            if not os.path.isdir(trial_dir):
                continue
            original_result_path = "%s/result.json" % (trial_dir)
            with open(original_result_path, 'r') as original_result_file:
                original_result = json.load(original_result_file)

            input_model = InputModel(context['crd']['body'], [], config.example_dir, 1, 1, [])

            input_model.apply_default_value(context['analysis_result']['default_value_map'])

            checker: Checker = checker_class(context=context,
                                             trial_dir=trial_dir,
                                             input_model=input_model,
                                             custom_oracle=None,
                                             feature_gate=FeatureGate(feature_gate))
            snapshots = []
            snapshots.append(EmptySnapshot(seed))

            alarm = False
            for generation in range(0, 20):
                mutated_filename = '%s/mutated-%d.yaml' % (trial_dir, generation)
                operator_log_path = "%s/operator-%d.log" % (trial_dir, generation)
                system_state_path = "%s/system-state-%03d.json" % (trial_dir, generation)
                events_log_path = "%s/events.log" % (trial_dir)
                cli_output_path = "%s/cli-output-%d.log" % (trial_dir, generation)
                runtime_result_path = "%s/generation-%d-runtime.json" % (trial_dir, generation)

                if not os.path.exists(mutated_filename):
                    break

                if not os.path.exists(operator_log_path):
                    continue

                with open(mutated_filename, 'r') as input_file, \
                        open(operator_log_path, 'r') as operator_log, \
                        open(system_state_path, 'r') as system_state, \
                        open(events_log_path, 'r') as events_log, \
                        open(cli_output_path, 'r') as cli_output, \
                        open(runtime_result_path, 'r') as runtime_result_file:
                    input = yaml.load(input_file, Loader=yaml.FullLoader)
                    cli_result = json.load(cli_output)
                    logging.info(cli_result)
                    system_state = json.load(system_state)
                    runtime_result = json.load(runtime_result_file)
                    operator_log = operator_log.read().splitlines()
                    snapshot = Snapshot(input, cli_result, system_state, operator_log)

                    prev_snapshot = snapshots[-1]
                    runResult = checker.check(snapshot=snapshot,
                                              prev_snapshot=prev_snapshot,
                                              revert=runtime_result['revert'],
                                              generation=generation,
                                              testcase_signature=runtime_result['testcase'])
                    snapshots.append(snapshot)

                    if runtime_result['recovery_result'] != None and runtime_result[
                            'recovery_result'] != 'Pass':
                        runResult.recovery_result = RecoveryResult(
                            runtime_result['delta', runtime_result['from'], runtime_result['to']])

                    if runtime_result['custom_result'] != None and runtime_result[
                            'custom_result'] != 'Pass':
                        runResult.custom_result = ErrorResult(
                            Oracle.CUSTOM, runtime_result['custom_result']['message'])

                    if runResult.is_connection_refused():
                        logging.debug('Connection refused')
                        snapshots.pop()
                        checker_save_result(trial_dir, runtime_result, runResult, False, mode)
                        continue
                    elif runResult.is_basic_error():
                        logging.debug('Basic error')
                        snapshots.pop()
                        checker_save_result(trial_dir, runtime_result, runResult, True, mode)
                        continue
                    is_invalid, _ = runResult.is_invalid()
                    if is_invalid:
                        logging.debug('Invalid')
                        snapshots.pop()
                        checker_save_result(trial_dir, runtime_result, runResult, False, mode)
                        continue
                    elif runResult.is_unchanged():
                        logging.debug('Unchanged')
                        checker_save_result(trial_dir, runtime_result, runResult, False, mode)
                        continue
                    elif runResult.is_error():
                        logging.info('%s reports an alarm' % system_state_path)
                        checker_save_result(trial_dir, runtime_result, runResult, True, mode)
                        alarm = True
                    else:
                        checker_save_result(trial_dir, runtime_result, runResult, False, mode)

                    num_fields_tuple = checker.count_num_fields(snapshot=snapshot,
                                                                prev_snapshot=prev_snapshot)
                    if num_fields_tuple != None:
                        num_system_fields, num_delta_fields = num_fields_tuple
                        num_system_fields_list.append(num_system_fields)
                        num_delta_fields_list.append(num_delta_fields)

            if not alarm:
                logging.info('%s does not report an alarm' % system_state_path)

    parser = argparse.ArgumentParser(description='Standalone checker for Acto')
    parser.add_argument('--testrun-dir', help='Directory to check', required=True)
    parser.add_argument('--config', help='Path to config file', required=True)
    parser.add_argument('--num-workers', help='Number of workers', type=int, default=4)
    parser.add_argument('--blackbox', dest='blackbox', help='Blackbox mode', action='store_true')
    # parser.add_argument('--output', help='Path to output file', required=True)

    args = parser.parse_args()

    with open(args.config, 'r') as config_file:
        config = json.load(config_file, object_hook=lambda d: SimpleNamespace(**d))
    testrun_dir = args.testrun_dir
    context_cache = os.path.join(os.path.dirname(config.seed_custom_resource), 'context.json')

    logging.basicConfig(
        filename=os.path.join('.', testrun_dir, 'checker_test.log'),
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

    trial_dirs = glob.glob(testrun_dir + '/*')
    with open(context_cache, 'r') as context_fin:
        context = json.load(context_fin)
        context['preload_images'] = set(context['preload_images'])

    context['enable_analysis'] = True

    if 'enable_analysis' in context and context['enable_analysis'] == True:
        logging.info('Analysis is enabled')
        for path in context['analysis_result']['control_flow_fields']:
            path.pop(0)
    else:
        context['enable_analysis'] = False

    with open(config.seed_custom_resource, 'r') as seed_file:
        seed = yaml.load(seed_file, Loader=yaml.FullLoader)

    BASELINE = FeatureGate.INVALID_INPUT_FROM_LOG | FeatureGate.DEFAULT_VALUE_COMPARISON
    CANONICALIZATION = BASELINE | FeatureGate.CANONICALIZATION
    TAINT_ANALYSIS = CANONICALIZATION | FeatureGate.TAINT_ANALYSIS
    DEPENDENCY_ANALYSIS = TAINT_ANALYSIS | FeatureGate.DEPENDENCY_ANALYSIS
    ALL = (FeatureGate.INVALID_INPUT_FROM_LOG | FeatureGate.DEFAULT_VALUE_COMPARISON |
           FeatureGate.DEPENDENCY_ANALYSIS | FeatureGate.TAINT_ANALYSIS |
           FeatureGate.CANONICALIZATION)
    F = {
        'baseline': BASELINE,
        'canonicalization': CANONICALIZATION,
        'taint_analysis': TAINT_ANALYSIS,
        'dependency_analysis': DEPENDENCY_ANALYSIS,
    }

    checker_class = Checker if not args.blackbox else BlackBoxChecker

    for name, feature_gate in F.items():
        mp_manager = multiprocessing.Manager()

        num_system_fields_list = mp_manager.list()
        num_delta_fields_list = mp_manager.list()

        workqueue = multiprocessing.Queue()
        for trial_dir in sorted(trial_dirs):
            workqueue.put(trial_dir)

        workers = [
            multiprocessing.Process(target=check_trial_worker,
                                    args=(workqueue, checker_class, num_system_fields_list,
                                          num_delta_fields_list, name, feature_gate))
            for _ in range(args.num_workers)
        ]

        for worker in workers:
            worker.start()

        for worker in workers:
            worker.join()

        num_system_fields_df = pandas.Series(list(num_system_fields_list))
        num_delta_fields_df = pandas.Series(list(num_delta_fields_list))
        logging.info(
            'Number of system fields: max[%s] min[%s] mean[%s]' %
            (num_system_fields_df.max(), num_system_fields_df.min(), num_system_fields_df.mean()))
        logging.info(
            'Number of delta fields: max[%s] min[%s] mean[%s]' %
            (num_delta_fields_df.max(), num_delta_fields_df.min(), num_delta_fields_df.mean()))
