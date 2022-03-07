from collections.abc import MutableMapping, MutableSequence
import yaml

from schema import AnyOfSchema, ObjectSchema, ArraySchema, StringSchema, NumberSchema, IntegerSchema, BooleanSchema


class ValueWithObjectSchema():

    def __init__(self, value, schema) -> None:
        self.schema = schema
        if value == None:
            self.store = None
        elif isinstance(value, dict):
            self.store = {}
            for k, v in value.items():
                self.store[k] = attach_schema_to_value(
                    v, self.schema.get_child_schema(k))
        else:
            raise TypeError

    def value(self):
        return self.store

    def __str__(self) -> str:
        if self.store == None:
            ret = 'None'
        else:
            ret = '{'
            for k, v in self.store.items():
                ret += str(k)
                ret += ':'
                ret += str(v)
                ret += ', '
            ret += '}'
        return ret


class ValueWithArraySchema():

    def __init__(self, value, schema) -> None:
        self.schema = schema
        if value == None:
            self.store = None
        elif isinstance(value, list):
            self.store = []
            for i in value:
                self.store.append(
                    attach_schema_to_value(i, self.schema.item_schema()))
        else:
            raise TypeError

    def value(self):
        return self.store

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


class ValueWithAnyOfSchema():
    '''Value with AnyOfSchema attached'''

    def __init__(self, value, schema) -> None:
        self.schema = schema
        if value == None:
            self.store = None

        for possible_schema in self.schema.possibilities():
            if self.__validate(value, possible_schema):
                self.store = attach_schema_to_value(value, possible_schema)
                return
        raise TypeError

    def __validate(self, value, schema) -> bool:
        # XXX: Fragile! Use a complete validation utility from library
        if isinstance(value, dict) and isinstance(schema, ObjectSchema):
            return True
        elif isinstance(value, list) and isinstance(schema, ArraySchema):
            return True
        elif isinstance(value, str) and isinstance(schema, StringSchema):
            return True
        elif isinstance(value, bool) and isinstance(schema, BooleanSchema):
            return True
        elif isinstance(value, int) and isinstance(schema, IntegerSchema):
            return True
        elif isinstance(value,
                        (float, int)) and isinstance(schema, NumberSchema):
            return True
        else:
            return False

    def __str__(self) -> str:
        if self.schema == None:
            ret = 'None'
        else:
            ret = str(self.store)
        return ret


class ValueWithSchema():
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


def attach_schema_to_value(value, schema):
    if isinstance(schema, ObjectSchema):
        return ValueWithObjectSchema(value, schema)
    elif isinstance(schema, ArraySchema):
        return ValueWithArraySchema(value, schema)
    elif isinstance(schema, AnyOfSchema):
        return ValueWithAnyOfSchema(value, schema)
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

    with open('data/rabbitmq-operator/cr.yaml', 'r') as cr_yaml:
        cr = yaml.load(cr_yaml, Loader=yaml.FullLoader)
    value = ValueWithSchema(cr['spec'], spec_schema)
    print(type(spec_schema))
    print(str(value))