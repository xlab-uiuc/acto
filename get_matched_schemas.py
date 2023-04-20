import inspect
import known_schemas
from known_schemas import *
from known_schemas.base import K8sSchema


def field_matched(schema: ObjectSchema, k8s_schema: K8sSchema) -> bool:
    if not isinstance(schema, ObjectSchema):
        return False
    for property_name in schema.properties:
        if property_name == "apiVersion":
            # avoid matching if it is a Kind, which is too generic
            return False
        if property_name != "enabled" and property_name not in k8s_schema.fields:
            return False
    return True


def find_matched_schema(schema: BaseSchema) -> List[List[str]]:
    matched_schemas = []
    for name, obj in inspect.getmembers(known_schemas):
        if inspect.isclass(obj) and issubclass(obj, K8sSchema):
            if hasattr(obj, 'fields') and isinstance(schema, ObjectSchema):
                if field_matched(schema, obj):
                    matched_schemas.append(list(schema.path))
                    return matched_schemas
    if isinstance(schema, ObjectSchema):
        for sub_schema in schema.properties.values():
            matched_schemas.extend(find_matched_schema(sub_schema))
    elif isinstance(schema, ArraySchema):
        matched_schemas.extend(find_matched_schema(schema.get_item_schema()))

    return matched_schemas


def get_testcase_breakdown():
    for name, obj in inspect.getmembers(known_schemas):
        if inspect.isclass(obj) and issubclass(obj, K8sSchema):
            for _, class_member in inspect.getmembers(obj):
                if class_member == K8sInvalidTestCase:
                    print(name)


if __name__ == '__main__':
    import json
    import glob
    import sys
    sys.path.append('..')
    import known_schemas

    files = glob.glob('data/*/context.json')
    files.sort()
    for file in files:
        with open(file, 'r') as f:
            context = json.load(f)
            crd = extract_schema(
                [], context['crd']['body']['spec']['versions'][-1]['schema']['openAPIV3Schema'])
            print(f'CRD: {type(crd)}')
            paths = find_matched_schema(crd['spec'])

            print("Matched schemas for %s:" % file)
            for schema in paths:
                print(f"known_schemas.K8sField({schema}),")

            print()