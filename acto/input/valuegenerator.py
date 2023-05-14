from abc import abstractmethod
import random
from typing import List, Tuple
import exrex
from acto.common import random_string
from acto.input.testplan import InputTreeNode
from acto.schema import StringSchema, NumberSchema, IntegerSchema, ObjectSchema, ArraySchema, AnyOfSchema, OneOfSchema, BooleanSchema, OpaqueSchema
from acto.schema import BaseSchema
from acto.utils.thread_logger import get_thread_logger
from .testcase import EnumTestCase, SchemaPrecondition, TestCase


class ValueGenerator(BaseSchema):
    '''Base class for value generator

    It defines the interface for value generator
    '''

    @abstractmethod
    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        raise NotImplementedError

    @abstractmethod
    def num_cases(self):
        raise NotImplementedError

    @abstractmethod
    def num_fields(self):
        raise NotImplementedError


class StringGenerator(StringSchema, ValueGenerator):
    '''Representation of a generic value generator for string schema
    
    It handles
        - minLength
        - maxLength
        - pattern
    '''
    default_max_length = 10
    DELETION_TEST = 'string-deletion'
    CHANGE_TEST = 'string-change'
    EMPTY_TEST = 'string-empty'

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        # TODO: Use minLength: the exrex does not support minLength
        if self.enum != None:
            if exclude_value != None:
                return random.choice([x for x in self.enum if x != exclude_value])
            else:
                return random.choice(self.enum)
        if self.pattern != None:
            # XXX: since it's random, we don't need to exclude the value
            return exrex.getone(self.pattern, self.max_length)
        if minimum:
            return random_string(self.min_length)
        return 'ACTOKEY'

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        '''String schema currently has two test cases, delete and change'''
        ret = [
            TestCase(StringGenerator.DELETION_TEST, self.delete_precondition, self.delete,
                     self.delete_setup)
        ]
        if self.enum != None:
            for case in self.enum:
                ret.append(EnumTestCase(case))
        else:
            change_testcase = TestCase(StringGenerator.CHANGE_TEST, self.change_precondition,
                                       self.change, self.change_setup)
            ret.append(change_testcase)
            ret.append(
                TestCase(StringGenerator.EMPTY_TEST, self.empty_precondition, self.empty_mutator,
                         self.empty_setup))
        return ret, []

    def num_cases(self):
        return 3

    def num_fields(self):
        return 1

    def to_tree(self):
        '''Override the to_tree method to return InputTreeNode'''
        return InputTreeNode(self.path)

    def change_precondition(self, prev):
        return prev != None

    def change(self, prev):
        '''Test case to change the value to another one'''
        logger = get_thread_logger(with_prefix=True)
        if self.enum != None:
            logger.fatal('String field with enum should not call change to mutate')
        if self.pattern != None:
            new_string = exrex.getone(self.pattern, self.max_length)
        else:
            new_string = 'ACTOKEY'
        if prev == new_string:
            logger.error('Failed to change, generated the same string with previous one')
        return new_string

    def change_setup(self, prev):
        logger = get_thread_logger(with_prefix=True)
        if len(self.examples) > 0:
            logger.info('Using example for setting up field [%s]: [%s]' %
                        (self.path, self.examples[0]))
            return self.examples[0]
        else:
            return self.gen()

    def empty_precondition(self, prev):
        return prev != ""

    def empty_mutator(self, prev):
        return ""

    def empty_setup(self, prev):
        return prev

    def delete(self, prev):
        return self.empty_value()

    def delete_precondition(self, prev):
        return prev != None and prev != self.default and prev != self.empty_value()

    def delete_setup(self, prev):
        logger = get_thread_logger(with_prefix=True)
        if len(self.examples) > 0:
            logger.info('Using example for setting up field [%s]: [%s]' %
                        (self.path, self.examples[0]))
            example_without_default = [x for x in self.enum if x != self.default]
            if len(example_without_default) > 0:
                return random.choice(example_without_default)
            else:
                return self.gen(exclude_value=self.default)
        else:
            return self.gen(exclude_value=self.default)


