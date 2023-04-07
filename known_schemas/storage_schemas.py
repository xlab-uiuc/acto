from typing import List, Tuple
from schema import BaseSchema, ObjectSchema, OpaqueSchema, StringSchema
from known_schemas.base import K8sBooleanSchema, K8sStringSchema, K8sObjectSchema, K8sArraySchema, K8sIntegerSchema
from .resource_schemas import QuantitySchema, StorageResourceRequirementsSchema
from test_case import TestCase, K8sTestCase


class HostPathTypeSchema(K8sStringSchema):

    def directory_or_create(prev):
        return "DirectoryOrCreate"

    def invalid_host_path_type(prev):
        return "InvalidHostPathType"

    DirectoryOrCreateTestcase = K8sTestCase(lambda prev: prev != "DirectoryOrCreate",
                                            directory_or_create, lambda prev: "Directory")

    InvalidHostPathTypeTestcase = K8sTestCase(lambda prev: prev != "DirectoryOrCreate",
                                              invalid_host_path_type, lambda prev: "Directory")

    def gen(self, exclude_value=None, **kwargs):
        if exclude_value == None:
            return "DirectoryOrCreate"
        elif exclude_value == "DirectoryOrCreate":
            return "Directory"
        else:
            return "DirectoryOrCreate"

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "HostPathType"


class FilePathSchema(K8sStringSchema):

    def tmp_file(prev):
        return "/tmp/test"

    TmpFileTestcase = K8sTestCase(lambda prev: prev != "/tmp/test", tmp_file,
                                  lambda prev: "/tmp/test2")

    def gen(self, exclude_value=None, **kwargs):
        if exclude_value == None:
            return "/tmp/test"
        elif exclude_value == "/tmp/test":
            return "/tmp/test2"
        else:
            return "/tmp/test"

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "FilePath"


class HostPathVolumeSourceSchema(K8sObjectSchema):

    fields = {"path": FilePathSchema, "type": HostPathTypeSchema}

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in HostPathVolumeSourceSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in HostPathVolumeSourceSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "HostPathVolumeSourceSchema"


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

    AccessModeChangeTestcase = K8sTestCase(change_access_mode_precondition, change_access_mode,
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

    def change_storage_class_name(prev):
        if prev == 'standard':
            return 'ssd'
        else:
            return 'standard'

    ChangeStorageClassNameTestcase = K8sTestCase(lambda prev: prev != "ssd",
                                                 change_storage_class_name, lambda prev: "ssd")

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
        "storageClassName": StorageClassNameSchema,
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


class ApiVersionSchema(K8sStringSchema):

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        if exclude_value == "v1":
            return "v2"
        return "v1"

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        return super().test_cases()

    def __str__(self) -> str:
        return "ApiVersion"


class PersistentVolumeClaimSchema(K8sObjectSchema):

    fields = {
        "apiVersion": ApiVersionSchema,
        "kind": OpaqueSchema,
        "metadata": K8sObjectSchema,
        "spec": PersistentVolumeClaimSpecSchema,
        "status": OpaqueSchema
    }

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in PersistentVolumeClaimSchema.fields.items():
            if field in schema_obj.properties and field_schema != OpaqueSchema:
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


class MediumSchema(K8sStringSchema):

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        self.enum = ['Memory', '']
        self.default = ''

    def Match(schema: StringSchema) -> bool:
        return super().Match()

    def __str__(self) -> str:
        return "Medium"


class EmptyDirVolumeSourceSchema(K8sObjectSchema):

    fields = {"medium": MediumSchema, "sizeLimit": QuantitySchema}

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in EmptyDirVolumeSourceSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in EmptyDirVolumeSourceSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "EmptyDirVolumeSourceSchema"