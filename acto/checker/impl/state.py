import copy
import json
import operator
import re
from functools import reduce
from typing import List, Tuple

from deepdiff.helper import NotPresent

from acto.checker.checker import Checker
from acto.common import OracleResult, PassResult, invalid_input_message, Diff, print_event, StateResult, Oracle, InvalidInputResult, is_subfield, translate_op, GENERIC_FIELDS
from acto.checker.impl.compare_state import delta_equals, CompareMethods
from acto.config import actoConfig
from acto.input import InputModel
from acto.input.get_matched_schemas import find_matched_schema
from acto.schema import extract_schema, BooleanSchema, ObjectSchema, ArraySchema
from acto.serialization import ActoEncoder
from acto.snapshot import Snapshot
from acto.utils import get_thread_logger, is_prefix


def canonicalize(s: str):
    '''Replace all upper case letters with _lowercase'''
    if isinstance(s, int):
        return 'ITEM'
    s = str(s)
    return re.sub(r"(?=[A-Z])", '_', s).lower()


def skip_default_input_delta(diff: Diff) -> bool:
    if diff.path[-1] == 'ACTOKEY':
        return False

    prev = diff.prev
    curr = diff.curr

    if prev is None:
        return True
    elif isinstance(prev, NotPresent):
        return True

    if curr is None:
        return True

    # the original code will return None, which is not a boolean value
    # add a failed assertion to mark as a potential bug
    # TODO: check if the function should return false here
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


def check_condition(input: dict, condition: dict, input_delta_path: list) -> bool:
    path = condition['field']

    # corner case: skip if condition is simply checking if the path is not nil
    if is_subfield(input_delta_path,
                   path) and condition['op'] == '!=' and condition['value'] is None:
        return True

    # hack: convert 'INDEX' to int 0
    for i in range(len(path)):
        if path[i] == 'INDEX':
            path[i] = 0

    try:
        value = reduce(operator.getitem, path, input)
    except (KeyError, TypeError) as e:
        if translate_op(condition['op']) == operator.eq and condition['value'] is None:
            return True
        else:
            return False

    # the condition_value is stored as string in the json file
    condition_value = condition['value']
    if isinstance(value, int):
        condition_value = int(condition_value) if condition_value is not None else None
    elif isinstance(value, float):
        condition_value = float(condition_value) if condition_value is not None else None
    try:
        if translate_op(condition['op'])(value, condition_value):
            return True
    except TypeError as e:
        return False
    # the original code will return None, which is not a boolean value
    # add a failed assertion to mark as a potential bug
    assert False


def check_condition_group(input: dict, condition_group: dict,
                          input_delta_path: list) -> bool:
    if 'type' in condition_group:
        typ = condition_group['type']
        if typ == 'AND':
            for condition in condition_group['conditions']:
                if not check_condition_group(input, condition, input_delta_path):
                    return False
            return True
        elif typ == 'OR':
            for condition in condition_group['conditions']:
                if check_condition_group(input, condition, input_delta_path):
                    return True
            return False
    else:
        return check_condition(input, condition_group, input_delta_path)


