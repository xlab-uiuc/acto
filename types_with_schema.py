from collections.abc import MutableMapping, MutableSequence
import yaml

from schema import ObjectSchema, ArraySchema


class DictWithSchema(MutableMapping):
    '''Dict-like structure, but with schema attached'''

    def __init__(self, value: dict, schema) -> None:
        self.schema = schema
        if value is None:
            self.store = None
        elif isinstance(value, dict):
            self.store = {}
            for k, v in value.items():
                self.store[k] = attach_schema(v,
                                              self.schema.get_child_schema(k))
        else:
            raise TypeError

    def __getitem__(self, key):
        return self.store[key]

    def __setitem__(self, key, value):
        self.store[key] = attach_schema(value,
                                        self.schema.get_child_schema(key))

    def __delitem__(self, key):
        del self.store[key]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def __str__(self) -> str:
        if self.store == None:
            return 'None'
        else:
            ret = '{'
            for k, v in self.store.items():
                ret += str(k)
                ret += ':'
                ret += str(v)
                ret += ', '
            ret += '}'
            return ret


class ListWithSchema(MutableSequence):
    '''List-like structure, with schema attached'''

    def __init__(self, value, schema) -> None:
        self.schema = schema
        if value is None:
            self.store = None
        elif isinstance(value, list):
            for i in value:
                self.store.append(attach_schema(i, self.schema.item_schema()))
        else:
            raise TypeError

    def __getitem__(self, i):
        return self.store[i]

    def __setitem__(self, key, value):
        self.store[key] = attach_schema(value,
                                        self.schema.get_child_schema(key))

    def __delitem__(self, key):
        del self.store[key]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def insert(self, i, v):
        self.list.insert(i, attach_schema(v, self.schema.item_schema()))

    def __str__(self) -> str:
        if self.store == None:
            return 'None'
        else:
            ret = '['
            for i in self.store:
                ret += str(i)
                ret += ', '
            ret += ']'
            return ret


class ValueWithSchema():
    '''Primitive, with schema attached'''

    def __init__(self, value, schema) -> None:
        self.schema = schema
        if value is None:
            self.store = None
        elif isinstance(value, dict):
            self.store = {}
            for k, v in value.items():
                self.store[k] = attach_schema(v,
                                              self.schema.get_child_schema(k))
        elif isinstance(value, list):
            value = []
            for i in value:
                self.store.append(attach_schema(i, self.schema.item_schema()))
        else:
            self.store = value

    def value(self):
        return self.store

    def __str__(self) -> str:
        if self.store == None:
            ret = 'None'
        elif isinstance(self.store, dict):
            ret = '{'
            for k, v in self.store.items():
                ret += str(k)
                ret += ':'
                ret += str(v)
                ret += ', '
            ret += '}'
        elif isinstance(self.store, list):
            ret = '['
            for i in self.store:
                ret += str(i)
                ret += ', '
            ret += ']'
        else:
            ret = str(self.store)
        return ret


def attach_schema(value, schema):
    if isinstance(schema, ObjectSchema):
        return DictWithSchema(value, schema)
    elif isinstance(schema, ArraySchema):
        return ListWithSchema(value, schema)
    else:
        return ValueWithSchema(value, schema)


if __name__ == '__main__':
    with open('data/rabbitmq-operator/operator.yaml', 'r') as operator_yaml:
        parsed_operator_documents = yaml.load_all(operator_yaml,
                                                  Loader=yaml.FullLoader)
        for document in parsed_operator_documents:
            if document['kind'] == 'CustomResourceDefinition':
                spec_schema = ObjectSchema(
                    document['spec']['versions'][0]['schema']['openAPIV3Schema']
                    ['properties']['spec'])

    with open('data/rabbitmq-operator/test.yaml', 'r') as cr_yaml:
        cr = yaml.load(cr_yaml, Loader=yaml.FullLoader)
    value = ValueWithSchema(cr['spec'], spec_schema)
    print(type(spec_schema))
    print(str(value))