from typing import Dict
from common import is_subfield

from schema import ArraySchema, ObjectSchema, extract_schema


def get_all_predicates(field_condition: Dict):
    predicates = set()
    if 'type' in field_condition:
        for condition in field_condition['conditions']:
            predicates.update(get_all_predicates(condition))
    else:
        field = field_condition['field']
        op = field_condition['op']
        value = field_condition['value']
        # print(f'Found a field condition: {field}')
        if value != None:
            # print(f'Found a field condition: {field} {op} {value}')
            predicates.add(json.dumps(field))
    return predicates

def helper(schema: ObjectSchema, field_conditions_map: Dict):
    if not isinstance(schema, ObjectSchema):
        return
    for key, value in schema.get_properties().items():
        if key == 'enabled':
            normal_schemas, l2, l3 = schema.get_all_schemas()
            for s in normal_schemas:
                encode_dependency(s.path, schema.path + [key], field_conditions_map)
            for s in l2:
                encode_dependency(s.path, schema.path + [key], field_conditions_map)
            for s in l3:
                encode_dependency(s.path, schema.path + [key], field_conditions_map)
        if isinstance(value, ObjectSchema):
            helper(value, field_conditions_map)
        elif isinstance(value, ArraySchema):
            helper(value.get_item_schema(), field_conditions_map)

def encode_dependency(depender: list, dependee: list, field_conditions_map: Dict):
    '''Encode dependency of dependant on dependee

    Args:
        depender: path of the depender
        dependee: path of the dependee
    '''

    # print(f"Found dependency: {depender} -> {dependee}")
    encoded_path = json.dumps(depender)
    if encoded_path not in field_conditions_map:
        field_conditions_map[encoded_path] = {'conditions': [], 'type': 'AND'}

    # Add dependency to the subfields, idealy we should have a B tree for this
    for key, value in field_conditions_map.items():
        path = json.loads(key)
        if is_subfield(path, depender):
            value['conditions'].append({
                'type': 'OR',
                'conditions': [{
                    'field': dependee,
                    'op': '==',
                    'value': True
                }]
            })


if __name__ == '__main__':
    import json
    import glob
    import sys
    sys.path.append('..')
    import known_schemas

    files = glob.glob('data/*/context.json')
    files.sort()
    for file in files:
        print(f'Inspecting dependency for {file}')
        predicates = set()
        fields_with_dependency = set()
        with open(file, 'r') as f:
            context = json.load(f)
            crd = extract_schema(
                [], context['crd']['body']['spec']['versions'][-1]['schema']['openAPIV3Schema'])
            field_conditions_map = context['analysis_result']['field_conditions_map']
            # field_conditions_map = {}
            helper(crd['spec'], field_conditions_map)
            for field, field_condition in field_conditions_map.items():
                field_predicate = get_all_predicates(field_condition)
                predicates.update(field_predicate)
                if len(field_predicate) > 0:
                    fields_with_dependency.add(field)

        print(f"Found {len(predicates)} predicates")
        print(f"Found {len(fields_with_dependency)} fields with dependency")
