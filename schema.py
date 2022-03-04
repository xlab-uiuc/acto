import logging
import yaml
from copy import deepcopy


class StringSchema:
    '''Representation of a string node
    
    It handles
        - minLength
        - maxLength
        - pattern
    '''
    def __init__(self, schema: dict) -> None:
        self.min_length = None if 'minLength' not in schema else schema['minLength']
        self.max_length = None if 'maxLength' not in schema else schema['maxLength']
        self.pattern = None if 'pattern' not in schema else schema['pattern']

    def __str__(self) -> str:
        return 'String'

class NumberSchema:
    '''Representation of a number node
    
    It handles
        - minimum
        - maximum
        - exclusiveMinimum
        - exclusiveMaximum
        - multipleOf
    '''
    def __init__(self, schema: dict) -> None:
        self.minimum = None if 'minimum' not in schema else schema['minimum']
        self.maximum = None if 'maximum' not in schema else schema['maximum']
        self.exclusive_minimum = None if 'exclusiveMinimum' not in schema else schema['exclusiveMinimum']
        self.exclusive_maximum = None if 'exclusiveMaximum' not in schema else schema['exclusiveMaximum']
        self.multiple_of = None if 'multipleOf' not in schema else schema['multipleOf']

    def __str__(self) -> str:
        return 'Number'

class IntegerSchema(NumberSchema):
    def __init__(self, schema: dict) -> None:
        super().__init__(schema)

    def __str__(self) -> str:
        return 'Integer'

class ObjectSchema:
    '''Representation of an object node
    
    It handles
        - properties
        - additionalProperties
        - required
        - minProperties
        - maxProperties
    TODO:
        - dependencies
        - patternProperties
        - regexp
    '''
    def __init__(self, schema: dict) -> None:
        self.children = {}
        self.additional_properties = None
        self.required = []
        if 'properties' in schema:
            for property_key, property_schema in schema['properties'].items():
                print(property_key)
                self.children[property_key] = schema_node(property_schema)
        if 'additionalProperties' in schema:
            self.additional_properties = schema_node(schema['additionalProperties'])
        if 'required' in schema:
            self.required = schema['required']
        if 'minProperties' in schema:
            self.min_properties = schema['minProperties']
        if 'maxProperties' in schema:
            self.max_properties = schema['maxProperties']

    def get_child_schema(self, key):
        if key in self.children:
            return self.children[key]
        elif self.additional_properties != None:
            return self.additional_properties
        else:
            raise TypeError

    def __str__(self) -> str:
        ret = '{'
        for k, v in self.children.items():
            ret += str(k)
            ret += ': '
            ret += str(v)
            ret += ', '
        ret += '}'
        return ret

class ArraySchema:
    '''Representation of an array node
    
    It handles
        - minItems
        - maxItems
        - exclusiveMinimum
        - exclusiveMaximum
    TODO:
        - multipleOf
    '''

    def __init__(self, schema: dict) -> None:
        self.item_schema = schema_node(schema['items'])
        self.min_items = None if 'minItems' not in schema else schema['minItems']
        self.max_items = None if 'maxItems' not in schema else schema['maxItems']
        self.exclusive_minimum = None if 'exclusiveMinimum' not in schema else schema['exclusiveMinimum']
        self.exclusive_maximum = None if 'exclusiveMaximum' not in schema else schema['exclusiveMaximum']

    def item_schema(self):
        return self.item_schema

    def __str__(self) -> str:
        return 'Array'

class AnyofSchema:

    def __init__(self, schema) -> None:
        self.possibilities = []
        for i in schema['anyOf']:
            base_schema = deepcopy(schema)
            del base_schema['anyOf']
            base_schema.update(i)
            self.possibilities.append(schema_node(base_schema))

    def __str__(self) -> str:
        ret = '['
        for i in self.possibilities:
            ret += str(i)
            ret += ', '
        ret += ']'
        return ret

class BooleanSchema:
    def __init__(self, schema: dict) -> None:
        pass

    def __str__(self) -> str:
        return 'boolean'

def schema_node(schema: dict) -> object:
    if 'anyOf' in schema and 'type' not in schema:
        return AnyofSchema(schema)
    t = schema['type']
    if t == 'string':
        return StringSchema(schema)
    elif t == 'number':
        return NumberSchema(schema)
    elif t == 'integer':
        return IntegerSchema(schema)
    elif t == 'boolean':
        return BooleanSchema(schema)
    elif t == 'array':
        return ArraySchema(schema)
    elif t == 'object':
        return ObjectSchema(schema)
    else:
        logging.error('Unsupported type %s' % t)
        return None


if __name__ == '__main__':
    with open('data/rabbitmq-operator/operator.yaml','r') as operator_yaml:
        parsed_operator_documents = yaml.load_all(operator_yaml,
                                                  Loader=yaml.FullLoader)
        for document in parsed_operator_documents:
            if document['kind'] == 'CustomResourceDefinition':
                spec_schema = ObjectSchema(document['spec']['versions'][0]['schema']['openAPIV3Schema']['properties']['spec'])
                print(str(spec_schema))