from typing import List, Tuple
from schema import BaseSchema, ObjectSchema
from known_schemas.base import K8sBooleanSchema, K8sStringSchema, K8sObjectSchema, K8sArraySchema, K8sIntegerSchema
from test_case import TestCase, K8sTestCase


class ConcurrencyPolicySchema(K8sStringSchema):

    def concurrency_policy_change_precondition(prev):
        return prev is not None

    def concurrency_policy_change(prev):
        if prev == 'Forbid':
            return 'Replace'
        else:
            return 'Forbid'

    def concurrency_policy_change_setup(prev):
        return 'Forbid'

    ConcurrencyPolicyChangeTestcase = K8sTestCase(concurrency_policy_change_precondition,
                                                  concurrency_policy_change,
                                                  concurrency_policy_change_setup)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        if exclude_value == 'Replace':
            return 'Forbid'
        else:
            return 'Replace'

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].extend([ConcurrencyPolicySchema.ConcurrencyPolicyChangeTestcase])
        return base_testcases

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "ConcurrencyPolicy"


class CronJobScheduleSchema(K8sStringSchema):

    def cronjob_schedule_change_precondition(prev):
        return prev is not None

    def cronjob_schedule_change(prev):
        if prev == '0 0 * * *':
            return '0 0 * * *1'
        else:
            return '0 0 * * *'

    def cronjob_schedule_change_setup(prev):
        return '0 0 * * *'

    CronJobScheduleChangeTestcase = K8sTestCase(cronjob_schedule_change_precondition,
                                                cronjob_schedule_change,
                                                cronjob_schedule_change_setup)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        return "0 0 * * *"

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].extend([CronJobScheduleSchema.CronJobScheduleChangeTestcase])
        return base_testcases

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "CronJobSchedule"


class CronJobSpecSchema(K8sObjectSchema):

    fields = {
        'concurrencyPolicy': ConcurrencyPolicySchema,
        "schedule": CronJobScheduleSchema,
        "startingDeadlineSeconds": K8sIntegerSchema,
        "successfulJobsHistoryLimit": K8sIntegerSchema,
        "suspend": K8sBooleanSchema,
        "failedJobsHistoryLimit": K8sIntegerSchema,
        "jobTemplate": K8sObjectSchema,
    }

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in CronJobSpecSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True


class CronJobSchema(K8sObjectSchema):

    fields = {
        'metadata': K8sObjectSchema,
        'spec': CronJobSpecSchema,
    }

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in CronJobSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "CronJob"
