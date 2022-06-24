import ctypes
import json

def analyze(project_path: str, seed_type: str, seed_pkg: str) -> dict:
    analysis_lib = ctypes.cdll.LoadLibrary('ssa/libanalysis.so')
    analyze_func = analysis_lib.Analyze
    analyze_func.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
    analyze_func.restype = ctypes.c_void_p

    analysis_result = analyze_func(project_path.encode("utf-8"), seed_type.encode("utf-8"), seed_pkg.encode("utf-8"))
    analysis_result_bytes = ctypes.string_at(analysis_result)
    taint_analysis_result = json.loads(analysis_result_bytes)
    all_fields = taint_analysis_result['usedPaths']
    tainted_fields = taint_analysis_result['taintedPaths']

    for tainted_field in tainted_fields:
        try:
            all_fields.remove(tainted_field)
            for field in all_fields:
                if is_subfield(tainted_field, field):
                    all_fields.remove(field)
        except ValueError:
            continue
    return all_fields


def is_subfield(path: list, subpath: list) -> bool:
    '''Checks if subpath is a subfield of path
    '''
    if len(path) > len(subpath):
        return False
    for i in range(len(path)):
        if path[i] != subpath[i]:
            return False
    return True


if __name__ == '__main__':
    print(analyze('/home/tyler/redis-operator/cmd/redisoperator', 'RedisFailover', 'github.com/spotahome/redis-operator/api/redisfailover/v1'))