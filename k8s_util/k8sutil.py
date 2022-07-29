import ctypes
import re
import logging

def canonicalizeQuantity(value):
    if not isinstance(value, str) or not bool(re.match('^[-+]?((\.[0-9]+)|([0-9]+(\.[0-9]+)?)|([0-9]+\.))(([KMGTPE]i)|([eE][-+]?((\.[0-9]+)|([0-9]+(\.[0-9]+)?)|([0-9]+\.)))|([mnkMGTPE]|))$', value)):
        return value
    k8sutil = ctypes.cdll.LoadLibrary('k8s_util/lib/k8sutil.so')
    parse = k8sutil.parse
    parse.argtypes = [ctypes.c_char_p]
    parse.restype = ctypes.c_void_p
    # print(str(value).encode("utf-8"))
    parse_output = parse(str(value).encode("utf-8"))
    parse_bytes = ctypes.string_at(parse_output)
    parse_string = parse_bytes.decode('utf-8')
    if 'INVALID' == parse_string:
        logging.error('the regex for number conversion is incorrect! The input string cannot be parsed')
        return parse_string
    return format(float(parse_string), ".3f")
    

if __name__ == '__main__':
    # print(canonicalizeQuantity('172.18.0.4'))
    # print(canonicalizeQuantity('1Mi'))
    # print(canonicalizeQuantity('asd'))
    # for i in ["+.9", "-.484785E-7466", "900m", "0"]:
    #     print(canonicalizeQuantity(i))
    # print(canonicalizeQuantity('-.298Mi')) # -312474
    # print(canonicalizeQuantity('-312475648m')) # -312476
    # print(canonicalizeQuantity('-.01Ki'))
    # print(canonicalizeQuantity('.01Ki'))
    # assert(float(canonicalizeQuantity('-.484785E-7466')) == float(canonicalizeQuantity('0')))
    # print(canonicalizeQuantity('+4678410156.347680E+.6994785'))
    # print(canonicalizeQuantity("+838612.516637636"))
    # print(canonicalizeQuantity("838612517m"))
    # assert(canonicalizeQuantity("+838612.516637636") == canonicalizeQuantity("838612517m"))
    # print(canonicalizeQuantity('+099'))
    # print(canonicalizeQuantity('99'))
    print(canonicalizeQuantity(".2316344e999842"))
    # print(canonicalizeQuantity("-92743e6047801799")) # crash