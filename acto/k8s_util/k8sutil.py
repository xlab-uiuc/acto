import ctypes
import logging
import os
import re

k8s_value_regex = re.compile(r'^[-+]?((\.[0-9]+)|([0-9]+(\.[0-9]+)?)|([0-9]+\.))(([KMGTPE]i)|([eE][-+]?((\.[0-9]+)|([0-9]+(\.[0-9]+)?)|([0-9]+\.)))|([mnkMGTPE]|))$')


def call_k8s_util(func_name):
    """
    The function will call the function in k8sutil.so with the given name
    parse: canonicalize the quantity string
    doubleIt: double the quantity string
    halfIt: half the quantity string

    @param func_name: function name in k8sutil.so, possible values: parse, doubleIt, halfIt
    @type func_name: str
    @return: the function will return a function that will call the function in k8sutil.so with the given name
    """

    def caller(value) -> (str, bool):
        value = str(value)
        ok = False
        if not k8s_value_regex.fullmatch(value):
            return value, ok
        k8sutil = ctypes.cdll.LoadLibrary(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib/k8sutil.so'))
        func = k8sutil[func_name]
        func.argtypes = [ctypes.c_char_p]
        func.restype = ctypes.c_void_p

        output = func(str(value).encode("utf-8"))
        output_bytes = ctypes.string_at(output)
        result = output_bytes.decode('utf-8')

        if 'INVALID' == result:
            logging.error('the regex for number conversion is incorrect! The input string cannot be parsed')
        else:
            ok = True
        return result, ok

    return caller


def drop_ok(func):
    return lambda value: func(value)[0]


canonicalize_quantity_unformatted = call_k8s_util('parse')
double_quantity = drop_ok(call_k8s_util('doubleIt'))
half_quantity = drop_ok(call_k8s_util('halfIt'))


def canonicalize_quantity(value):
    """
    The function will canonicalize value from kubernetes api (like 1.5Gi) to a float number string (like '1610612736.000')

    @param value: value from kubernetes api
    @return: canonicalized value or the original value if the value cannot be canonicalized
    """
    if not isinstance(value, str):
        return value
    parse_string, ok = canonicalize_quantity_unformatted(value)
    if not ok:
        return parse_string
    return format(float(parse_string), ".3f")
