import logging
import yaml
from copy import deepcopy
import random
from abc import abstractmethod
import exrex
import json
from jsonschema import validate

from test_case import *
from common import ActoEncoder, random_string
from testplan import TreeNode


class BaseSchema:
    '''Base class for schemas
    
    Handles some keywords used for any types
    '''

    def __init__(self, path: list, schema: dict) -> None:
        self.path = path
        self.raw_schema = schema
        self.default = None if 'default' not in schema else schema['default']
        self.enum = None if 'enum' not in schema else schema['enum']
        self.examples = []

    def get_path(self) -> list:
        return self.path

    @abstractmethod
    def gen(self, exclude_value=None, **kwargs):
        return None

    @abstractmethod
    def test_cases(self) -> list:
        return None

    @abstractmethod
    def get_all_schemas(self):
        return None

    @abstractmethod
    def to_tree(self) -> TreeNode:
        '''Returns tree structure, used for input generation'''
        return TreeNode(self.path)

    @abstractmethod
    def load_examples(self, example):
        '''Load example into schema and subschemas'''

    def delete(self, prev):
        return None

    def delete_precondition(self, prev):
        return prev != None and prev != self.default

    def delete_setup(self, prev):
        if len(self.examples) > 0:
            logging.info('Using example for setting up field [%s]: [%s]' %
                         (self.path, self.examples[0]))
            example_without_default = [x for x in self.enum if x != self.default]
            if len(example_without_default) > 0:
                return random.choice(example_without_default)
            else:
                return self.gen(exclude_value=self.default)
        else:
            return self.gen(exclude_value=self.default)

    def validate(self, instance) -> bool:
        try:
            validate(instance, self.raw_schema)
            return True
        except:
            return False


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
        self.min_length = None if 'minLength' not in schema else schema['minLength']
        self.max_length = self.default_max_length if 'maxLength' not in schema else schema[
            'maxLength']
        self.pattern = None if 'pattern' not in schema else schema['pattern']

    def gen(self, exclude_value=None, **kwargs):
        # TODO: Use minLength: the exrex does not support minLength
        if self.enum != None:
            if exclude_value != None:
                return random.choice([x for x in self.enum if x != exclude_value])
            else:
                return random.choice(self.enum)
        if self.pattern != None:
            # XXX: since it's random, we don't need to exclude the value
            return exrex.getone(self.pattern, self.max_length)
        return random_string(10)

    def test_cases(self):
        '''String schema currently has two test cases, delete and change'''
        ret = [TestCase(self.delete_precondition, self.delete, self.delete_setup)]
        if self.enum != None:
            for case in self.enum:
                ret.append(EnumTestCase(case))
        else:
            change_testcase = TestCase(self.change_precondition, self.change, self.change_setup)
            ret.append(change_testcase)
        return ret

    def get_all_schemas(self) -> list:
        return [self]

    def to_tree(self) -> TreeNode:
        return TreeNode(self.path)

    def load_examples(self, example: str):
        self.examples.append(example)

    def num_cases(self):
        return 3

    def num_fields(self):
        return 1

    def __str__(self) -> str:
        return 'String'

    def change_precondition(self, prev):
        return prev != None

    def change(self, prev):
        '''Test case to change the value to another one'''
        if self.enum != None:
            logging.fatal('String field with enum should not call change to mutate')
        if self.pattern != None:
            new_string = exrex.getone(self.pattern, self.max_length)
        else:
            new_string = random_string(10)
        if prev == new_string:
            logging.error('Failed to change, generated the same string with previous one')
        return new_string

    def change_setup(self, prev):
        if len(self.examples) > 0:
            logging.info('Using example for setting up field [%s]: [%s]' %
                         (self.path, self.examples[0]))
            return self.examples[0]
        else:
            return self.gen()


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
        self.minimum = self.default_minimum if 'minimum' not in schema else schema['minimum']
        self.maximum = self.default_maximum if 'maximum' not in schema else schema['maximum']
        self.exclusive_minimum = None if 'exclusiveMinimum' not in schema else schema[
            'exclusiveMinimum']
        self.exclusive_maximum = None if 'exclusiveMaximum' not in schema else schema[
            'exclusiveMaximum']
        self.multiple_of = None if 'multipleOf' not in schema else schema['multipleOf']

    def gen(self, exclude_value=None, **kwargs) -> float:
        # TODO: Use exclusive_minimum, exclusive_maximum, multiple_of
        if self.enum != None:
            if exclude_value != None:
                return random.choice([x for x in self.enum if x != exclude_value])
            else:
                return random.choice(self.enum)
        return random.uniform(self.minimum, self.maximum)

    def test_cases(self) -> list:
        ret = [TestCase(self.delete_precondition, self.delete, self.delete_setup)]
        if self.enum != None:
            for case in self.enum:
                ret.append(EnumTestCase(case))
        else:
            ret.append(TestCase(self.increase_precondition, self.increase, self.increase_setup))
            ret.append(TestCase(self.decrease_precondition, self.decrease, self.decrease_setup))
        return ret

    def get_all_schemas(self) -> list:
        return [self]

    def to_tree(self) -> TreeNode:
        return TreeNode(self.path)

    def load_examples(self, example: float):
        self.examples.append(example)

    def num_cases() -> int:
        return 3

    def num_fields(self) -> int:
        return 1

    def __str__(self) -> str:
        return 'Number'

    def increase_precondition(self, prev):
        if prev == None:
            return False
        if self.multiple_of == None:
            return prev < self.maximum
        else:
            return prev < self.maximum - self.multiple_of

    def increase(self, prev):
        if self.multiple_of != None:
            return prev + self.multiple_of
        else:
            return random.uniform(prev, self.maximum)

    def increase_setup(self, prev):
        return self.minimum

    def decrease_precondition(self, prev):
        if prev == None:
            return False
        if self.multiple_of == None:
            return prev > self.minimum
        else:
            return prev > self.minimum + self.multiple_of

    def decrease(self, prev):
        if self.multiple_of != None:
            return prev - self.multiple_of
        else:
            return random.uniform(self.minimum, prev)

    def decrease_setup(self, prev):
        return self.maximum


