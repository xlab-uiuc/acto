from abc import abstractmethod
import yaml
import random
import string

from acto.utils import get_thread_logger
from acto.schema import AnyOfSchema, ObjectSchema, ArraySchema, StringSchema, NumberSchema, IntegerSchema, BooleanSchema, OpaqueSchema


class ValueWithSchema():

    def __init__(self) -> None:
        pass

    @abstractmethod
    def raw_value(self) -> object:
        return None

    @abstractmethod
    def mutate(self):
        return

    @abstractmethod
    def update(self):
        return

    @abstractmethod
    def get_value_by_path(self, path: list):
        return

    @abstractmethod
    def create_path(self, path: list):
        return

    @abstractmethod
    def set_value_by_path(self, value, path):
        return


class ValueWithObjectSchema(ValueWithSchema):

    def __init__(self, value, schema) -> None:
        self.schema = schema
        if value == None:
            self.store = None
        elif isinstance(value, dict):
            self.store = {}
            for k, v in value.items():
                self.store[k] = attach_schema_to_value(v, self.schema.get_property_schema(k))
        else:
            raise TypeError('Value [%s] has type [%s] Path [%s]' %
                            (value, type(value), self.schema.get_path()))

    def value(self):
        return self.store

    def __str__(self) -> str:
        if self.store == None:
            ret = None
        else:
            ret = {}
            for k, v in self.store.items():
                ret[k] = str(v.raw_value())
        return str(ret)

    def raw_value(self) -> dict:
        if self.store == None:
            return None
        else:
            ret = {}
            for k, v in self.store.items():
                ret[k] = v.raw_value()
            return ret

    def mutate(self, p_delete=0.05, p_replace=0.1):
        '''Mutate a small portion of the value
        
        - Replace with null
        - Replace with a new value
        - mutate a child
        TODO: generate a property that didn't exist before
        '''
        logger = get_thread_logger(with_prefix=True)

        if self.store == None:
            value = self.schema.gen()
            self.update(value)
        else:
            dice = random.random()
            if dice < p_delete:
                self.store = None
            elif dice < p_replace:
                value = self.schema.gen()
                self.update(value)
            else:
                properties = self.schema.get_properties()
                if len(properties) == 0:
                    # XXX: Handle additional properties better
                    if self.schema.get_additional_properties() == None:
                        logger.warning('Object schema is opaque %s', self.schema.get_path())
                        return
                    else:
                        letters = string.ascii_lowercase
                        key = ''.join(random.choice(letters) for i in range(5))
                        self.__setitem__(key, self.schema.get_additional_properties().gen())
                else:
                    child_key = random.choice(list(self.schema.get_properties()))
                    if child_key not in self.store:
                        self.__setitem__(child_key,
                                         self.schema.get_property_schema(child_key).gen())
                    self.store[child_key].mutate()

    def update(self, value):
        if value == None:
            self.store = None
        elif isinstance(value, dict):
            self.store = {}
            for k, v in value.items():
                self.store[k] = attach_schema_to_value(v, self.schema.get_property_schema(k))
        else:
            raise TypeError('Value [%s] Path [%s]' % (value, self.schema.get_path()))

    def get_value_by_path(self, path: list):
        '''Fetch the value specified by path'''
        if self.store == None:
            return None
        if len(path) == 0:
            return self.raw_value()
        key = path.pop(0)
        if key not in self.store:
            # path does not exist yet
            return None
        else:
            return self.store[key].get_value_by_path(path)

    def create_path(self, path: list):
        '''Ensures the path exists'''
        if len(path) == 0:
            return
        key = path.pop(0)
        if self.store == None:
            self.update(self.schema.gen(minimum=True))
            self.__setitem__(key, None)
        elif key not in self.store:
            self.__setitem__(key, None)
        self.store[key].create_path(path)

    def set_value_by_path(self, value, path):
        if len(path) == 0:
            self.update(value)
        else:
            key = path.pop(0)
            self.store[key].set_value_by_path(value, path)

    def __getitem__(self, key):
        return self.store[key]

    def __setitem__(self, key, value):
        self.store[key] = attach_schema_to_value(value, self.schema.get_property_schema(key))

    def __contains__(self, item: string):
        # in operator
        return item in self.store


