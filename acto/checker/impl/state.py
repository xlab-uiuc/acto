import copy
import json
import re
from dataclasses import dataclass
from typing import List, Tuple, Optional

from acto.checker.checker import BinaryChecker, OracleResult
from acto.checker.impl.state_condition import check_condition_group
from acto.common import invalid_input_message, Diff, print_event, is_subfield, GENERIC_FIELDS
from acto.checker.impl.state_compare import CompareMethods, is_none_or_not_present
from acto.config import actoConfig
from acto.input import InputModel
from acto.input.get_matched_schemas import find_matched_schema
from acto.k8s_util.k8sutil import canonicalize_quantity
from acto.schema import extract_schema, ObjectSchema, ArraySchema, BaseSchema
from acto.snapshot import Snapshot
from acto.utils import get_thread_logger, is_prefix


@dataclass
class StateResult(OracleResult):
    invalid_field_path: Optional[List[str]] = None
    diff: Optional[Diff] = None


def canonicalize_field_name(s: str):
    """Replace all uppercase letters with lowercase ones"""
    if isinstance(s, int):
        return 'ITEM'
    s = str(s)
    return re.sub(r"(?=[A-Z])", '_', s).lower()


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


def check_field_dependencies_are_satisfied(input_delta: Diff, snapshot: Snapshot, field_conditions_map: dict) -> bool:
    logger = get_thread_logger(with_prefix=True)

    encoded_path = json.dumps(input_delta.path)
    condition_group = None
    if encoded_path in field_conditions_map:
        condition_group = field_conditions_map[encoded_path]
    else:
        # if no exact match, try to find parent field
        parent = find_nearest_parent(input_delta.path, list(field_conditions_map.keys()))
        if parent is not None:
            condition_group = field_conditions_map[json.dumps(parent)]
    if condition_group and not check_condition_group(snapshot.input, condition_group, input_delta.path):
        # if one condition does not satisfy, skip this testcase
        logger.info('Field precondition %s does not satisfy' % condition_group)
        return False
    return True


def check_field_has_default_value(input_delta: Diff, input_model: InputModel) -> Tuple[bool, bool]:
    logger = get_thread_logger(with_prefix=True)

    try:
        default_value = input_model.get_schema_by_path(input_delta.path).default
        prev = input_delta.prev
        curr = input_delta.curr
        if actoConfig.checkers.state.enable_canonicalization:
            default_value = canonicalize_quantity(default_value)
            prev = canonicalize_quantity(prev)
            curr = canonicalize_quantity(curr)
        prev_has_default = False
        curr_has_default = False
        if default_value == prev:
            logger.debug(f'Field {input_delta.path}(prev) has default value {default_value}')
            prev_has_default = True
        if default_value == curr:
            logger.debug(f'Field {input_delta.path}(curr) has default value {default_value}')
            curr_has_default = True
        return prev_has_default, curr_has_default
    except AttributeError:
        logger.debug(f'No default value for field {input_delta.path}')
        return False, False
    except Exception as e:
        logger.error(f'Exception {e} when getting default value for field {input_delta.path}')
        return False, False


def should_compare_path(k8s_paths: List[List[str]], path: List[str]) -> bool:
    if path[-1] == 'ACTOKEY':
        return True

    for k8s_path in k8s_paths:
        if is_prefix(k8s_path, path):
            return True
    logger = get_thread_logger(with_prefix=True)
    logger.info('Skip comparing %s' % path)
    return False


def list_matched_fields(k8s_paths: List[List[str]], path: list, delta_dict: dict) -> Tuple[list, bool]:
    """Search through the entire system delta to find the longest matching field

    Args:
        path: path of input delta as list
        delta_dict: dict of system delta
        k8s_paths: A list of paths to the matched schemas

    Returns:
        list of system delta with the longest matching field path with input delta
    """
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
                while canonicalize_field_name(path[-position - 1]) == canonicalize_field_name(delta.path[-position - 1]):
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
    elif should_compare_path(k8s_paths, path):
        return results, True
    else:
        logger = get_thread_logger(with_prefix=True)
        logger.debug(f"Skipping {path} because it is not in the list of fields to compare")
        return [], False