class IntegerSchema(NumberSchema):
    '''Special case of NumberSchema'''

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)
        if self.default == None:
            self.default = 0

    def gen(self, exclude_value = None, **kwargs) -> int:
        # TODO: Use exclusive_minimum, exclusive_maximum
        if self.enum != None:
            if exclude_value != None:
                return random.choice([x for x in self.enum if x != exclude_value])
            else:
                return random.choice(self.enum)
        elif self.multiple_of != None:
            return random.randrange(self.minimum, self.maximum + 1, self.multiple_of)
        else:
            if exclude_value != None:
                return random.choice([x for x in range(self.minimum, self.maximum + 1) if x != exclude_value])
            else:
                return random.randrange(self.minimum, self.maximum + 1)

    def test_cases(self) -> list:
        return super().test_cases()

    def get_all_schemas(self) -> list:
        return [self]

    def to_tree(self) -> TreeNode:
        return TreeNode(self.path)

    def load_examples(self, example: int):
        self.examples.append(example)

    def num_cases(self) -> int:
        return 3

    def num_fields(self) -> int:
        return 1

    def __str__(self) -> str:
        return 'Integer'

    def increase_precondition(self, prev):
        if prev == None:
            return False
        if self.multiple_of == None:
            return prev < self.maximum
        else:
            return prev < self.maximum - self.multiple_of

    def increase(self, prev):
        if self.multiple_of != None:
            return random.randrange(prev, self.maximum + 1, self.multiple_of)
        else:
            return random.randint(prev + 1, self.maximum)

    def increase_setup(self, prev):
        return self.minimum

    def decrease_precondition(self, prev):
        if prev == None:
            return False
        if self.multiple_of == None:
            return prev > self.minimum
        else:
            return prev > self.minimum + self.multiple_of

    def decrease(self, prev):
        if self.multiple_of != None:
            return random.randrange(self.minimum, prev, self.multiple_of)
        else:
            return random.randint(self.minimum, prev - 1)

    def decrease_setup(self, prev):
        return self.maximum


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
        if 'properties' not in schema and 'additionalProperties' not in schema:
            logging.warning('Object schema %s does not have properties nor additionalProperties' %
                            self.path)
        if 'properties' in schema:
            for property_key, property_schema in schema['properties'].items():
                self.properties[property_key] = extract_schema(self.path + [property_key],
                                                               property_schema)
        if 'additionalProperties' in schema:
            self.additional_properties = extract_schema(self.path + ['additional_properties'],
                                                        schema['additionalProperties'])
        if 'required' in schema:
            self.required = schema['required']
        if 'minProperties' in schema:
            self.min_properties = schema['minProperties']
        if 'maxProperties' in schema:
            self.max_properties = schema['maxProperties']

    def gen(self, exclude_value = None, minimum: bool = False, **kwargs) -> dict:
        # TODO: Use constraints: minProperties, maxProperties
        if self.enum != None:
            if exclude_value != None:
                return random.choice([x for x in self.enum if x != exclude_value])
            else:
                return random.choice(self.enum)

        # XXX: need to handle exclude_value, but not important for now for object types
        result = {}
        if len(self.properties) == 0:
            if self.additional_properties == None:
                # raise TypeError('[%s]: No properties and no additional properties' % self.path)
                logging.warning('[%s]: No properties and no additional properties' % self.path)
                return None
            key = random_string(5)
            result[key] = self.additional_properties.gen(minimum=minimum)
        else:
            for k, v in self.properties.items():
                if minimum:
                    if k in self.required:
                        result[k] = v.gen(minimum=True)
                    else:
                        continue
                else:
                    if random.uniform(0, 1) < 0.1 and k not in self.required:
                        # 10% of the chance this child will be null
                        result[k] = None
                    else:
                        result[k] = v.gen(minimum=minimum)
        if 'enabled' in self.properties:
            result['enabled'] = True
        return result

    def test_cases(self):
        ret = [TestCase(self.delete_precondition, self.delete, self.delete_setup)]
        if self.enum != None:
            for case in self.enum:
                ret.append(EnumTestCase(case))
        return ret

    def get_all_schemas(self) -> list:
        '''Return all the subschemas as a list'''
        ret = [self]
        if self.properties != None:
            for value in self.properties.values():
                ret.extend(value.get_all_schemas())
        if self.additional_properties != None:
            ret.append(self.additional_properties)
        # if len(ret) > 500:
        #     # XXX: Temporary prune
        #     return []
        return ret

    def to_tree(self) -> TreeNode:
        node = TreeNode(self.path)
        if self.properties != None:
            for key, value in self.properties.items():
                node.add_child(key, value.to_tree())

        if self.additional_properties != None:
            node.add_child('additional_properties', self.additional_properties.to_tree())

        return node

    def load_examples(self, example: dict):
        self.examples.append(example)
        for key, value in example.items():
            if key in self.properties:
                self.properties[key].load_examples(value)

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

    def num_cases(self) -> int:
        num = 0
        for i in self.properties.values():
            num += i.num_cases()
        return num + 1

    def num_fields(self):
        num = 0
        for i in self.properties.values():
            num += i.num_fields()
        return num + 1

    def __str__(self) -> str:
        ret = '{'
        for k, v in self.properties.items():
            ret += str(k)
            ret += ': '
            ret += str(v)
            ret += ', '
        ret += '}'
        return ret

    def __getitem__(self, key):
        return self.properties[key]

    def __setitem__(self, key, value):
        self.properties[key] = value


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
        self.item_schema = extract_schema(self.path + ['ITEM'], schema['items'])
        self.min_items = self.default_min_items if 'minItems' not in schema else schema['minItems']
        self.max_items = self.default_max_items if 'maxItems' not in schema else schema['maxItems']
        self.unique_items = None if 'uniqueItems' not in schema else schema['exclusiveMinimum']

    def get_item_schema(self):
        return self.item_schema

    def gen(self, exclude_value = None, minimum: bool = False, **kwargs) -> list:
        if self.enum != None:
            if exclude_value != None:
                return random.choice([x for x in self.enum if x != exclude_value])
            else:
                return random.choice(self.enum)
        else:
            # XXX: need to handle exclude_value, but not important for now for array types
            result = []
            if 'size' in kwargs and kwargs['size'] != None:
                num = kwargs['size']
            else:
                num = random.randint(self.min_items, self.max_items)
            for _ in range(num):
                result.append(self.item_schema.gen(minimum=minimum))
            return result

    def test_cases(self) -> list:
        ret = [TestCase(self.delete_precondition, self.delete, self.delete_setup)]
        if self.enum != None:
            for case in self.enum:
                ret.append(EnumTestCase(case))
        else:
            ret.append(TestCase(self.push_precondition, self.push_mutator, self.push_setup))
            ret.append(TestCase(self.pop_precondition, self.pop_mutator, self.pop_setup))
        return ret

    def get_all_schemas(self) -> list:
        ret = [self]
        ret.extend(self.item_schema.get_all_schemas())
        return ret

    def to_tree(self) -> TreeNode:
        node = TreeNode(self.path)
        node.add_child('ITEM', self.item_schema.to_tree())
        return node

    def load_examples(self, example: list):
        self.examples.append(example)
        for item in example:
            self.item_schema.load_examples(item)

    def num_cases(self):
        return self.item_schema.num_cases() + 3

    def num_fields(self):
        return self.item_schema.num_fields() + 1

    def push_precondition(self, prev):
        if prev == None:
            return False
        if len(prev) >= self.max_items:
            return False
        return True

    def push_mutator(self, prev):
        new_item = self.item_schema.gen()
        return prev + [new_item]

    def push_setup(self, prev):
        if len(self.examples) > 0:
            for example in self.examples:
                if len(example) > 1:
                    logging.info('Using example for setting up field [%s]: [%s]' %
                                 (self.path, self.examples[0]))
                    return example
        if prev == None:
            return self.gen()
        return self.gen(size=self.min_items)

    def pop_precondition(self, prev):
        if prev == None:
            return False
        if len(prev) <= self.min_items:
            return False
        if len(prev) == 0:
            return False
        return True

    def pop_mutator(self, prev):
        prev.pop()
        return prev

    def pop_setup(self, prev):
        if len(self.examples) > 0:
            for example in self.examples:
                if len(example) > 1:
                    logging.info('Using example for setting up field [%s]: [%s]' %
                                 (self.path, self.examples[0]))
                    return example
        if prev == None:
            return self.gen()
        return self.gen(size=self.max_items)

    def __str__(self) -> str:
        return 'Array'

    def __getitem__(self, key):
        return self.item_schema

    def __setitem__(self, key, value):
        self.item_schema = value


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
            self.possibilities.append(extract_schema(self.path + ['%s' % str(index)], base_schema))

    def get_possibilities(self):
        return self.possibilities

    def gen(self, exclude_value = None, minimum: bool = False, **kwargs):
        schema = random.choice(self.possibilities)
        return schema.gen(exclude_value=exclude_value, minimum=minimum)

    def test_cases(self) -> list:
        ret = []
        if self.enum != None:
            for case in self.enum:
                ret.append(EnumTestCase(case))
        else:
            for possibility in self.possibilities:
                testcases = possibility.test_cases()
                for testcase in testcases:
                    testcase.add_precondition(SchemaPrecondition(possibility).precondition)
                ret.extend(testcases)
        return ret

    def get_all_schemas(self) -> list:
        return [self]

    def to_tree(self) -> TreeNode:
        return TreeNode(self.path)

    def load_examples(self, example: list):
        for possibility in self.possibilities:
            if possibility.validate(example):
                possibility.load_examples(example)

    def num_cases(self) -> int:
        num = 0
        for i in self.possibilities:
            num += i.num_cases()
        return num + 1

    def num_fields(self) -> int:
        num = 0
        for i in self.possibilities:
            num += i.num_fields()
        return num

    def __str__(self) -> str:
        ret = '['
        for i in self.possibilities:
            ret += str(i)
            ret += ', '
        ret += ']'
        return ret