def should_skip_input_delta(input_model: InputModel, field_conditions_map: dict, control_flow_fields: list, input_delta: Diff, snapshot: Snapshot) -> bool:
    '''Determines if the input delta should be skipped or not

    Args:
        input_delta: Diff
        snapshot: current snapshot of the system state

    Returns:
        if the arg input_delta should be skipped in oracle
    '''
    logger = get_thread_logger(with_prefix=True)

    if 'ephemeralContainers' in input_delta.path:
        return True

    if actoConfig.checkers.state.enable_default_value_comparison:
        try:
            default_value = input_model.get_schema_by_path(input_delta.path).default
            logger.info(f"Default value for {input_delta.path} is {default_value}")
            if str(input_delta.prev) == str(default_value):
                if (input_delta.curr == None or isinstance(input_delta.curr, NotPresent)):
                    return True
                elif isinstance(input_delta.curr, list) and len(input_delta.curr) == 0:
                    return True
                elif isinstance(input_delta.curr, dict) and len(input_delta.curr) == 0:
                    return True
                elif isinstance(input_delta.curr, str) and len(input_delta.curr) == 0:
                    return True
            elif str(input_delta.curr) == str(default_value):
                if (input_delta.prev == None or isinstance(input_delta.prev, NotPresent)):
                    return True
                elif isinstance(input_delta.prev, list) and len(input_delta.prev) == 0:
                    return True
                elif isinstance(input_delta.prev, dict) and len(input_delta.prev) == 0:
                    return True
                elif isinstance(input_delta.prev, str) and len(input_delta.prev) == 0:
                    return True
        except Exception as e:
            # print error message
            logger.warning(f"{e} happened when trying to fetch default value")

    if actoConfig.checkers.state.analysis.dependency:
        # dependency checking
        encoded_path = json.dumps(input_delta.path)
        if encoded_path in field_conditions_map:
            condition_group = field_conditions_map[encoded_path]
            if not check_condition_group(snapshot.input, condition_group,
                                         input_delta.path):
                # if one condition does not satisfy, skip this testcase
                logger.info('Field precondition %s does not satisfy, skip this testcase' %
                            condition_group)
                return True
        else:
            # if no exact match, try to find parent field
            parent = find_nearest_parent(input_delta.path, list(field_conditions_map.keys()))
            if parent is not None:
                condition_group = field_conditions_map[json.dumps(parent)]
                if not check_condition_group(snapshot.input, condition_group,
                                             input_delta.path):
                    # if one condition does not satisfy, skip this testcase
                    logger.info('Field precondition %s does not satisfy, skip this testcase' %
                                condition_group)
                    return True

    if actoConfig.checkers.state.analysis.taint:

        for control_flow_field in control_flow_fields:
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


def should_compare(k8s_paths: List[List[str]], path: List[str]) -> bool:
    if path[-1] == 'ACTOKEY':
        return True

    for k8s_path in k8s_paths:
        if is_prefix(k8s_path, path):
            return True
    logger = get_thread_logger(with_prefix=True)
    logger.info('Skip comparing %s' % path)
    return False


def list_matched_fields(k8s_paths: List[List[str]], path: list, delta_dict: dict) -> Tuple[list, bool]:
    '''Search through the entire system delta to find the longest matching field

    Args:
        path: path of input delta as list
        delta_dict: dict of system delta

    Returns:
        list of system delta with the longest matching field path with input delta
    '''
    # if the name of the field is generic, don't match using the path
    for regex in GENERIC_FIELDS:
        if re.search(regex, str(path[-1])):
            return [], False

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

    if max_match > 1:
        return results, True
    elif should_compare(k8s_paths, path):
        return results, True
    else:
        logger = get_thread_logger(with_prefix=True)
        logger.debug(f"Skipping {path} because it is not in the list of fields to compare")
        return [], False