class NumberGenerator(NumberSchema, ValueGenerator):
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

    DELETION_TEST = 'number-deletion'
    INCREASE_TEST = 'number-increase'
    DECREASE_TEST = 'number-decrease'
    EMPTY_TEST = 'number-empty'
    CHANGE_TEST = 'number-change'

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)

    def gen(self, exclude_value=None, **kwargs) -> float:
        # TODO: Use exclusive_minimum, exclusive_maximum, multiple_of
        if self.enum != None:
            if exclude_value != None:
                return random.choice([x for x in self.enum if x != exclude_value])
            else:
                return random.choice(self.enum)
        return random.uniform(self.minimum, self.maximum)

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        ret = [
            TestCase(NumberGenerator.DELETION_TEST, self.delete_precondition, self.delete,
                     self.delete_setup)
        ]
        if self.enum != None:
            for case in self.enum:
                ret.append(EnumTestCase(case))
        else:
            ret.append(
                TestCase(NumberGenerator.CHANGE_TEST, self.change_precondition, self.change,
                         self.change_setup))
        return ret, []

    def num_cases() -> int:
        return 3

    def num_fields(self) -> int:
        return 1

    def to_tree(self):
        '''Override the to_tree method to return InputTreeNode'''
        return InputTreeNode(self.path)

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

    def empty_precondition(self, prev):
        return prev != 0

    def empty_mutator(self, prev):
        return 0

    def empty_setup(self, prev):
        return 1

    def change_precondition(self, prev):
        return prev != None

    def change(self, prev):
        '''Test case to change the value to another one'''
        logger = get_thread_logger(with_prefix=True)
        if self.enum != None:
            logger.fatal('Number field with enum should not call change to mutate')
        if self.multiple_of != None:
            new_number = random.randrange(self.minimum, self.maximum + 1, self.multiple_of)
        else:
            new_number = random.uniform(self.minimum, self.maximum)
        if prev == new_number:
            logger.error('Failed to change, generated the same number with previous one')
        return new_number

    def change_setup(self, prev):
        return 2

    def delete(self, prev):
        return self.empty_value()

    def delete_precondition(self, prev):
        return prev != None and prev != self.default and prev != self.empty_value()

    def delete_setup(self, prev):
        logger = get_thread_logger(with_prefix=True)
        if len(self.examples) > 0:
            logger.info('Using example for setting up field [%s]: [%s]' %
                        (self.path, self.examples[0]))
            example_without_default = [x for x in self.enum if x != self.default]
            if len(example_without_default) > 0:
                return random.choice(example_without_default)
            else:
                return self.gen(exclude_value=self.default)
        else:
            return self.gen(exclude_value=self.default)


class IntegerGenerator(IntegerSchema, ValueGenerator):
    '''Representation of a integer node
    
    It handles
        - minimum
        - maximum
        - exclusiveMinimum
        - exclusiveMaximum
        - multipleOf
    '''
    default_minimum = 0
    default_maximum = 5

    DELETION_TEST = 'integer-deletion'
    INCREASE_TEST = 'integer-increase'
    DECREASE_TEST = 'integer-decrease'
    EMPTY_TEST = 'integer-empty'
    CHANGE_TEST = 'integer-change'

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)

    def gen(self, exclude_value=None, **kwargs) -> int:
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
                return random.choice(
                    [x for x in range(self.minimum, self.maximum + 1) if x != exclude_value])
            else:
                return random.randrange(self.minimum, self.maximum + 1)

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        normal, special = super().test_cases()
        return normal, special

    def num_cases(self) -> int:
        return 3

    def num_fields(self) -> int:
        return 1

    def to_tree(self):
        '''Override the to_tree method to return InputTreeNode'''
        return InputTreeNode(self.path)

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
            return min(self.maximum, prev * 2)

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
            return max(self.minimum, int(prev / 2))

    def decrease_setup(self, prev):
        return self.maximum

    def change_precondition(self, prev):
        return prev != None

    def change(self, prev):
        return prev + 2

    def change_setup(self, prev):
        return 2

    def delete(self, prev):
        return self.empty_value()

    def delete_precondition(self, prev):
        return prev != None and prev != self.default and prev != self.empty_value()

    def delete_setup(self, prev):
        logger = get_thread_logger(with_prefix=True)
        if len(self.examples) > 0:
            logger.info('Using example for setting up field [%s]: [%s]' %
                        (self.path, self.examples[0]))
            example_without_default = [x for x in self.enum if x != self.default]
            if len(example_without_default) > 0:
                return random.choice(example_without_default)
            else:
                return self.gen(exclude_value=self.default)
        else:
            return self.gen(exclude_value=self.default)


