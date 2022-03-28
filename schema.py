import logging
import yaml
from copy import deepcopy
import random
from abc import abstractmethod
import exrex
import string


class BaseSchema:
    '''Base class for schemas
    
    Handles some keywords used for any types
    '''

    def __init__(self, path: list, schema: dict) -> None:
        self.path = path
        self.default = None if 'default' not in schema else schema['default']
        self.enum = None if 'enum' not in schema else schema['enum']

    def get_path(self) -> list:
        return self.path

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

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)
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
        letters = string.ascii_lowercase
        return ( ''.join(random.choice(letters) for i in range(10)) )
    
    def num_cases(self):
        return 3

    def num_fields(self):
        return 1


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

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)
        self.minimum = self.default_minimum if 'minimum' not in schema else schema[
            'minimum']
        self.maximum = self.default_maximum if 'maximum' not in schema else schema[
            'maximum']
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

    def num_cases():
        return 3

    def num_fields(self):
        return 1


class IntegerSchema(NumberSchema):
    '''Special case of NumberSchema'''

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)

    def __str__(self) -> str:
        return 'Integer'

    def gen(self):
        # TODO: Use exclusive_minimum, exclusive_maximum
        if self.enum != None:
            return random.choice(self.enum)
        elif self.multiple_of != None:
            return random.randrange(self.minimum, self.maximum + 1,
                                    self.multiple_of)
        else:
            return random.randint(self.minimum, self.maximum)
    
    def num_cases(self):
        return 3

    def num_fields(self):
        return 1

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

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)
        self.properties = {}
        self.additional_properties = None
        self.required = []
        if 'properties' in schema:
            for property_key, property_schema in schema['properties'].items():
                self.properties[property_key] = extract_schema(
                    self.path + [property_key], property_schema)
        if 'additionalProperties' in schema:
            self.additional_properties = extract_schema(
                self.path + ['additional_properties'],
                schema['additionalProperties'])
        if 'required' in schema:
            self.required = schema['required']
        if 'minProperties' in schema:
            self.min_properties = schema['minProperties']
        if 'maxProperties' in schema:
            self.max_properties = schema['maxProperties']

    def get_property_schema(self, key):
        if key in self.properties:
            return self.properties[key]
        elif self.additional_properties != None:
            return self.additional_properties
        else:
            logging.warning('Field [%s] does not have a schema, using opaque schema', key)
            return OpaqueSchema(self.path + [key], {})

    def get_properties(self) -> dict:
        return self.properties

    def get_additional_properties(self):
        return self.additional_properties

    def __str__(self) -> str:
        ret = '{'
        for k, v in self.properties.items():
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
        if len(self.properties) == 0:
            if self.additional_properties == None:
                # raise TypeError('[%s]: No properties and no additional properties' % self.path)
                logging.warning('[%s]: No properties and no additional properties' % self.path)
                return None
            letters = string.ascii_lowercase
            key = ''.join(random.choice(letters) for i in range(5))
            result[key] = self.additional_properties.gen()
        else:
            for k, v in self.properties.items():
                if random.uniform(0, 1) < 0.1 and k not in self.required:
                    # 10% of the chance this child will be null
                    result[k] = None
                else:
                    result[k] = v.gen()
        return result

    def num_cases(self):
        num = 0
        for i in self.properties.values():
            num += i.num_cases()
        return num+1

    def num_fields(self):
        num = 0
        for i in self.properties.values():
            num += i.num_fields()
        return num+1


class ArraySchema(BaseSchema):
    '''Representation of an array node
    
    It handles
        - minItems
        - maxItems
        - items
        - uniqueItems
    '''
    default_min_items = 0
    default_max_items = 5

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)
        self.item_schema = extract_schema(self.path + ['item'], schema['items'])
        self.min_items = self.default_min_items if 'minItems' not in schema else schema[
            'minItems']
        self.max_items = self.default_max_items if 'maxItems' not in schema else schema[
            'maxItems']
        self.unique_items = None if 'uniqueItems' not in schema else schema[
            'exclusiveMinimum']

    def get_item_schema(self):
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

    def num_cases(self):
        return self.item_schema.num_cases()+3

    def num_fields(self):
        return self.item_schema.num_fields()+1


class AnyOfSchema(BaseSchema):
    '''Representing a schema with AnyOf keyword in it
    '''

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)
        self.possibilities = []
        for index, v in enumerate(schema['anyOf']):
            base_schema = deepcopy(schema)
            del base_schema['anyOf']
            base_schema.update(v)
            self.possibilities.append(
                extract_schema(self.path + ['%s' % str(index)], base_schema))

    def __str__(self) -> str:
        ret = '['
        for i in self.possibilities:
            ret += str(i)
            ret += ', '
        ret += ']'
        return ret

    def get_possibilities(self):
        return self.possibilities

    def gen(self):
        schema = random.choice(self.possibilities)
        return schema.gen()

    def num_cases(self):
        num = 0
        for i in self.possibilities:
            num += i.num_cases()
        return num+1

    def num_fields(self):
        num = 0
        for i in self.possibilities:
            num += i.num_fields()
        return num


class BooleanSchema(BaseSchema):

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)
        pass

    def __str__(self) -> str:
        return 'boolean'

    def gen(self):
        return random.choice([True, False])

    def num_cases(self):
        return 3
    
    def num_fields(self):
        return 1


class OpaqueSchema(BaseSchema):
    '''Opaque schema to handle the fields that do not have a schema'''

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)
        pass

    def __str__(self) -> str:
        return 'any'

    def gen(self):
        return None

    def num_cases(self):
        return 1
    
    def num_fields(self):
        return 1


def extract_schema(path: list, schema: dict) -> object:
    if 'anyOf' in schema:
        return AnyOfSchema(path, schema)
    t = schema['type']
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
        logging.error('Unsupported type %s' % t)
        return None


if __name__ == '__main__':
    with open('data/rabbitmq-operator/operator.yaml', 'r') as operator_yaml:
        parsed_operator_documents = yaml.load_all(operator_yaml,
                                                  Loader=yaml.FullLoader)
        for document in parsed_operator_documents:
            if document['kind'] == 'CustomResourceDefinition':
                spec_schema = ObjectSchema(
                    ['root'], document['spec']['versions'][0]['schema']
                    ['openAPIV3Schema']['properties']['spec'])
                print(str(spec_schema))
                print(spec_schema.gen())
                print(spec_schema.num_fields())
                for k,v in spec_schema.properties.items():
                    print('%s has %d fields' % (k, v.num_fields()))
                print(spec_schema.num_cases())

    ss = StringSchema(None, {"type": "string"})
    print(ss.gen())