class StateChecker(BinaryChecker):
    name = 'state'

    def __init__(self, input_model: InputModel, context: dict, **kwargs):
        super().__init__(**kwargs)
        self.input_model = input_model
        self.context = context
        crd = extract_schema([], context['crd']['body']['spec']['versions'][-1]['schema']['openAPIV3Schema'])
        self.k8s_paths = find_matched_schema(crd)

        if actoConfig.mode == 'whitebox' and 'analysis_result' in context and 'field_conditions_map' in context['analysis_result']:
            self.field_conditions_map = context['analysis_result']['field_conditions_map']
        else:
            self.field_conditions_map = {}

        self.update_dependency(self.input_model.get_root_schema())

    def update_dependency(self, schema: BaseSchema):
        if not isinstance(schema, ObjectSchema):
            return
        for key, value in schema.get_properties().items():
            if key == 'enabled':
                self.encode_dependency(schema.path, schema.path + [key])
            if isinstance(value, ObjectSchema):
                self.update_dependency(value)
            elif isinstance(value, ArraySchema):
                self.update_dependency(value.get_item_schema())

    def encode_dependency(self, depender: list, dependee: list):
        """Encode dependency of dependant on dependee

        Args:
            depender: path of the depender
            dependee: path of the dependee
        """
        logger = get_thread_logger(with_prefix=True)

        logger.info('Encode dependency of %s on %s' % (depender, dependee))
        encoded_path = json.dumps(depender)
        if encoded_path not in self.field_conditions_map:
            self.field_conditions_map[encoded_path] = {'conditions': [], 'type': 'AND'}

        # Add dependency to the subfields, ideally we should have a B tree for this
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

    def enabled(self, snapshot: Snapshot) -> bool:
        return super().enabled(snapshot) and snapshot.trial_state != 'recovering'

    def _binary_check(self, snapshot: Snapshot, prev_snapshot: Snapshot) -> OracleResult:
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
                            return StateResult('Invalid input from status message: %s' % delta.curr, invalid_field_path=responsible_path, diff=delta)

        # cr_spec_diff is same as input delta, so it is excluded
        system_delta_without_cr = copy.deepcopy(system_delta)
        system_delta_without_cr.pop('custom_resource_spec')

        compare_method = CompareMethods(actoConfig.checkers.state.enable_canonicalization)

        for (diff_type, delta_list) in input_delta.items():
            for delta in delta_list.values():
                logger.debug('Checking input delta [%s]' % delta.path)

                # whether we expect the system to produce a delta
                must_produce_delta = True

                if 'ephemeralContainers' in delta.path:
                    must_produce_delta = False

                if not check_field_dependencies_are_satisfied(delta, snapshot, self.field_conditions_map):
                    must_produce_delta = False

                # check curr and prev is the default value
                prev_is_default, curr_is_default = check_field_has_default_value(delta, self.input_model)

                # if the field is changed from default to null or null to default
                # we don't expect the system to produce a delta
                if prev_is_default and is_none_or_not_present(delta.curr):
                    must_produce_delta = False
                if curr_is_default and is_none_or_not_present(delta.prev):
                    must_produce_delta = False

                if is_none_or_not_present(delta.prev) and is_none_or_not_present(delta.curr):
                    must_produce_delta = False

                if actoConfig.checkers.state.enable_canonicalization:
                    canonicalized_prev = canonicalize_quantity(delta.prev)
                    canonicalized_curr = canonicalize_quantity(delta.curr)
                    if canonicalized_prev == canonicalized_curr:
                        must_produce_delta = False

                # Find the longest matching field, compare the delta change
                match_deltas, should_compare = list_matched_fields(self.k8s_paths, delta.path, system_delta_without_cr)
                should_compare = should_compare and must_produce_delta

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
                        state_delta = None
                        for resource_delta_list in system_delta_without_cr.values():
                            for type_delta_list in resource_delta_list.values():
                                for state_delta in type_delta_list.values():
                                    if compare_method.equals_after_transform(delta.prev, delta.curr,
                                                                             state_delta.prev,
                                                                             state_delta.curr):
                                        found = True
                        if found:
                            logger.info('Found match by comparing prev and curr of input delta')
                            logger.info(f'Input delta {delta.path}, Matched delta {state_delta.path}')
                            logger.info(f'Input delta prev {delta.prev}, curr {delta.curr}')
                            logger.info(f'Matched delta prev {state_delta.prev}, curr {state_delta.curr}')
                            continue
                        logger.error('Found no matching fields for input delta')
                        logger.error('Input delta [%s]' % delta.path)
                        print_event(f'Found bug: {delta.path} changed from [{delta.prev}] to [{delta.curr}]')
                        return StateResult('Found no matching fields for input', diff=delta)
                    else:
                        logger.error('Found no matching fields for input delta')
                        logger.error(f'Input delta {delta.path}')
                        logger.error(f'Input delta prev {delta.prev}, curr {delta.curr}')
                        for match_delta in match_deltas:
                            logger.error(f'Matched delta {match_delta.path}')
                            logger.error(f'Matched delta prev {match_delta.prev}, curr {match_delta.curr}')
                        logger.error('Failed to match input delta with matched system state delta')
                        print_event(f'Found bug: {delta.path} changed from [{delta.prev}] to [{delta.curr}]')
                        return StateResult('Found no matching fields for input', diff=delta)
                elif not should_compare:
                    logger.debug('Input delta [%s] is skipped' % delta.path)

        logger.info('All input deltas are matched')
        return StateResult()