class ObjectGenerator(ObjectSchema, ValueGenerator):
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

    DELETION_TEST = 'object-deletion'
    EMPTY_TEST = 'object-empty'

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)
        if self.properties:
            for property_key, property_schema in self.properties.items():
                self.properties[property_key] = get_value_generator_from_schema(property_schema)
        if self.additional_properties:
            self.additional_properties = get_value_generator_from_schema(self.additional_properties)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs) -> dict:
        # TODO: Use constraints: minProperties, maxProperties
        logger = get_thread_logger(with_prefix=True)

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
                logger.warning('[%s]: No properties and no additional properties' % self.path)
                return None
            key = 'ACTOKEY'
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

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        ret = [
            TestCase(ObjectGenerator.DELETION_TEST, self.delete_precondition, self.delete,
                     self.delete_setup)
        ]
        if self.enum != None:
            for case in self.enum:
                ret.append(EnumTestCase(case))
        else:
            ret.append(
                TestCase(ObjectGenerator.EMPTY_TEST, self.empty_precondition, self.empty_mutator,
                         self.empty_setup))
        return ret, []

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

    def to_tree(self):
        '''Override the to_tree method to return InputTreeNode'''
        return InputTreeNode(self.path)

    def empty_precondition(self, prev):
        return prev != {}

    def empty_mutator(self, prev):
        return {}

    def empty_setup(self, prev):
        return prev

    def delete(self, prev):
        return self.empty_value()

    def delete_precondition(self, prev):
        return prev != None and prev != self.default and prev != self.empty_value()

    def delete_setup(self, prev):
        logger = get_thread_logger(with_prefix=True)
        if len(self.examples) > 0:
            logger.info('Using example for setting up field [%s]: [%s]' %
                        (self.path, self.examples[0]))
            example_without_default = [x for x in self.enum if x != self.default]
            if len(example_without_default) > 0:
                return random.choice(example_without_default)
            else:
                return self.gen(exclude_value=self.default)
        else:
            return self.gen(exclude_value=self.default)