class BooleanSchema(BaseSchema):

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)
        if self.default == None:
            self.default = False
        pass

    def gen(self, exclude_value = None, **kwargs):
        if exclude_value != None:
            return not exclude_value
        else:
            return random.choice([True, False])

    def test_cases(self):
        ret = [TestCase(self.delete_precondition, self.delete, self.delete_setup)]
        if self.enum != None:
            for case in self.enum:
                ret.append(EnumTestCase(case))
        else:
            ret.append(
                TestCase(self.toggle_off_precondition, self.toggle_off, self.toggle_off_setup))
            ret.append(TestCase(self.toggle_on_precondition, self.toggle_on, self.toggle_on_setup))
        return ret

    def get_all_schemas(self) -> list:
        return [self]

    def to_tree(self) -> TreeNode:
        return TreeNode(self.path)

    def load_examples(self, example: bool):
        pass

    def num_cases(self):
        return 3

    def num_fields(self):
        return 1

    def __str__(self) -> str:
        return 'boolean'

    def toggle_on_precondition(self, prev):
        if prev == None and self.default == False:
            return True
        elif prev == False:
            return True
        else:
            return False

    def toggle_on(self, prev):
        return True

    def toggle_on_setup(self, prev):
        return False

    def toggle_off_precondition(self, prev):
        if prev == None and self.default == True:
            return True
        elif prev == True:
            return True
        else:
            return False

    def toggle_off(self, prev):
        return False

    def toggle_off_setup(self, prev):
        return True


