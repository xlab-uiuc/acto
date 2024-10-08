"""Common functions and classes used by acto"""

import json
import operator
import random
import re
import string
from typing import Any, Sequence, Tuple, TypeAlias, Union

import deepdiff.model as deepdiff_model
import kubernetes
import pydantic
from deepdiff.helper import NotPresent
from typing_extensions import Self

from acto.utils.thread_logger import get_thread_logger

PathSegment: TypeAlias = Union[str, int]


class PropertyPath(pydantic.BaseModel):
    """Path of a field in a dict"""

    path: list[PathSegment]

    def __init__(self, path: Sequence[PathSegment]) -> None:
        """Override constructor to allow positional argument"""
        super().__init__(path=path)

    def __eq__(self, other):
        return isinstance(other, PropertyPath) and self.path == other.path

    def __hash__(self):
        return hash(tuple(self.path))

    def __str__(self):
        return json.dumps(self.path)

    def __repr__(self):
        return str(self)

    def __getitem__(self, item: int):
        return self.path[item]

    def __len__(self):
        return len(self.path)

    def __contains__(self, item: PathSegment):
        return item in self.path

    @classmethod
    def from_json_patch_string(cls, patch_path: str) -> Self:
        """Convert a JSON patch string to a PropertyPath object"""
        items = patch_path.split("/")
        return cls(items[1:])


class HashableDict(dict):
    """Hashable dict"""

    def __hash__(self):
        return hash(json.dumps(self, sort_keys=True))


class HashableList(list):
    """Hashable list"""

    def __hash__(self):
        return hash(json.dumps(self, sort_keys=True))


class Diff(pydantic.BaseModel):
    """Class for storing the diff between two values"""

    prev: Any = pydantic.Field(description="Previous value")
    curr: Any = pydantic.Field(description="Current value")
    path: PropertyPath = pydantic.Field(description="Path of the Diff")

    @pydantic.model_serializer
    def to_dict(self) -> dict:
        """serialize Diff object"""
        return {"prev": self.prev, "curr": self.curr, "path": self.path}

    @staticmethod
    def from_dict(obj: dict) -> "Diff":
        """deserialize Diff object"""
        return Diff(**obj)

    def __eq__(self, other):
        def value_eq_with_not_present(a: Any, b: Any) -> bool:
            if isinstance(a, NotPresent):
                return isinstance(b, NotPresent)
            return a == b

        return (
            value_eq_with_not_present(self.prev, other.prev)
            and value_eq_with_not_present(self.curr, other.curr)
            and self.path == other.path
        )


def flatten_list(l: list, curr_path: list) -> list:
    """Convert list into list of tuples (path, value)

    Args:
        l: list to be flattened
        curr_path: current path of d

    Returns:
        list of Tuples (path, basic value)
    """
    result = []
    for idx, value in enumerate(l):
        path = curr_path + [idx]
        if isinstance(value, dict):
            result.extend(flatten_dict(value, path))
        elif isinstance(value, list):
            # do not flatten empty list
            if not value:
                result.append((path, value))
            else:
                result.extend(flatten_list(value, path))
        else:
            result.append((path, value))
    return result


def flatten_dict(d: dict, curr_path: list) -> list:
    """Convert dict into list of tuples (path, value)

    Args:
        d: dict to be flattened
        curr_path: current path of d

    Returns:
        list of Tuples (path, basic value)
    """
    result = []
    for key, value in d.items():
        path = curr_path + [key]
        if isinstance(value, dict):
            # do not flatten empty dict
            if value == {}:
                result.append((path, value))
            else:
                result.extend(flatten_dict(value, path))
        elif isinstance(value, list):
            result.extend(flatten_list(value, path))
        else:
            result.append((path, value))
    return result


def postprocess_diff(
    diff: deepdiff_model.TreeResult,
) -> dict[str, dict[str, Diff]]:
    """Postprocess diff from DeepDiff tree view"""

    diff_dict: dict[str, dict[str, Diff]] = {}
    for category, changes in diff.items():
        diff_dict[category] = {}
        for change in changes:
            # Heuristic
            # When an entire dict/list is added or removed, flatten this
            # dict/list to help field matching and value comparison in oracle

            if (isinstance(change.t1, (dict, list))) and (
                change.t2 is None or isinstance(change.t2, NotPresent)
            ):
                if isinstance(change.t1, dict):
                    flattened_changes = flatten_dict(change.t1, [])
                else:
                    flattened_changes = flatten_list(change.t1, [])
                for path, value in flattened_changes:
                    if value is None or isinstance(value, NotPresent):
                        continue
                    str_path = change.path()
                    for i in path:
                        str_path += f"[{i}]"
                    diff_dict[category][str_path] = Diff(
                        prev=value,
                        curr=change.t2,
                        path=PropertyPath(
                            change.path(output_format="list") + path
                        ),
                    )
            elif (isinstance(change.t2, (dict, list))) and (
                change.t1 is None or isinstance(change.t1, NotPresent)
            ):
                if isinstance(change.t2, dict):
                    flattened_changes = flatten_dict(change.t2, [])
                else:
                    flattened_changes = flatten_list(change.t2, [])
                for path, value in flattened_changes:
                    if value is None or isinstance(value, NotPresent):
                        continue
                    str_path = change.path()
                    for i in path:
                        str_path += f"[{i}]"
                    diff_dict[category][str_path] = Diff(
                        prev=change.t1,
                        curr=value,
                        path=PropertyPath(
                            change.path(output_format="list") + path
                        ),
                    )
            else:
                diff_dict[category][change.path()] = Diff(
                    prev=change.t1,
                    curr=change.t2,
                    path=PropertyPath(change.path(output_format="list")),
                )
    return diff_dict