class ArrayGenerator(ArraySchema, ValueGenerator):
    '''Representation of an array node
    
    It handles
        - minItems
        - maxItems
        - items
        - uniqueItems
    '''
    default_min_items = 0
    default_max_items = 5

    DELETION_TEST = 'array-deletion'
    PUSH_TEST = 'array-push'
    POP_TEST = 'array-pop'
    EMPTY_TEST = 'array-empty'

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)
        self.item_schema = get_value_generator_from_schema(self.item_schema)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs) -> list:
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

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        ret = [
            TestCase(ArrayGenerator.DELETION_TEST, self.delete_precondition, self.delete,
                     self.delete_setup)
        ]
        if self.enum != None:
            for case in self.enum:
                ret.append(EnumTestCase(case))
        else:
            ret.append(
                TestCase(ArrayGenerator.PUSH_TEST, self.push_precondition, self.push_mutator,
                         self.push_setup))
            ret.append(
                TestCase(ArrayGenerator.POP_TEST, self.pop_precondition, self.pop_mutator,
                         self.pop_setup))
            ret.append(
                TestCase(ArrayGenerator.EMPTY_TEST, self.empty_precondition, self.empty_mutator,
                         self.empty_setup))
        return ret, []

    def num_cases(self):
        return self.item_schema.num_cases() + 3

    def num_fields(self):
        return self.item_schema.num_fields() + 1

    def to_tree(self):
        '''Override the to_tree method to return InputTreeNode'''
        return InputTreeNode(self.path)

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
        logger = get_thread_logger(with_prefix=True)
        if len(self.examples) > 0:
            for example in self.examples:
                if len(example) > 1:
                    logger.info('Using example for setting up field [%s]: [%s]' %
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
        logger = get_thread_logger(with_prefix=True)

        if len(self.examples) > 0:
            for example in self.examples:
                if len(example) > 1:
                    logger.info('Using example for setting up field [%s]: [%s]' %
                                (self.path, self.examples[0]))
                    return example
        if prev == None:
            return self.gen()
        return self.gen(size=self.max_items)

    def empty_precondition(self, prev):
        return prev != []

    def empty_mutator(self, prev):
        return []

    def empty_setup(self, prev):
        return prev

    def delete(self, prev):
        return self.empty_value()

    def delete_precondition(self, prev):
        return prev != None and prev != self.default and prev != self.empty_value()

    def delete_setup(self, prev):
        logger = get_thread_logger(with_prefix=True)
        if len(self.examples) > 0:
            logger.info('Using example for setting up field [%s]: [%s]' %
                        (self.path, self.examples[0]))
            example_without_default = [x for x in self.enum if x != self.default]
            if len(example_without_default) > 0:
                return random.choice(example_without_default)
            else:
                return self.gen(exclude_value=self.default)
        else:
            return self.gen(exclude_value=self.default)


class AnyOfGenerator(AnyOfSchema, ValueGenerator):
    '''Representing a schema with AnyOf keyword in it
    '''

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        schema = random.choice(self.possibilities)
        return schema.gen(exclude_value=exclude_value, minimum=minimum)

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        ret = []
        if self.enum != None:
            for case in self.enum:
                ret.append(EnumTestCase(case))
        else:
            for possibility in self.possibilities:
                testcases, _ = possibility.test_cases()
                for testcase in testcases:
                    testcase.add_precondition(SchemaPrecondition(possibility).precondition)
                ret.extend(testcases)
        return ret, []

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

    def to_tree(self):
        '''Override the to_tree method to return InputTreeNode'''
        return InputTreeNode(self.path)


class OneOfGenerator(OneOfSchema, ValueGenerator):
    '''Representing a schema with OneOf keyword in it
    '''

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        schema = random.choice(self.possibilities)
        return schema.gen(exclude_value=exclude_value, minimum=minimum)

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        ret = []
        if self.enum != None:
            for case in self.enum:
                ret.append(EnumTestCase(case))
        else:
            for possibility in self.possibilities:
                testcases, _ = possibility.test_cases()
                for testcase in testcases:
                    testcase.add_precondition(SchemaPrecondition(possibility).precondition)
                ret.extend(testcases)
        return ret, []

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

    def to_tree(self):
        '''Override the to_tree method to return InputTreeNode'''
        return InputTreeNode(self.path)


class BooleanGenerator(BooleanSchema, ValueGenerator):

    DELETION_TEST = 'boolean-deletion'
    TOGGLE_OFF_TEST = 'boolean-toggle-off'
    TOGGLE_ON_TEST = 'boolean-toggle-on'

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)

    def gen(self, exclude_value=None, **kwargs):
        if exclude_value != None:
            return not exclude_value
        else:
            return random.choice([True, False])

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        ret = [
            TestCase(BooleanGenerator.DELETION_TEST, self.delete_precondition, self.delete,
                     self.delete_setup)
        ]
        if self.enum != None:
            for case in self.enum:
                ret.append(EnumTestCase(case))
        else:
            ret.append(
                TestCase(BooleanGenerator.TOGGLE_OFF_TEST, self.toggle_off_precondition,
                         self.toggle_off, self.toggle_off_setup))
            ret.append(
                TestCase(BooleanGenerator.TOGGLE_ON_TEST, self.toggle_on_precondition,
                         self.toggle_on, self.toggle_on_setup))
        return ret, []

    def num_cases(self):
        return 3

    def num_fields(self):
        return 1

    def to_tree(self):
        '''Override the to_tree method to return InputTreeNode'''
        return InputTreeNode(self.path)

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

    def delete(self, prev):
        return self.empty_value()

    def delete_precondition(self, prev):
        return prev != None and prev != self.default and prev != self.empty_value()

    def delete_setup(self, prev):
        logger = get_thread_logger(with_prefix=True)
        if len(self.examples) > 0:
            logger.info('Using example for setting up field [%s]: [%s]' %
                        (self.path, self.examples[0]))
            example_without_default = [x for x in self.enum if x != self.default]
            if len(example_without_default) > 0:
                return random.choice(example_without_default)
            else:
                return self.gen(exclude_value=self.default)
        else:
            return self.gen(exclude_value=self.default)