class OpaqueSchema(BaseSchema):
    '''Opaque schema to handle the fields that do not have a schema'''

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)
        pass

    def gen(self, **kwargs):
        return None

    def test_cases(self):
        return []

    def get_all_schemas(self):
        return []

    def to_tree(self) -> TreeNode:
        return TreeNode(self.path)

    def load_examples(self, example):
        pass

    def num_cases(self):
        return 1

    def num_fields(self):
        return 1

    def __str__(self) -> str:
        return 'any'


def extract_schema(path: list, schema: dict) -> BaseSchema:
    if 'anyOf' in schema:
        return AnyOfSchema(path, schema)
    if 'type' not in schema:
        return OpaqueSchema(path, schema)
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
    with open('data/redis-operator/databases.spotahome.com_redisfailovers.yaml',
              'r') as operator_yaml:
        parsed_operator_documents = yaml.load_all(operator_yaml, Loader=yaml.FullLoader)
        for document in parsed_operator_documents:
            if document['kind'] == 'CustomResourceDefinition':
                spec_schema = ObjectSchema(
                    ['root'], document['spec']['versions'][0]['schema']['openAPIV3Schema']
                    ['properties']['spec']['properties']['redis'])
                print(str(spec_schema))
                print(spec_schema.gen())
                print(spec_schema.num_fields())
                for k, v in spec_schema.properties.items():
                    print('%s has %d fields' % (k, v.num_fields()))
                print(spec_schema.num_cases())

                schema_list = spec_schema.get_all_schemas()
                test_plan = {}
                for schema in schema_list:
                    test_plan[str(schema.path)] = schema.test_cases()
                with open('test_plan.json', 'w') as fout:
                    json.dump(test_plan, fout, cls=ActoEncoder, indent=4)

    ss = StringSchema(None, {"type": "string"})
    print(ss.gen())