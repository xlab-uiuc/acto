from abc import abstractmethod
from typing import List, Tuple

from acto.input.valuegenerator import (AnyOfGenerator, ArrayGenerator,
                                       BooleanGenerator, IntegerGenerator,
                                       ObjectGenerator, OpaqueGenerator,
                                       StringGenerator)
from acto.schema import (AnyOfSchema, ArraySchema, BaseSchema, BooleanSchema,
                         IntegerSchema, ObjectSchema, OpaqueSchema,
                         StringSchema, extract_schema)


class K8sField():

    def __init__(self, path, schema) -> None:
        self.path = path
        self.custom_schema = schema


class K8sSchema():

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj.path, schema_obj.raw_schema)

    @abstractmethod
    def Match(schema) -> bool:
        pass


class K8sStringSchema(K8sSchema, StringGenerator):

    def Match(schema: StringSchema) -> bool:
        return isinstance(schema, StringSchema)
    
    def get_normal_semantic_schemas(self) -> Tuple[List['BaseSchema'], List['BaseSchema']]:
        return [], [self]


class K8sObjectSchema(K8sSchema, ObjectGenerator):

    def Match(schema: ObjectSchema) -> bool:
        return isinstance(schema, ObjectSchema)
    
    def get_normal_semantic_schemas(self) -> Tuple[List['BaseSchema'], List['BaseSchema']]:
        base, semantic = super().get_normal_semantic_schemas()
        return [], base + semantic


class K8sArraySchema(K8sSchema, ArrayGenerator):

    def Match(schema: ArraySchema) -> bool:
        return isinstance(schema, ArraySchema)
    
    def get_normal_semantic_schemas(self) -> Tuple[List['BaseSchema'], List['BaseSchema']]:
        base, semantic = super().get_normal_semantic_schemas()
        return [], base + semantic


class K8sIntegerSchema(K8sSchema, IntegerGenerator):

    def Match(schema: IntegerSchema) -> bool:
        return isinstance(schema, IntegerSchema)
    
    def get_normal_semantic_schemas(self) -> Tuple[List['BaseSchema'], List['BaseSchema']]:
        return [], [self]


class K8sBooleanSchema(K8sSchema, BooleanGenerator):

    def Match(schema: BooleanSchema) -> bool:
        return isinstance(schema, BooleanSchema)

    def get_normal_semantic_schemas(self) -> Tuple[List['BaseSchema'], List['BaseSchema']]:
        return [], [self]


class K8sAnyOfSchema(K8sSchema, AnyOfGenerator):

    def Match(schema: AnyOfSchema) -> bool:
        return isinstance(schema, AnyOfSchema)
    
    def get_normal_semantic_schemas(self) -> Tuple[List['BaseSchema'], List['BaseSchema']]:
        base, semantic = super().get_normal_semantic_schemas()
        return [], base + semantic

class K8sOpaqueSchema(K8sSchema, OpaqueGenerator):
    
    def Match(schema: OpaqueSchema) -> bool:
        return True
    
    def get_normal_semantic_schemas(self) -> Tuple[List['BaseSchema'], List['BaseSchema']]:
        return [], [self]