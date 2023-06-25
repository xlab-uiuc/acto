from typing import List, Tuple

from acto.input.testcase import K8sInvalidTestCase, K8sTestCase, TestCase
from acto.k8s_util.k8sutil import (canonicalize_quantity, double_quantity,
                                   half_quantity)
from acto.schema import (AnyOfSchema, BaseSchema, IntegerSchema, ObjectSchema,
                         StringSchema, extract_schema)

from .base import K8sAnyOfSchema, K8sObjectSchema


class QuantitySchema(K8sAnyOfSchema):

    def increase_precondition(prev) -> bool:
        if prev == None:
            return False
        elif canonicalize_quantity(prev) == 'INVALID':
            return False
        return True

    def quantity_increase(prev):
        return double_quantity(prev)

    def increase_setup(prev):
        return "1000m"

    def decrease_precondition(prev) -> bool:
        if prev == None:
            return False
        elif canonicalize_quantity(prev) == 'INVALID':
            return False
        return True

    def quantity_decrease(prev):
        return half_quantity(prev)

    def decrease_setup(prev):
        return "1000m"

    Increase = K8sTestCase(increase_precondition, quantity_increase, increase_setup)
    Decrease = K8sTestCase(decrease_precondition, quantity_decrease, decrease_setup)

    def Match(schema: AnyOfSchema) -> bool:
        if not K8sAnyOfSchema.Match(schema):
            return False
        for sub_schema in schema.get_possibilities():
            if not isinstance(sub_schema, StringSchema) and not isinstance(
                    sub_schema, IntegerSchema):
                return False

        return True

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        return '1000m'

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_test_cases = super().test_cases()
        base_test_cases[1].extend([QuantitySchema.Increase, QuantitySchema.Decrease])
        return base_test_cases

    def __str__(self) -> str:
        return "Quantity"


class ResourceSchema(K8sObjectSchema):

    additional_properties = QuantitySchema

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        self.additional_properties = ResourceSchema.additional_properties(
            self.additional_properties)

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        if schema.additional_properties is None:
            return False
        return ResourceSchema.additional_properties.Match(schema.additional_properties)

    def __str__(self) -> str:
        return "Resource"


class ComputeResourceSchema(ResourceSchema):

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        cpu_schema = extract_schema(self.path + ['cpu'], self.additional_properties.raw_schema)
        memory_schema = extract_schema(self.path + ['memory'],
                                       self.additional_properties.raw_schema)
        self.properties['cpu'] = QuantitySchema(cpu_schema)
        self.properties['memory'] = QuantitySchema(memory_schema)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs) -> list:
        return {'cpu': '1000m', 'memory': '1000m'}


class StorageResourceSchema(ResourceSchema):

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        storage_schema = extract_schema(self.path + ['storage'],
                                        self.additional_properties.raw_schema)
        self.properties['storage'] = QuantitySchema(storage_schema)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs) -> list:
        return {'storage': '1000m'}

    def __str__(self) -> str:
        return "StorageResource"


class ComputeResourceRequirementsSchema(K8sObjectSchema):

    fields = {"limits": ComputeResourceSchema, "requests": ComputeResourceSchema}

    INVALID_COMPUTE_RESOURCE_REQUIREMENTS = {"requests": {"hugepages-2Mi": "1000m",}}

    def invalid_compute_resource(prev):
        return ComputeResourceRequirementsSchema.INVALID_COMPUTE_RESOURCE_REQUIREMENTS

    invalid_compute_resource_test = K8sInvalidTestCase(
        lambda prev: True, invalid_compute_resource,
        lambda prev: ComputeResourceRequirementsSchema.INVALID_COMPUTE_RESOURCE_REQUIREMENTS)

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in ComputeResourceRequirementsSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs) -> dict:
        return {
            "requests": {
                "cpu": "800m",
                "memory": "1000m"
            },
            "limits": {
                "cpu": "800m",
                "memory": "1000m"
            }
        }

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        if len(schema.properties) != len(ResourceRequirementsSchema.fields):
            return False
        for field, field_schema in ResourceRequirementsSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False

        return True

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_test_cases = super().test_cases()
        base_test_cases[0].clear()
        base_test_cases[1].append(ComputeResourceRequirementsSchema.invalid_compute_resource_test)
        return base_test_cases

    def __str__(self) -> str:
        return "ComputeResourceRequirements"


class StorageResourceRequirementsSchema(K8sObjectSchema):

    fields = {"limits": StorageResourceSchema, "requests": StorageResourceSchema}

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in StorageResourceRequirementsSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs) -> dict:
        return {
            "requests": {
                "storage": "1000m"
            },
        }

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        if len(schema.properties) != len(ResourceRequirementsSchema.fields):
            return False
        for field, field_schema in ResourceRequirementsSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False

        return True

    def __str__(self) -> str:
        return "StorageResourceRequirements"


class ResourceRequirementsSchema(K8sObjectSchema):

    fields = {"limits": ResourceSchema, "requests": ResourceSchema}

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in ResourceRequirementsSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs) -> dict:
        return {
            "requests": {
                "cpu": "800m"
            },
            "limits": {
                "cpu": "800m"
            },
        }

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        if len(schema.properties) != len(ResourceRequirementsSchema.fields):
            return False
        for field, field_schema in ResourceRequirementsSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False

        return True

    def __str__(self) -> str:
        return "ResourceRequirements"