class OpaqueGenerator(OpaqueSchema, ValueGenerator):
    '''Opaque schema to handle the fields that do not have a schema'''

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)

    def gen(self, **kwargs):
        return None

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        return [], []

    def num_cases(self):
        return 1

    def num_fields(self):
        return 1
    
    def to_tree(self):
        '''Override the to_tree method to return InputTreeNode'''
        return InputTreeNode(self.path)


def get_value_generator_from_schema(schema: BaseSchema):
    '''Factory method to get the basic value generator from the schema'''

    if isinstance(schema, StringSchema):
        return StringGenerator(schema.path, schema.raw_schema)
    elif isinstance(schema, NumberSchema):
        return NumberGenerator(schema.path, schema.raw_schema)
    elif isinstance(schema, IntegerSchema):
        return IntegerGenerator(schema.path, schema.raw_schema)
    elif isinstance(schema, ArraySchema):
        return ArrayGenerator(schema.path, schema.raw_schema)
    elif isinstance(schema, ObjectSchema):
        return ObjectGenerator(schema.path, schema.raw_schema)
    elif isinstance(schema, BooleanSchema):
        return BooleanGenerator(schema.path, schema.raw_schema)
    elif isinstance(schema, OneOfSchema):
        return OneOfGenerator(schema.path, schema.raw_schema)
    elif isinstance(schema, AnyOfSchema):
        return AnyOfGenerator(schema.path, schema.raw_schema)
    elif isinstance(schema, OpaqueSchema):
        return OpaqueGenerator(schema.path, schema.raw_schema)
    else:
        raise NotImplementedError('Schema type [%s] is not supported' % type(schema))


def extract_schema_with_value_generator(path: list, schema: dict) -> ValueGenerator:
    '''Extract the schema and the value generator from the schema
    
    It is very similar to the `extract_schema` function, but it returns the value generator
    instead of the schema.
    '''
    logger = get_thread_logger(with_prefix=True)

    if 'anyOf' in schema:
        return AnyOfGenerator(path, schema)
    elif 'oneOf' in schema:
        return OneOfGenerator(path, schema)

    if 'type' not in schema:
        if 'properties' in schema:
            return ObjectGenerator(path, schema)
        else:
            logger.warn('No type found in schema: %s' % str(schema))
            return OpaqueGenerator(path, schema)
    t = schema['type']
    if isinstance(t, list):
        if 'null' in t:
            t.remove('null')
        if len(t) == 1:
            t = t[0]

    if t == 'string':
        return StringGenerator(path, schema)
    elif t == 'number':
        return NumberGenerator(path, schema)
    elif t == 'integer':
        return IntegerGenerator(path, schema)
    elif t == 'boolean':
        return BooleanGenerator(path, schema)
    elif t == 'array':
        return ArrayGenerator(path, schema)
    elif t == 'object':
        return ObjectGenerator(path, schema)
    else:
        logger.error('Unsupported type %s' % t)
        return None