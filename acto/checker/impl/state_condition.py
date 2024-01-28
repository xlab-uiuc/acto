import operator
from functools import reduce

from acto.common import PropertyPath, is_subfield, translate_op


def check_condition(
    snapshot_input: dict, condition: dict, input_delta_path: PropertyPath
) -> bool:
    path = condition["field"]

    # corner case: skip if condition is simply checking if the path is not nil
    if (
        is_subfield(input_delta_path.path, path)
        and condition["op"] == "!="
        and condition["value"] is None
    ):
        return True

    # hack: convert 'INDEX' to int 0
    for i in range(len(path)):
        if path[i] == "INDEX":
            path[i] = 0

    try:
        value = reduce(operator.getitem, path, snapshot_input)
    except (KeyError, TypeError):
        if (
            translate_op(condition["op"]) == operator.eq
            and condition["value"] is None
        ):
            return True
        else:
            return False

    # the condition_value is stored as string in the json file
    condition_value = condition["value"]
    if isinstance(value, int):
        condition_value = (
            int(condition_value) if condition_value is not None else None
        )
    elif isinstance(value, float):
        condition_value = (
            float(condition_value) if condition_value is not None else None
        )
    try:
        return translate_op(condition["op"])(value, condition_value)
    except TypeError:
        return False


def check_condition_group(
    snapshot_input: dict, condition_group: dict, input_delta_path: PropertyPath
) -> bool:
    if "type" in condition_group:
        typ = condition_group["type"]
        if typ == "AND":
            for condition in condition_group["conditions"]:
                if not check_condition_group(
                    snapshot_input, condition, input_delta_path
                ):
                    return False
            return True
        elif typ == "OR":
            for condition in condition_group["conditions"]:
                if check_condition_group(
                    snapshot_input, condition, input_delta_path
                ):
                    return True
            return False
        else:
            raise NotImplementedError
    else:
        return check_condition(
            snapshot_input, condition_group, input_delta_path
        )
