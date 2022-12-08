from typing import List, Tuple
from schema import AnyOfSchema, BaseSchema, IntegerSchema, ObjectSchema, StringSchema
from known_schemas.base import K8sObjectSchema, K8sAnyOfSchema
from schema import BaseSchema
from k8s_util.k8sutil import canonicalizeQuantity, double_quantity, half_quantity
from test_case import TestCase

class QuantitySchema(K8sAnyOfSchema):

    def increase_precondition(prev) -> bool:
        if prev == None:
            return False
        elif canonicalizeQuantity(prev) == 'INVALID':
            return False
        return True

    def increase(prev):
        return double_quantity(prev)

    def increase_setup(prev):
        return "1000m"

    def decrease_precondition(prev) -> bool:
        if prev == None:
            return False
        elif canonicalizeQuantity(prev) == 'INVALID':
            return False
        return True

    def decrease(prev):
        return half_quantity(prev)

    def decrease_setup(prev):
        return "1000m"

    Increase = TestCase(increase_precondition, increase, increase_setup)
    Decrease = TestCase(decrease_precondition, decrease, decrease_setup)

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
        self.properties['cpu'] = QuantitySchema(self.additional_properties)
        self.properties['memory'] = QuantitySchema(self.additional_properties)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs) -> list:
        return {'cpu': '1000m', 'memory': '1000m'}


class StorageResourceSchema(ResourceSchema):

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        self.properties['storage'] = QuantitySchema(self.additional_properties)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs) -> list:
        return {'storage': '1000m'}

    def __str__(self) -> str:
        return "StorageResource"


class ComputeResourceRequirementsSchema(K8sObjectSchema):

    fields = {"limits": ComputeResourceSchema, "requests": ComputeResourceSchema}

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in ComputeResourceRequirementsSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs) -> dict:
        ret = {}
        for field, field_schema in ComputeResourceRequirementsSchema.fields.items():
            ret[field] = field_schema.gen()
        return ret

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
        return "ResourceRequirements"


class ResourceRequirementsSchema(K8sObjectSchema):

    fields = {"limits": ResourceSchema, "requests": ResourceSchema}

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in ResourceRequirementsSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs) -> dict:
        ret = {}
        for field, field_schema in ResourceRequirementsSchema.fields.items():
            ret[field] = field_schema.gen()
        return ret

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
