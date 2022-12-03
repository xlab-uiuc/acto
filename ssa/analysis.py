import ctypes
import json
import copy

def analyze(project_path: str, seed_type: str, seed_pkg: str) -> dict:
    analysis_lib = ctypes.cdll.LoadLibrary('ssa/libanalysis.so')
    analyze_func = analysis_lib.Analyze
    analyze_func.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
    analyze_func.restype = ctypes.c_void_p

    analysis_result = analyze_func(project_path.encode("utf-8"), seed_type.encode("utf-8"), seed_pkg.encode("utf-8"))
    analysis_result_bytes = ctypes.string_at(analysis_result)
    taint_analysis_result = json.loads(analysis_result_bytes)
    all_fields = copy.deepcopy(taint_analysis_result['usedPaths'])
    tainted_fields = taint_analysis_result['taintedPaths']
    default_value_map = taint_analysis_result['defaultValues']
    field_conditions_list = taint_analysis_result['fieldConditions']

    for tainted_field in tainted_fields:
        try:
            all_fields.remove(tainted_field)

            if len(tainted_field) > 2:
                # only remove subfields if the field is not 'root', 'root.spec'
                for field in all_fields:
                    if is_subfield(tainted_field, field):
                        all_fields.remove(field)
                    elif is_subfield(field, tainted_field):
                        all_fields.remove(field)
        except ValueError:
            continue

    field_conditions_map = {}
    for field_condition_groups in field_conditions_list:
        new_field_condition_group = {}
        new_field_condition_group['type'] = field_condition_groups['type']
        new_field_condition_group['conditions'] = []
        for field_condition_group in field_condition_groups['conditionGroups']:
            new_condition_group = {}
            new_condition_group['type'] = field_condition_group['type']

            new_conditions = []
            for condition in field_condition_group['conditions']:

                if condition['value'] == 'null':
                    value = None
                elif condition['value'] == 'true':
                    value = True
                elif condition['value'] == 'false':
                    value = False
                else:
                    value = condition['value']

                new_condition = {
                    'field': condition['field'][1:],  # remove the leading 'root'
                    'op': condition['op'],
                    'value': value
                }
                new_conditions.append(new_condition)

            new_condition_group['conditions'] = new_conditions
            new_field_condition_group['conditions'].append(new_condition_group)

        field_conditions_map[json.dumps(field_condition_groups['path'][1:])] = new_field_condition_group

    analysis_result = {
        'used_fields': taint_analysis_result['usedPaths'],
        'control_flow_fields': all_fields,
        'default_value_map': default_value_map,
        'field_conditions_map': field_conditions_map,
        'fields_to_k8s_map': taint_analysis_result['fieldToK8sMapping']
    }
    return analysis_result


def is_subfield(subpath: list, path: list) -> bool:
    '''Checks if subpath is a subfield of path
    '''
    if len(path) > len(subpath):
        return False
    for i in range(len(path)):
        if path[i] != subpath[i]:
            return False
    return True


if __name__ == '__main__':
    # print(analyze('/home/tyler/rabbitmq-operator', 'RabbitmqCluster', 'github.com/rabbitmq/cluster-operator/api/v1beta1'))
    # print(analyze('/home/tyler/redis-operator/cmd/redisoperator', 'RedisFailover', 'github.com/spotahome/redis-operator/api/redisfailover/v1'))
    print(analyze('/home/tyler/acto-ops/cass-operator-241e71', 'CassandraDatacenter', 'github.com/k8ssandra/cass-operator/apis/cassandra/v1beta1'))
    # print(analyze('/home/tyler/percona-server-mongodb-operator/cmd/manager', 'PerconaServerMongoDB', 'github.com/percona/percona-server-mongodb-operator/pkg/apis/psmdb/v1'))
    # print(analyze('/home/tyler/zookeeper-operator', 'ZookeeperCluster', 'github.com/pravega/zookeeper-operator/api/v1beta1'))
    # print(analyze('/home/tyler/cockroach-operator/cmd/cockroach-operator', 'CrdbCluster', 'github.com/cockroachdb/cockroach-operator/apis/v1alpha1'))
    # print(analyze('/home/tyler/tidb-operator/cmd/controller-manager', 'TidbCluster', 'github.com/pingcap/tidb-operator/pkg/apis/pingcap/v1alpha1'))
    # print(analyze('/home/tyler/redis-operator-2', 'RedisCluster', 'redis-operator/api/v1beta1'))
