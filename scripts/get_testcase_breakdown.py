import inspect

import known_schemas
from known_schemas.base import *
from test_case import K8sInvalidTestCase, K8sTestCase, TestCase


def get_testcase_breakdown():
    total_number = 0
    invalid_number = 0
    num_properties = 0
    for name, obj in inspect.getmembers(known_schemas):
        if inspect.isclass(obj) and issubclass(obj, K8sSchema):
            for _, class_member in inspect.getmembers(obj):
                # print(class_member)
                # if isinstance(class_member, K8sInvalidTestCase):
                #     print(class_member)
                # elif isinstance(class_member, K8sTestCase):
                #     print(class_member)
                if isinstance(class_member, TestCase):
                    if isinstance(class_member, K8sInvalidTestCase):
                        invalid_number += 1
                    total_number += 1
            if issubclass(obj, K8sStringSchema):
                total_number += 3
            elif issubclass(obj, K8sIntegerSchema):
                total_number += 2
            elif issubclass(obj, K8sObjectSchema):
                total_number += 2
            elif issubclass(obj, K8sArraySchema):
                total_number += 4
            elif issubclass(obj, K8sBooleanSchema):
                total_number += 2
            elif issubclass(obj, AnyOfSchema):
                total_number += 6
    print(f'Total number of test cases: {total_number}')
    print(f'Number of invalid test cases: {invalid_number}')
    print(f'Number of properties: {num_properties}')

if __name__ == '__main__':
    get_testcase_breakdown()