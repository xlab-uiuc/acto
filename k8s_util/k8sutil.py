import ctypes

k8sutil = ctypes.cdll.LoadLibrary('lib/k8sutil.so')
parse = k8sutil.parse
parse.argtypes = [ctypes.c_char_p]
parse.restype = ctypes.c_void_p

parse_output = parse(".47415".encode("utf-8"))
parse_bytes = ctypes.string_at(parse_output)
parse_string = parse_bytes.decode('utf-8')

print(parse_string)

def canonicalizeQuantity(value):
    k8sutil = ctypes.cdll.LoadLibrary('lib/k8sutil.so')
    parse = k8sutil.parse
    parse.argtypes = [ctypes.c_char_p]
    parse.restype = ctypes.c_void_p

    parse_output = parse(str(value).encode("utf-8"))
    parse_bytes = ctypes.string_at(parse_output)
    parse_string = parse_bytes.decode('utf-8')
    return parse_string