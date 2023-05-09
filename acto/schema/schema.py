from acto.utils import get_thread_logger
from .base import BaseSchema
from .string import StringSchema
from .number import NumberSchema
from .opaque import OpaqueSchema
from .boolean import BooleanSchema
from .integer import IntegerSchema

def extract_schema(path: list, schema: dict) -> BaseSchema:
    from .object import ObjectSchema
    from .anyof import AnyOfSchema
    from .oneof import OneOfSchema
    from .array import ArraySchema
    logger = get_thread_logger(with_prefix=True)

    if 'anyOf' in schema:
        return AnyOfSchema(path, schema)
    elif 'oneOf' in schema:
        return OneOfSchema(path, schema)

    if 'type' not in schema:
        if 'properties' in schema:
            return ObjectSchema(path, schema)
        else:
            logger.warn('No type found in schema: %s' % str(schema))
            return OpaqueSchema(path, schema)
    t = schema['type']
    if isinstance(t, list):
        if 'null' in t:
            t.remove('null')
        if len(t) == 1:
            t = t[0]

    if t == 'string':
        return StringSchema(path, schema)
    elif t == 'number':
        return NumberSchema(path, schema)
    elif t == 'integer':
        return IntegerSchema(path, schema)
    elif t == 'boolean':
        return BooleanSchema(path, schema)
    elif t == 'array':
        return ArraySchema(path, schema)
    elif t == 'object':
        return ObjectSchema(path, schema)
    else:
        logger.error('Unsupported type %s' % t)
        return None


# if __name__ == '__main__':
#     with open('data/rabbitmq-operator/operator.yaml',
#               'r') as operator_yaml:
#         parsed_operator_documents = yaml.load_all(operator_yaml, Loader=yaml.FullLoader)
#         for document in parsed_operator_documents:
#             if document['kind'] == 'CustomResourceDefinition':
#                 spec_schema = ObjectSchema(
#                     ['root'], document['spec']['versions'][0]['schema']['openAPIV3Schema']
#                     ['properties']['spec'])
#                 print(str(spec_schema))
#                 print(spec_schema.gen())
#                 print(spec_schema.num_fields())
#                 for k, v in spec_schema.properties.items():
#                     print('%s has %d fields' % (k, v.num_fields()))
#                 print(spec_schema.num_cases())

#                 schema_list = spec_schema.get_all_schemas()
#                 test_plan = {}
#                 for schema in schema_list:
#                     test_plan[str(schema.path)] = schema.test_cases()
#                 with open('test_plan.json', 'w') as fout:
#                     json.dump(test_plan, fout, cls=ActoEncoder, indent=4)

    # ss = StringSchema(None, {"type": "string"})
    # print(ss.gen())

    # schemas = {
    #     'configmap': '/home/tyler/k8s_resources/configmap-v1.json',
    #     'cronjob': '/home/tyler/k8s_resources/cronjob-batch-v2alpha1.json',
    #     'deployment': '/home/tyler/k8s_resources/deployment-apps-v1.json',
    #     'ingress': '/home/tyler/k8s_resources/ingress-networking-v1.json',
    #     'pvc': '/home/tyler/k8s_resources/persistentvolumeclaim-v1.json',
    #     'pdb': '/home/tyler/k8s_resources/poddisruptionbudget-policy-v1beta1.json',
    #     'pod': '/home/tyler/k8s_resources/pod-v1.json',
    #     'secret': '/home/tyler/k8s_resources/secret-v1.json',
    #     'service': '/home/tyler/k8s_resources/service-v1.json',
    #     'statefulset': '/home/tyler/k8s_resources/statefulset-apps-v1.json',
    # }

    # resource_num_fields = {}

    # for resource, schema_path in schemas.items():
    #     with open(schema_path, 'r') as schema_file:
    #         schema = json.load(schema_file)
    #         spec_schema = extract_schema([], schema)

    #         resource_num_fields[resource] = len(spec_schema.get_all_schemas()[0])

    # print(resource_num_fields)

    # used_resource_in_operators = {
    #     'cass-operator': [
    #         'configmap', 'deployment', 'pvc', 'pdb', 'secret', 'service', 'statefulset'
    #     ],
    #     'cockroach-operator': [
    #         'configmap', 'deployment', 'pvc', 'pdb', 'secret', 'service', 'statefulset'
    #     ],
    #     'knative-operator': ['configmap', 'deployment', 'pdb', 'secret', 'service'],
    #     'mongodb-community-operator': [
    #         'configmap', 'deployment', 'pvc', 'secret', 'service', 'statefulset'
    #     ],
    #     'percona-server-mongodb-operator': [
    #         'configmap', 'deployment', 'ingress', 'pvc', 'pdb', 'secret', 'service', 'statefulset'
    #     ],
    #     'percona-xtradb-cluster-operator': [
    #         'configmap', 'deployment', 'pvc', 'pdb', 'secret', 'service', 'statefulset'
    #     ],
    #     'rabbitmq-operator': ['configmap', 'deployment', 'pvc', 'secret', 'service', 'statefulset'],
    #     'redis-operator': ['configmap', 'deployment', 'pdb', 'secret', 'service', 'statefulset'],
    #     'redis-ot-operator': ['configmap', 'deployment', 'pvc', 'secret', 'service', 'statefulset'],
    #     'tidb-operator': ['configmap', 'deployment', 'pvc', 'secret', 'service', 'statefulset'],
    #     'zookeeper-operator': [
    #         'configmap', 'deployment', 'pvc', 'pdb', 'secret', 'service', 'statefulset'
    #     ],
    # }

    # for operator, resources in used_resource_in_operators.items():
    #     num_system_fields = 0
    #     for resource in resources:
    #         num_system_fields += resource_num_fields[resource]

    #     print('%s has %d system fields' % (operator, num_system_fields))
        # print(num_system_fields)

    # with open('data/cass-operator/bundle.yaml',
    #           'r') as operator_yaml:
    #     parsed_operator_documents = yaml.load_all(operator_yaml, Loader=yaml.FullLoader)
    #     for document in parsed_operator_documents:
    #         if document['kind'] == 'CustomResourceDefinition':
    #             spec_schema = ObjectSchema(
    #                 ['root'], document['spec']['versions'][0]['schema']['openAPIV3Schema']
    #                 ['properties']['spec'])
    #             print(spec_schema.num_fields())
    #             for k, v in spec_schema.properties.items():
    #                 print('%s has %d fields' % (k, len(v.get_all_schemas()[0])))