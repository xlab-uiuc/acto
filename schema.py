import logging
import yaml
from copy import deepcopy
import random
from abc import abstractmethod
import exrex


class BaseSchema:
    '''Base class for schemas
    
    Handles some keywords used for any types
    '''

    def __init__(self, schema) -> None:
        self.default = None if 'default' not in schema else schema['default']
        self.enum = None if 'enum' not in schema else schema['enum']

    @abstractmethod
    def gen(self):
        return None


class StringSchema(BaseSchema):
    '''Representation of a string node
    
    It handles
        - minLength
        - maxLength
        - pattern
    '''
    default_max_length = 10

    def __init__(self, schema: dict) -> None:
        super().__init__(schema)
        self.min_length = None if 'minLength' not in schema else schema[
            'minLength']
        self.max_length = self.default_max_length if 'maxLength' not in schema else schema[
            'maxLength']
        self.pattern = None if 'pattern' not in schema else schema['pattern']

    def __str__(self) -> str:
        return 'String'

    def gen(self):
        # TODO: Use minLength: the exrex does not support minLength
        if self.enum != None:
            return random.choice(self.enum)
        if self.pattern != None:
            return exrex.getone(self.pattern, self.max_length)
        return 'random'


class NumberSchema(BaseSchema):
    '''Representation of a number node
    
    It handles
        - minimum
        - maximum
        - exclusiveMinimum
        - exclusiveMaximum
        - multipleOf
    '''
    default_minimum = 0
    default_maximum = 5

    def __init__(self, schema: dict) -> None:
        super().__init__(schema)
        self.minimum = self.default_minimum if 'minimum' not in schema else schema['minimum']
        self.maximum = self.default_maximum if 'maximum' not in schema else schema['maximum']
        self.exclusive_minimum = None if 'exclusiveMinimum' not in schema else schema[
            'exclusiveMinimum']
        self.exclusive_maximum = None if 'exclusiveMaximum' not in schema else schema[
            'exclusiveMaximum']
        self.multiple_of = None if 'multipleOf' not in schema else schema[
            'multipleOf']

    def __str__(self) -> str:
        return 'Number'

    def gen(self):
        # TODO: Use exclusive_minimum, exclusive_maximum, multiple_of
        if self.enum != None:
            return random.choice(self.enum)
        return random.uniform(self.minimum, self.maximum)


class IntegerSchema(NumberSchema):
    '''Special case of NumberSchema'''

    def __init__(self, schema: dict) -> None:
        super().__init__(schema)

    def __str__(self) -> str:
        return 'Integer'

    def gen(self):
        # TODO: Use exclusive_minimum, exclusive_maximum
        if self.enum != None:
            return random.choice(self.enum)
        elif self.multiple_of != None:
            return random.randrange(self.minimum, self.maximum+1, self.multiple_of)
        else:
            return random.randint(self.minimum, self.maximum)


class ObjectSchema(BaseSchema):
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
        super().__init__(schema)
        self.children = {}
        self.additional_properties = None
        self.required = []
        if 'properties' in schema:
            for property_key, property_schema in schema['properties'].items():
                print(property_key)
                self.children[property_key] = schema_node(property_schema)
        if 'additionalProperties' in schema:
            self.additional_properties = schema_node(
                schema['additionalProperties'])
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

    def gen(self):
        # TODO: Use constraints: required, minProperties, maxProperties
        if self.enum != None:
            return random.choice(self.enum)
        result = {}
        for k, v in self.children.items():
            if random.uniform(0, 1) < 0.1 and k not in self.required:
                # 10% of the chance this child will be null
                result[k] = None
            else:
                result[k] = v.gen()
        return result


class ArraySchema(BaseSchema):
    '''Representation of an array node
    
    It handles
        - minItems
        - maxItems
        - exclusiveMinimum
        - exclusiveMaximum
    TODO:
        - multipleOf
    '''
    default_min_items = 0
    default_max_items = 5

    def __init__(self, schema: dict) -> None:
        super().__init__(schema)
        self.item_schema = schema_node(schema['items'])
        self.min_items = self.default_min_items if 'minItems' not in schema else schema['minItems']
        self.max_items = self.default_max_items if 'maxItems' not in schema else schema['maxItems']
        self.exclusive_minimum = None if 'exclusiveMinimum' not in schema else schema[
            'exclusiveMinimum']
        self.exclusive_maximum = None if 'exclusiveMaximum' not in schema else schema[
            'exclusiveMaximum']

    def item_schema(self):
        return self.item_schema

    def __str__(self) -> str:
        return 'Array'

    def gen(self):
        if self.enum != None:
            return random.choice(self.enum)
        else:
            result = []
            num = random.randint(self.min_items, self.max_items)
            for _ in range(num):
                result.append(self.item_schema.gen())
            return result


class AnyofSchema(BaseSchema):
    '''Representing a schema with anyof keyword in it
    '''

    def __init__(self, schema) -> None:
        super().__init__(schema)
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

    def gen(self):
        schema = random.choice(self.possibilities)
        return schema.gen()


class BooleanSchema(BaseSchema):

    def __init__(self, schema: dict) -> None:
        super().__init__(schema)
        pass

    def __str__(self) -> str:
        return 'boolean'

    def gen(self):
        return random.choice([True, False])


def schema_node(schema: dict) -> object:
    if 'anyOf' in schema:
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
    with open('data/rabbitmq-operator/operator.yaml', 'r') as operator_yaml:
        parsed_operator_documents = yaml.load_all(operator_yaml,
                                                  Loader=yaml.FullLoader)
        for document in parsed_operator_documents:
            if document['kind'] == 'CustomResourceDefinition':
                spec_schema = ObjectSchema(
                    document['spec']['versions'][0]['schema']['openAPIV3Schema']
                    ['properties']['spec'])
                print(str(spec_schema))
                print(spec_schema.gen())