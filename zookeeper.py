import input
import schema


class InitContainerschema(schema.ObjectSchema):

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)

    def __init__(self, schema_obj: schema.BaseSchema) -> None:
        super().__init__(schema_obj.path, schema_obj.raw_schema)

    def get_all_schemas(self) -> list:
        '''Return all the subschemas as a list'''
        return [self]

    def __str__(self) -> str:
        return 'initContainers'


class PersistenceSchema(schema.ObjectSchema):

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)

    def __init__(self, schema_obj: schema.BaseSchema) -> None:
        super().__init__(schema_obj.path, schema_obj.raw_schema)

    def get_all_schemas(self) -> list:
        '''Return all the subschemas as a list'''
        return [self]

    def __str__(self) -> str:
        return 'persistence'


class AffinitySchema(schema.ObjectSchema):

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)

    def __init__(self, schema_obj: schema.BaseSchema) -> None:
        super().__init__(schema_obj.path, schema_obj.raw_schema)

    def get_all_schemas(self) -> list:
        '''Return all the subschemas as a list'''
        return [self]

    def __str__(self) -> str:
        return 'affinity'


class ContainersSchema(schema.ObjectSchema):

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)

    def __init__(self, schema_obj: schema.BaseSchema) -> None:
        super().__init__(schema_obj.path, schema_obj.raw_schema)

    def get_all_schemas(self) -> list:
        '''Return all the subschemas as a list'''
        return [self]

    def __str__(self) -> str:
        return 'containers'


class VolumesSchema(schema.ObjectSchema):

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)

    def __init__(self, schema_obj: schema.BaseSchema) -> None:
        super().__init__(schema_obj.path, schema_obj.raw_schema)

    def get_all_schemas(self) -> list:
        '''Return all the subschemas as a list'''
        return [self]

    def __str__(self) -> str:
        return 'volumes'

class PodSchema(schema.ObjectSchema):

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)

    def __init__(self, schema_obj: schema.BaseSchema) -> None:
        super().__init__(schema_obj.path, schema_obj.raw_schema)

    def get_all_schemas(self) -> list:
        '''Return all the subschemas as a list'''
        return [self]

    def __str__(self) -> str:
        return 'pod'

custom_fields = [
    # input.CustomField(['spec', 'initContainers'], InitContainerschema),
    input.CustomField(['spec', 'persistence'], PersistenceSchema),
    # input.CustomField(['spec', 'containers'], ContainersSchema),
    # input.CustomField(['spec', 'volumes'], VolumesSchema),
    input.CustomField(['spec', 'pod'], PodSchema),
]