class StateChecker(Checker):
    name = 'state'

    def __init__(self, trial_dir: str, input_model: InputModel, context: dict, **kwargs):
        super().__init__(trial_dir, **kwargs)
        self.input_model = input_model
        self.context = context
        crd = extract_schema([], context['crd']['body']['spec']['versions'][-1]['schema']['openAPIV3Schema'])
        self.k8s_paths = find_matched_schema(crd)

        if actoConfig.mode == 'whitebox':
            if 'analysis_result' in context and 'control_flow_fields' in context['analysis_result']:
                self.control_flow_fields = context['analysis_result']['control_flow_fields']
            else:
                self.control_flow_fields = []
        else:
            schemas_tuple = input_model.get_all_schemas()
            all_schemas = schemas_tuple[0] + schemas_tuple[1] + schemas_tuple[2]
            self.control_flow_fields = [
                schema.get_path() for schema in all_schemas if isinstance(schema, BooleanSchema)
            ]

        if actoConfig.mode == 'whitebox' and 'analysis_result' in context and 'field_conditions_map' in context['analysis_result']:
            self.field_conditions_map = context['analysis_result']['field_conditions_map']
        else:
            self.field_conditions_map = {}

        self.helper(self.input_model.get_root_schema())

    def write_delta_log(self, generation:int, input_delta, system_delta):
        delta_log_path = f'{self.trial_dir}/delta-{generation}.log'
        with open(delta_log_path, 'w') as f:
            f.write('---------- INPUT DELTA  ----------\n')
            f.write(json.dumps(input_delta, cls=ActoEncoder, indent=6))
            f.write('\n---------- SYSTEM DELTA ----------\n')
            f.write(json.dumps(system_delta, cls=ActoEncoder, indent=6))
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
    def check(self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot) -> OracleResult:
        """
          System state oracle

          For each delta in the input, find the longest matching fields in the system state.
          Then compare the delta values (prev, curr).

          Args:
              result - includes the path to delta log files

          Returns:
              RunResult of the checking
        """
        logger = get_thread_logger(with_prefix=True)

        input_delta, system_delta = snapshot.delta(prev_snapshot)
        self.write_delta_log(generation, input_delta, system_delta)

        # check if the input is valid
        # we can know this by checking the status message
        # you can refer to a delta log file for the details
        status_delta = system_delta['custom_resource_status']
        if status_delta is not None:
            for delta_list in status_delta.values():
                for delta in delta_list.values():
                    if len(delta.path) == 3 and delta.path[0] == 'conditions' and delta.path[2] == 'message' and isinstance(delta.curr, str):
                        is_invalid, responsible_path = invalid_input_message(delta.curr, input_delta)
                        if is_invalid:
                            logger.info('Invalid input from status message: %s' % delta.curr)
                            return InvalidInputResult(responsible_path)

        # cr_spec_diff is same as input delta, so it is excluded
        system_delta_without_cr = copy.deepcopy(system_delta)
        system_delta_without_cr.pop('custom_resource_spec')

        compare_method = CompareMethods(actoConfig.checkers.state.enable_canonicalization)

        for (diff_type, delta_list) in input_delta.items():
            for delta in delta_list.values():
                logger.debug('Checking input delta [%s]' % delta.path)
                corresponding_schema = self.input_model.get_schema_by_path(delta.path)

                if diff_type != 'iterable_item_removed':
                    if not corresponding_schema.patch and skip_default_input_delta(delta):
                        logger.debug('Input delta [%s] is skipped' % delta.path)
                        continue

                if delta_equals(delta.prev, delta.curr):
                    # if the input delta is considered as equivalent, skip
                    logger.debug('Input delta [%s] is equivalent' % delta.path)
                    continue

                if should_skip_input_delta(self.input_model, self.field_conditions_map, self.control_flow_fields, delta, snapshot):
                    logger.debug('Input delta [%s] is skipped' % delta.path)
                    continue

                # Find the longest matching field, compare the delta change
                match_deltas, should_compare = list_matched_fields(self.k8s_paths, delta.path, system_delta_without_cr)

                # TODO: should the delta match be inclusive?
                # Policy: pass if any of the matched deltas is equivalent
                found = False
                for match_delta in match_deltas:
                    logger.debug('Input delta [%s] matched with [%s]' %
                                 (delta.path, match_delta.path))
                    if compare_method.equals_after_transform(delta.prev, delta.curr, match_delta.prev,
                                                             match_delta.curr):
                        found = True
                        break

                if not found and should_compare:
                    if len(match_deltas) == 0:
                        # if prev and curr of the delta are the same, also consider it as a match
                        found = False
                        for resource_delta_list in system_delta_without_cr.values():
                            for type_delta_list in resource_delta_list.values():
                                for state_delta in type_delta_list.values():
                                    if compare_method.equals_after_transform(delta.prev, delta.curr,
                                                                             state_delta.prev,
                                                                             state_delta.curr):
                                        found = True
                        if found:
                            logger.info('Found match by comparing prev and curr of input delta')
                            continue
                        logger.error('Found no matching fields for input delta')
                        logger.error('Input delta [%s]' % delta.path)
                        print_event(f'Found bug: {delta.path} changed from [{delta.prev}] to [{delta.curr}]')
                        return StateResult(Oracle.SYSTEM_STATE,
                                           'Found no matching fields for input', delta)
                    else:
                        logger.error('Found no matching fields for input delta')
                        logger.error('Input delta [%s]' % delta.path)
                        print_event(f'Found bug: {delta.path} changed from [{delta.prev}] to [{delta.curr}]')
                        return StateResult(Oracle.SYSTEM_STATE,
                                           'Found no matching fields for input', delta)
                elif not should_compare:
                    logger.debug('Input delta [%s] is skipped' % delta.path)

        logger.info('All input deltas are matched')
        return PassResult()
