from typing import List, Tuple
from schema import BaseSchema, ObjectSchema
from known_schemas.base import K8sBooleanSchema, K8sStringSchema, K8sObjectSchema, K8sArraySchema, K8sIntegerSchema
from known_schemas.resource_schemas import StorageResourceRequirementsSchema
from test_case import TestCase

class AccessModeSchema(K8sStringSchema):

    def change_access_mode_precondition(prev):
        return prev is not None

    def change_access_mode(prev):
        if prev == 'ReadWriteOnce':
            return 'ReadWriteMany'
        else:
            return 'ReadWriteOnce'

    def change_access_mode_setup(prev):
        return 'ReadWriteOnce'

    AccessModeChangeTestcase = TestCase(change_access_mode_precondition, change_access_mode,
                                        change_access_mode_setup)

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        self.enum = ['ReadWriteOnce', 'ReadOnlyMany', 'ReadWriteMany', 'ReadWriteOncePod']

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        if exclude_value == 'ReadWriteOnce':
            return 'ReadOnlyMany'
        else:
            return 'ReadWriteOnce'

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].extend([AccessModeSchema.AccessModeChangeTestcase])
        return base_testcases

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "AccessMode"


class StorageClassNameSchema(K8sStringSchema):

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        self.default = 'standard'

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        return 'standard'

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "StorageClassName"


class PersistentVolumeClaimSpecSchema(K8sObjectSchema):

    fields = {
        "accessModes": AccessModeSchema,
        "dataSource": K8sObjectSchema,
        "resources": StorageResourceRequirementsSchema,
        "selector": K8sObjectSchema,
        "storageClassName": K8sStringSchema,
        "volumeMode": K8sStringSchema,  # Filesystem or Block
        "volumeName": K8sStringSchema
    }

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in PersistentVolumeClaimSpecSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in PersistentVolumeClaimSpecSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "PersistentVolumeClaimSpec"


class PersistentVolumeClaimSchema(K8sObjectSchema):

    fields = {"metadata": K8sObjectSchema, "spec": PersistentVolumeClaimSpecSchema}

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in PersistentVolumeClaimSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in PersistentVolumeClaimSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "PersistentVolumeClaimSchema"