class ValueWithArraySchema(ValueWithSchema):

    def __init__(self, value, schema) -> None:
        self.schema = schema
        if value == None:
            self.store = None
        elif isinstance(value, list):
            self.store = []
            for i in value:
                self.store.append(attach_schema_to_value(i, self.schema.get_item_schema()))
        else:
            raise TypeError('Value [%s] Path [%s]' % (value, self.schema.get_path()))

    def value(self):
        return self.store

    def __str__(self) -> str:
        if self.store == None:
            return 'None'
        else:
            ret = []
            for i in self.store:
                ret.append(str(i.raw_value()))
            return str(ret)

    def raw_value(self) -> list:
        if self.store == None:
            return None
        else:
            ret = []
            for i in self.store:
                ret.append(i.raw_value())
            return ret

    def mutate(self, p_delete=0.05, p_replace=0.1):
        '''Mutate a small portion of the value
        
        - Replace with null
        - Delete an item
        - Append an item
        - mutate an item
        '''
        if self.store == None:
            value = self.schema.gen()
            self.update(value)
        elif len(self.store) == 0:
            self.append(self.schema.get_item_schema().gen())
        else:
            dice = random.random()
            if dice < p_delete:
                self.store = None
            elif dice < 0.4:
                # Delete an item
                index = random.randint(0, len(self.store) - 1)
                del self.store[index]
            elif dice < 0.7:
                # Append an item
                self.append(self.schema.get_item_schema().gen())
            else:
                # mutate an item
                index = random.randint(0, len(self.store) - 1)
                self.store[index].mutate()

    def update(self, value):
        if value == None:
            self.store = None
        elif isinstance(value, list):
            self.store = []
            for i in value:
                self.store.append(attach_schema_to_value(i, self.schema.get_item_schema()))
        else:
            raise TypeError('Value [%s] Path [%s]' % (value, self.schema.get_path()))

    def append(self, value):
        self.store.append(attach_schema_to_value(value, self.schema.get_item_schema()))

    def get_value_by_path(self, path: list):
        '''Fetch the value specified by path'''
        if self.store == None:
            return None
        if len(path) == 0:
            return self.raw_value()
        key = path.pop(0)
        if key >= len(self.store):
            # path does not exist yet
            return None
        else:
            return self.store[key].get_value_by_path(path)

    def create_path(self, path: list):
        '''Ensures the path exists'''
        if len(path) == 0:
            return
        key = path.pop(0)
        if self.store == None:
            self.store = []
            for i in range(0, key):
                self.append(None)
            self.append(None)
        elif key >= len(self.store):
            for i in range(len(self.store), key):
                self.append(None)
            self.append(None)
        self.store[key].create_path(path)

    def set_value_by_path(self, value, path):
        if len(path) == 0:
            self.update(value)
        else:
            key = path.pop(0)
            self.store[key].set_value_by_path(value, path)

    def __getitem__(self, key):
        return self.store[key]

    def __setitem__(self, key, value):
        self.store[key] = attach_schema_to_value(value, self.schema.get_item_schema())

    def __contains__(self, item: int):
        # in operator
        return item < len(self.store)


