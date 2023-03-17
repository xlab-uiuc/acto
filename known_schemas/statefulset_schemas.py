from typing import List, Tuple
from schema import BaseSchema, ObjectSchema
from known_schemas.base import K8sStringSchema, K8sObjectSchema, K8sArraySchema, K8sIntegerSchema
from known_schemas.pod_schemas import PodSpecSchema
from schema import BaseSchema, IntegerSchema, StringSchema
from test_case import Store, TestCase, K8sTestCase


class PodManagementPolicySchema(K8sStringSchema):

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
        return prev + 1

    def scaleDownUpSetup(prev) -> int:
        if prev == None:
            return 1
        return prev - 1

    def scaleUpDownPrecondition(prev, store: Store) -> bool:
        if store.data == None:
            store.data = True
            return False
        else:
            return True

    def scaleUpDown(prev) -> int:
        return prev - 1

    def scaleUpDownSetup(prev) -> int:
        if prev == None:
            return 4
        return prev + 1

    ScaleDownUp = K8sTestCase(scaleDownUpPrecondition, scaleDownUp, scaleDownUpSetup, Store())
    ScaleUpDown = K8sTestCase(scaleUpDownPrecondition, scaleUpDown, scaleUpDownSetup, Store())

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs) -> list:
        if exclude_value is None:
            return 3
        else:
            return exclude_value + 1

    def Match(schema: ObjectSchema) -> bool:
        return isinstance(schema, IntegerSchema)

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].extend([ReplicasSchema.ScaleDownUp, ReplicasSchema.ScaleUpDown])
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


class UpdateStrategySchema(K8sStringSchema):

    def update_strategy_change_precondition(prev):
        return prev is not None

    def update_strategy_change(prev):
        if prev == 'RollingUpdate':
            return 'OnDelete'
        else:
            return 'RollingUpdate'

    def update_strategy_change_setup(prev):
        return 'RollingUpdate'

    UpdateStrategyChangeTestcase = K8sTestCase(update_strategy_change_precondition,
                                               update_strategy_change, update_strategy_change_setup)

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
        base_testcases[1].extend([UpdateStrategySchema.UpdateStrategyChangeTestcase])
        return super().test_cases()

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "UpdateStrategy"


class StatefulSetSpecSchema(K8sObjectSchema):

    fields = {
        'podManagementPolicy': PodManagementPolicySchema,
        'replicas': ReplicasSchema,
        'selector': K8sObjectSchema,
        'serviceName': K8sStringSchema,
        'template': PodTemplateSchema,
        'updateStrategy': K8sObjectSchema,
        'volumeClaimTemplates': K8sArraySchema
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