def invalid_input_message_regex(log_msg: list[str]) -> bool:
    """Returns if the log shows the input is invalid

    Args:
        log_msg: message body of the log

    Returns:
        Tuple(bool, list):
            - if the log_msg indicates the input delta is invalid
            - when log indicates invalid input: the responsible field path for the invalid input
    """
    logger = get_thread_logger(with_prefix=True)

    for log_line in log_msg:
        for regex in INVALID_INPUT_LOG_REGEX:
            if re.search(regex, log_line):
                logger.info(
                    "Recognized invalid input through regex: %s", log_line
                )
                return True

    return False


def invalid_input_message(
    log_msg: str, input_delta: dict[str, dict[str, Diff]]
) -> Tuple[bool, PropertyPath]:
    """Returns if the log shows the input is invalid

    Args:
        log_msg: message body of the log
        input_delta: the input delta we applied to the CR

    Returns:
        Tuple(bool, list):
            - if the log_msg indicates the input delta is invalid
            - when log indicates invalid input: the responsible field path for the invalid input
    """
    logger = get_thread_logger(with_prefix=True)
    is_invalid = False

    for regex in INVALID_INPUT_LOG_REGEX:
        if re.search(regex, log_msg):
            logger.info("Recognized invalid input through regex: %s", log_msg)
            is_invalid = True
            break

    # Check if the log line contains the field or value
    # If so, also return True

    for delta_category in input_delta.values():
        for delta in delta_category.values():
            if isinstance(delta.path[-1], str) and delta.path[-1] in log_msg:
                logger.info(
                    "Recognized invalid input through field [%s] in error message: %s",
                    delta.path[-1],
                    log_msg,
                )
                return True, delta.path

            # if delta.curr is an int, we do exact match to avoid matching a short
            # int (e.g. 1) to a log line and consider the int as invalid input
            if isinstance(delta.curr, int) and len(str(delta.curr)) > 1:
                for item in log_msg.split(" "):
                    if item == str(delta.curr):
                        logger.info(
                            "Recognized invalid input through value [%s] in error message: %s",
                            delta.curr,
                            log_msg,
                        )
                        return True, delta.path
            elif len(str(delta.curr)) > 1 and str(delta.curr) in log_msg:
                logger.info(
                    "Recognized invalid input through value [%s] in error message: %s",
                    str(delta.curr),
                    log_msg,
                )
                return True, delta.path

    return is_invalid, PropertyPath([])


def canonicalize(s: str):
    """Replace all upper case letters with _lowercase"""
    if isinstance(s, int):
        return "ITEM"
    s = str(s)
    return re.sub(r"(?=[A-Z])", "_", s).lower()


def is_subfield(subpath: list, path: list) -> bool:
    """Checks if subpath is a subfield of path"""
    if len(path) > len(subpath):
        return False
    for i in range(len(path)):
        if path[i] != subpath[i]:
            return False
    return True


def random_string(_: int):
    """Generate random string with length n"""
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(10))


def translate_op(input_op: str):
    """Translate operator from string to function"""
    if input_op == "!=":
        return operator.ne
    if input_op == "==":
        return operator.eq
    if input_op == "<=":
        return operator.le
    if input_op == "<":
        return operator.lt
    if input_op == ">=":
        return operator.ge
    if input_op == ">":
        return operator.gt

    raise ValueError(f"Unknown operator: {input_op}")


EXCLUDE_PATH_REGEX = [
    r"managed_fields",
    r"managedFields",
    r"last\-applied\-configuration",
    r"generation",
    r"resourceVersion",
    r"resource_version",
    r"observed_generation",
    r"observedGeneration",
    r"control\-plane\.alpha\.kubernetes\.io\/leader",
]

EXCLUDE_ERROR_REGEX = [
    r"the object has been modified; please apply your changes to the latest version and try again",
    r"incorrect status code of 500 when calling endpoint",
    r"failed to ensure version, running with default",
    r"create issuer: no matches for kind",
    r"failed to run smartUpdate",
    r"dial: ping mongo",
    r"pod is not running",
    r"failed to sync(.)*status",
    r"can't failover, requeuing",
    r"Secret (.)* not found",
    r"failed to get proxySQL db",
    r"{\"severity\":\"INFO\"",
    r"{\"level\":\"info\"",
    r"PD failover replicas \(0\) reaches the limit \(0\)",
]

INVALID_INPUT_LOG_REGEX = [
    r"invalid",
    r"not valid",
    r"no valid",
    r"unsupported",
    r"but expected",
    r"are not available",
    r"must include",
    r"must have",
    r"can't be empty",
]

GENERIC_FIELDS = [
    r"^name$",
    r"^effect$",
    r"^key$",
    r"^operator$",
    r"\d",
    r"^claimName$",
    r"^host$",
    r"^type$",
]


def kubernetes_client(
    kubeconfig: str, context_name: str
) -> kubernetes.client.ApiClient:
    """Create a kubernetes client from kubeconfig and context name"""
    return kubernetes.config.kube_config.new_client_from_config(
        config_file=kubeconfig, context=context_name
    )


def print_event(msg: str):
    """Print event to stdout"""
    print(msg)
