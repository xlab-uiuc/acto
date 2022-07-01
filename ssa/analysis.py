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
    default_value_map = taint_analysis_result['defaultValues']

    for tainted_field in tainted_fields:
        try:
            all_fields.remove(tainted_field)

            if len(tainted_field) > 2:
                # only remove subfields if the field is not 'root', 'root.spec'
                for field in all_fields:
                    if is_subfield(tainted_field, field):
                        all_fields.remove(field)
        except ValueError:
            continue


    analysis_result = {
        'control_flow_fields': all_fields,
        'default_value_map': default_value_map
    }
    return analysis_result


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
    # print(analyze('/home/tyler/cluster-operator', 'RabbitmqCluster', 'github.com/rabbitmq/cluster-operator/api/v1beta1'))
    # print(analyze('/home/tyler/redis-operator/cmd/redisoperator', 'RedisFailover', 'github.com/spotahome/redis-operator/api/redisfailover/v1'))
    print(analyze('/home/tyler/cass-operator', 'CassandraDatacenter', 'github.com/k8ssandra/cass-operator/apis/cassandra/v1beta1'))
    # print(analyze('/home/tyler/percona-server-mongodb-operator/cmd/manager', 'PerconaServerMongoDB', 'github.com/percona/percona-server-mongodb-operator/pkg/apis/psmdb/v1'))
    # print(analyze('/home/tyler/zookeeper-operator', 'ZookeeperCluster', 'github.com/pravega/zookeeper-operator/api/v1beta1'))

    # print(analyze('/home/tyler/cockroach-operator/cmd/cockroach-operator', 'CrdbCluster', 'github.com/cockroachdb/cockroach-operator/apis/v1alpha1'))