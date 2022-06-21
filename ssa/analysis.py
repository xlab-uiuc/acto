import ctypes
import json

def analyze(project_path: str, seed_type: str, seed_pkg: str) -> dict:
    analysis_lib = ctypes.cdll.LoadLibrary('ssa/analysis.so')
    analyze_func = analysis_lib.Analyze
    analyze_func.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
    analyze_func.restype = ctypes.c_void_p

    analysis_result = analyze_func(project_path.encode("utf-8"), seed_type.encode("utf-8"), seed_pkg.encode("utf-8"))
    analysis_result_bytes = ctypes.string_at(analysis_result)
    return json.loads(analysis_result_bytes)

if __name__ == '__main__':
    print(analyze('/home/tyler/redis-operator/cmd/redisoperator', 'RedisFailover', 'github.com/spotahome/redis-operator/api/redisfailover/v1'))