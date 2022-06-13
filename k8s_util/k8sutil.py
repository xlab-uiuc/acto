import ctypes
import re

def canonicalizeQuantity(value):
    if not isinstance(value, str) or not bool(re.match('^([+-]?[0-9.]+)([eEinumkKMGTP]*[-+]?[0-9]*)$', value)):
        return value
    k8sutil = ctypes.cdll.LoadLibrary('k8s_util/lib/k8sutil.so')
    parse = k8sutil.parse
    parse.argtypes = [ctypes.c_char_p]
    parse.restype = ctypes.c_void_p

    parse_output = parse(str(value).encode("utf-8"))
    parse_bytes = ctypes.string_at(parse_output)
    parse_string = parse_bytes.decode('utf-8')
    return parse_string

if __name__ == '__main__':
    print(canonicalizeQuantity(8080))
    print(canonicalizeQuantity('1Mi'))
    print(canonicalizeQuantity('asd'))