class ValueWithAnyOfSchema(ValueWithSchema):
    '''Value with AnyOfSchema attached
    
    store here is an instance of ValueWithSchema
    '''

    def __init__(self, value, schema) -> None:
        self.schema = schema
        if value == None:
            self.store = None

        for possible_schema in self.schema.get_possibilities():
            if self.__validate(value, possible_schema):
                self.store = attach_schema_to_value(value, possible_schema)
                return
        raise TypeError('Value [%s] Path [%s]' % (value, self.schema.get_path()))

    def __validate(self, value, schema) -> bool:
        # XXX: Fragile! Use a complete validation utility from library
        if value == None:
            return True
        elif isinstance(value, dict) and isinstance(schema, ObjectSchema):
            return True
        elif isinstance(value, list) and isinstance(schema, ArraySchema):
            return True
        elif isinstance(value, str) and isinstance(schema, StringSchema):
            return True
        elif isinstance(value, bool) and isinstance(schema, BooleanSchema):
            return True
        elif isinstance(value, int) and isinstance(schema, IntegerSchema):
            return True
        elif isinstance(value, (float, int)) and isinstance(schema, NumberSchema):
            return True
        else:
            return False

    def __str__(self) -> str:
        if self.schema == None:
            ret = 'None'
        else:
            ret = str(self.store)
        return ret

    def raw_value(self) -> dict:
        '''serialization'''
        if self.store == None:
            return None
        else:
            return self.store.raw_value()

    def mutate(self, p_delete=0.05, p_replace=0.1):
        '''Mutate a small portion of the value
        
        - Replace with null
        - Replace with a new value
        - Mutate depend on the current schema
        '''
        if self.store == None:
            value = self.schema.gen()
            self.update(value)
        else:
            dice = random.random()
            if dice < p_delete:
                self.store = None
            elif dice < p_replace:
                self.update(self.schema.gen())
            else:
                self.store.mutate()

    def update(self, value):
        if value == None:
            self.store = None
        else:
            for possible_schema in self.schema.get_possibilities():
                if self.__validate(value, possible_schema):
                    self.store = attach_schema_to_value(value, possible_schema)
                    return
            raise TypeError('Value [%s] Path [%s]' % (value, self.schema.get_path()))

    def get_value_by_path(self, path: list):
        '''Fetch the value specified by path'''
        if self.store == None:
            return None
        else:
            return self.store.get_value_by_path(path)

    def create_path(self, path: list):
        '''Ensures the path exists'''
        if len(path) == 0:
            return
        key = path.pop(0)

        # XXX: Complicated, no use case yet, let's implement later
        raise NotImplementedError

    def set_value_by_path(self, value, path):
        if len(path) == 0:
            self.update(value)
        else:
            self.store.set_value_by_path(value, path)


class ValueWithBasicSchema(ValueWithSchema):
    '''Value with schema attached for Number/Integer, Bool, String'''

    def __init__(self, value, schema) -> None:
        self.schema = schema
        if value is None:
            self.store = None
        else:
            self.store = value

    def value(self):
        return self.store

    def __str__(self) -> str:
        if self.store == None:
            ret = 'None'
        else:
            ret = str(self.store)
        return ret

    def raw_value(self) -> dict:
        '''serialization'''
        return self.store

    def mutate(self, p_delete=0.05, p_replace=0.1):
        '''Generate a new value or set to null
        '''
        if self.store == None:
            self.store = self.schema.gen()
        else:
            dice = random.random()
            if dice < p_delete:
                self.store = None
            else:
                self.update(self.schema.gen())

    def update(self, value):
        if value is None:
            self.store = None
        else:
            self.store = value

    def get_value_by_path(self, path: list):
        if len(path) > 0:
            raise Exception('Reached basic value, but path is not exhausted')
        return self.store

    def create_path(self, path: list):
        if len(path) == 0:
            return
        else:
            raise Exception('Reached basic value, but path is not exhausted')

    def set_value_by_path(self, value, path):
        if len(path) == 0:
            self.update(value)
        else:
            raise Exception('Reached basic value, but path is not exhausted')


class ValueWithOpaqueSchema(ValueWithSchema):
    '''Value with an opaque schema'''

    def __init__(self, value, schema) -> None:
        self.schema = schema
        self.store = value

    def raw_value(self) -> object:
        return self.store

    def mutate(self):
        return

    def update(self, value):
        self.store = value


def attach_schema_to_value(value, schema):
    if isinstance(schema, ObjectSchema):
        return ValueWithObjectSchema(value, schema)
    elif isinstance(schema, ArraySchema):
        return ValueWithArraySchema(value, schema)
    elif isinstance(schema, AnyOfSchema):
        return ValueWithAnyOfSchema(value, schema)
    elif isinstance(schema, OpaqueSchema):
        return ValueWithOpaqueSchema(value, schema)
    else:
        return ValueWithBasicSchema(value, schema)


if __name__ == '__main__':
    with open('data/rabbitmq-operator/operator.yaml', 'r') as operator_yaml:
        parsed_operator_documents = yaml.load_all(operator_yaml, Loader=yaml.FullLoader)
        for document in parsed_operator_documents:
            if document['kind'] == 'CustomResourceDefinition':
                spec_schema = ObjectSchema(document['spec']['versions'][0]['schema']
                                           ['openAPIV3Schema']['properties']['spec'])

    with open('data/rabbitmq-operator/cr.yaml', 'r') as cr_yaml:
        cr = yaml.load(cr_yaml, Loader=yaml.FullLoader)
    value = attach_schema_to_value(cr['spec'], spec_schema)
    print(type(spec_schema))
    print(str(value))
    value.mutate()
    print(value.raw_value())