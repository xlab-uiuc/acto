import input
import schema


class OverrideSchema(schema.ObjectSchema):

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)

    def __init__(self, schema_obj: schema.BaseSchema) -> None:
        super().__init__(schema_obj.path, schema_obj.raw_schema)

    def get_all_schemas(self) -> list:
        '''Return all the subschemas as a list'''
        return [self]

    def __str__(self) -> str:
        return 'override'


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


class TolerationSchema(schema.ObjectSchema):

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)

    def __init__(self, schema_obj: schema.BaseSchema) -> None:
        super().__init__(schema_obj.path, schema_obj.raw_schema)

    def get_all_schemas(self) -> list:
        '''Return all the subschemas as a list'''
        return [self]

    def __str__(self) -> str:
        return 'toleration'


class PodtemplatespecSchema(schema.ObjectSchema):

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)

    def __init__(self, schema_obj: schema.BaseSchema) -> None:
        super().__init__(schema_obj.path, schema_obj.raw_schema)

    def get_all_schemas(self) -> list:
        '''Return all the subschemas as a list'''
        return [self]

    def __str__(self) -> str:
        return 'podTemplateSpec'


custom_fields = [
    # input.CustomField(['spec', 'override'], OverrideSchema),
    # input.CustomField(['spec', 'affinity'], AffinitySchema),
    input.CustomField(['spec', 'podTemplateSpec'], PodtemplatespecSchema)
]