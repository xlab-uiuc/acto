from typing import List, Tuple

from acto.input.testcase import (K8sInvalidTestCase, K8sTestCase, Store,
                                 TestCase)
from acto.schema import BaseSchema, IntegerSchema, ObjectSchema, StringSchema

from .base import (K8sArraySchema, K8sIntegerSchema, K8sObjectSchema,
                   K8sStringSchema)
from .pod_schemas import PodSpecSchema


class PodManagementPolicySchema(K8sStringSchema):

    def change_pod_management_policy(prev) -> str:
        if prev == "Parallel":
            return "OrderedReady"
        else:
            return "Parallel"

    def invalid_pod_management_policy(prev) -> str:
        return "InvalidPodManagementPolicy"

    ChangePodManagementPolicy = K8sTestCase(lambda prev: prev is not None,
                                            change_pod_management_policy, lambda prev: "Parallel")

    InvalidPodManagementPolicy = K8sInvalidTestCase(lambda prev: prev is not None,
                                                    invalid_pod_management_policy,
                                                    lambda prev: "Parallel")

    def gen(self, exclude_value=None, **kwargs):
        if exclude_value == None:
            return "OrderedReady"
        elif exclude_value == "Parallel":
            return "OrderedReady"
        else:
            return "Parallel"

    def Match(schema: ObjectSchema) -> bool:
        return isinstance(schema, StringSchema)

    def __str__(self) -> str:
        return "PodManagementPolicy"


class ReplicasSchema(K8sIntegerSchema):
    '''ScaleDownUp and ScaleUpDown'''

    def scaleDownUpPrecondition(prev, store: Store) -> bool:
        if store.data == None:
            store.data = True
            return False
        else:
            return True

    def scaleDownUp(prev) -> int:
        if prev == None:
            return 4
        return prev + 2

    def scaleDownUpSetup(prev) -> int:
        if prev == None:
            return 1
        return prev - 2

    def scaleUpDownPrecondition(prev, store: Store) -> bool:
        if store.data == None:
            store.data = True
            return False
        else:
            return True

    def scaleUpDown(prev) -> int:
        if prev == None:
            return 1
        return prev - 2

    def scaleUpDownSetup(prev) -> int:
        if prev == None:
            return 5
        return prev + 2

    def overload(prev) -> int:
        return 1000

    ScaleDownUp = K8sTestCase(scaleDownUpPrecondition, scaleDownUp, scaleDownUpSetup, Store())
    ScaleUpDown = K8sTestCase(scaleUpDownPrecondition, scaleUpDown, scaleUpDownSetup, Store())
    Overload = K8sInvalidTestCase(lambda prev: prev is not None, overload, lambda prev: prev)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs) -> list:
        if exclude_value is None:
            return 3
        else:
            return exclude_value + 1

    def Match(schema: ObjectSchema) -> bool:
        return isinstance(schema, IntegerSchema)

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].extend(
            [ReplicasSchema.ScaleDownUp, ReplicasSchema.ScaleUpDown, ReplicasSchema.Overload])
        return base_testcases

    def __str__(self) -> str:
        return "Replicas"


class PodTemplateSchema(K8sObjectSchema):

    fields = {
        "metadata": K8sObjectSchema,
        "spec": PodSpecSchema,
    }

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in PodTemplateSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in PodTemplateSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "PodTemplate"


class RollingUpdateSchema(K8sObjectSchema):

    fields = {
        "partition": K8sIntegerSchema,
    }

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in RollingUpdateSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in RollingUpdateSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "RollingUpdate"


class UpdateStrategyTypeSchema(K8sStringSchema):

    def update_strategy_change_precondition(prev):
        return prev is not None

    def update_strategy_change(prev):
        if prev == 'RollingUpdate':
            return 'OnDelete'
        else:
            return 'RollingUpdate'

    def update_strategy_change_setup(prev):
        return 'RollingUpdate'

    def invalid_update_strategy(prev):
        return 'InvalidUpdateStrategy'

    UpdateStrategyChangeTestcase = K8sTestCase(update_strategy_change_precondition,
                                               update_strategy_change, update_strategy_change_setup)

    InvalidUpdateStrategy = K8sInvalidTestCase(lambda prev: prev is not None,
                                               invalid_update_strategy,
                                               lambda prev: 'RollingUpdate')

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        self.default = 'RollingUpdate'

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        if exclude_value == 'OnDelete':
            return 'RollingUpdate'
        else:
            return 'OnDelete'

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].extend([
            UpdateStrategyTypeSchema.UpdateStrategyChangeTestcase,
            UpdateStrategyTypeSchema.InvalidUpdateStrategy
        ])
        return base_testcases

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "UpdateStrategyType"


class UpdateStrategySchema(K8sObjectSchema):

    fields = {
        "rollingUpdate": RollingUpdateSchema,
        "type": UpdateStrategyTypeSchema,
    }

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in UpdateStrategySchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in UpdateStrategySchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "UpdateStrategy"


class StatefulSetSpecSchema(K8sObjectSchema):

    fields = {
        'podManagementPolicy': PodManagementPolicySchema,
        'replicas': ReplicasSchema,
        'selector': K8sObjectSchema,
        'serviceName': K8sStringSchema,
        'template': PodTemplateSchema,
        'updateStrategy': UpdateStrategySchema,
        'volumeClaimTemplates': K8sArraySchema,
    }

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in StatefulSetSpecSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in StatefulSetSpecSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "StatefulSetSpecSchema"


class StatefulSetSchema(K8sObjectSchema):

    fields = {"metadata": K8sObjectSchema, "spec": StatefulSetSpecSchema}

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in StatefulSetSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in StatefulSetSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "StatefulSetSchema"
