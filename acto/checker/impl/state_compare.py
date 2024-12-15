import configparser
from typing import Any

from deepdiff.helper import NotPresent

from acto.k8s_util.k8sutil import canonicalize_quantity
from acto.common import flatten_dict


def is_none_or_not_present(value: Any) -> bool:
    """
    Check if value is None or NotPresent
    @param value:
    @return:
    """
    if value is None:
        return True
    if isinstance(value, NotPresent):
        return True
    return False


def is_nullish(value: Any) -> bool:
    """
    Check if value is None, NotPresent, empty string, empty list, empty dict, or 0
    @param value:
    @return:
    """
    if is_none_or_not_present(value):
        return True

    if isinstance(value, str) and value == '':
        return True

    if isinstance(value, int) and value == 0:
        return True

    if isinstance(value, float) and value == 0:
        return True

    if isinstance(value, list) and len(value) == 0:
        return True

    if isinstance(value, dict) and len(value) == 0:
        return True

    return False


def either_is_nullish(left: Any, right: Any) -> bool:
    """
    Check if either left or right is None, NotPresent, empty string, empty list, empty dict, or 0
    @param left:
    @param right:
    @return:
    """
    return is_nullish(left) or is_nullish(right)


def input_is_substring_of_output(input_value: Any, output_value: Any) -> bool:
    # if input is int, then we want exact match to avoid mapping 10 to 1000, 2 to 20, etc.
    if type(input_value) == int and input_value == output_value:
        return True
    if str(input_value).lower() in str(output_value).lower():
        return True


def input_config_is_subset_of_output_config(input_config: Any, output_config: Any) -> bool:
    if isinstance(input_config, str) and isinstance(output_config, str):
        try:
            input_parser = configparser.ConfigParser()
            input_parser.read_string("[ACTO]\n" + input_config)
            if len(input_parser.options("ACTO")) == 0:
                return False

            output_parser = configparser.ConfigParser()
            output_parser.read_string("[ACTO]\n" + output_config)

            for k, v in input_parser.items("ACTO"):
                if output_parser.get("ACTO", k) != v:
                    return False
            return True
        except configparser.Error:
            return False
    return False

def compare_application_config(input_config: Any, output_config: Any) -> bool:
    if isinstance(input_config, dict) and isinstance(output_config, dict):
        try:
            set_input_config = flatten_dict(input_config, ["root"])
            set_output_config = flatten_dict(output_config, ["root"])
            for item in set_input_config:
                if item not in set_output_config:
                    return False
            return True
        except configparser.Error:
            return False
    return False

class CompareMethods:
    def __init__(self, enable_k8s_value_canonicalization=True):
        """
        @param enable_k8s_value_canonicalization: if True, then canonicalize_quantity() will be used to canonicalize values
        """
        self.custom_equality_checkers = []
        self.enable_k8s_value_canonicalization = enable_k8s_value_canonicalization
        if enable_k8s_value_canonicalization:
            self.custom_equality_checkers.extend([input_is_substring_of_output, input_config_is_subset_of_output_config])

    def equals(self, left: Any, right: Any) -> bool:
        """
        Compare two values. If the values are not equal, then try to use custom_equality_checkers to see if they are
        @param left:
        @param right:
        @return:
        """
        if left == right:
            return True
        else:
            for equals in self.custom_equality_checkers:
                if equals(left, right):
                    return True
            return False

    def equals_after_transform(self, in_prev, in_curr, out_prev, out_curr) -> bool:
        # parse the argument: if a number, convert it to pure decimal format (i.e. 1e3 -> 1000); otherwise unchanged
        in_prev, in_curr, out_prev, out_curr = self.transform_field_value(in_prev, in_curr, out_prev, out_curr)

        # try every compare method possible
        if self.equals(in_prev, out_prev) and self.equals(in_curr, out_curr):
            return True
        if either_is_nullish(in_prev, out_prev) and self.equals(in_curr, out_curr):
            return True
        if self.equals(in_prev, out_prev) and either_is_nullish(in_curr, out_curr):
            return True
        return False

    def transform_field_value(self, in_prev, in_curr, out_prev, out_curr):
        """
        Transform the field value if necessary
        only one transformer is allowed for each field

        However, currently we only support one transformer. So we just apply the transformer to all fields.

        @param in_prev:
        @param in_curr:
        @param out_prev:
        @param out_curr:
        @return: transformed in_prev, in_curr, out_prev, out_curr
        """
        if self.enable_k8s_value_canonicalization:
            in_prev = canonicalize_quantity(in_prev)
            in_curr = canonicalize_quantity(in_curr)
            out_prev = canonicalize_quantity(out_prev)
            out_curr = canonicalize_quantity(out_curr)

        # return original values
        return in_prev, in_curr, out_prev, out_curr

class CustomCompareMethods():
    def __init__(self):
        self.custom_equality_checkers = []
        self.custom_equality_checkers.extend([compare_application_config])
    
    def equals(self, left: Any, right: Any) -> bool:
        """
        Compare two values. If the values are not equal, then try to use custom_equality_checkers to see if they are
        @param left:
        @param right:
        @return:
        """
        if left == right:
            return True
        else:
            for equals in self.custom_equality_checkers:
                if equals(left, right):
                    return True
            return False
