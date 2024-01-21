# pylint: disable=missing-docstring, line-too-long

import os
import pathlib
import unittest

import yaml

from acto.input.generator import TEST_GENERATORS, generator, get_testcases
from acto.input.k8s_schemas import K8sSchemaMatcher
from acto.input.testcase import TestCase
from acto.schema import extract_schema

test_dir = pathlib.Path(__file__).parent.resolve()
test_data_dir = os.path.join(test_dir, "test_data")


def gen(_):
    return [TestCase("test", lambda x: True, lambda x: None, lambda x: None)]


class TestSchema(unittest.TestCase):
    """This class tests the schema matching code for various CRDs."""

    @classmethod
    def setUpClass(cls):
        with open(
            os.path.join(test_data_dir, "rabbitmq_crd.yaml"),
            "r",
            encoding="utf-8",
        ) as operator_yaml:
            rabbitmq_crd = yaml.load(operator_yaml, Loader=yaml.FullLoader)
        schema_matcher = K8sSchemaMatcher.from_version("1.29")
        cls.spec_schema = extract_schema(
            [], rabbitmq_crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"]
        )
        cls.matches = schema_matcher.find_matched_schemas(cls.spec_schema)

    def test_path_suffix(self):
        TEST_GENERATORS.clear()
        generator(paths=["serviceAccountToken/expirationSeconds"])(gen)
        testcases = get_testcases(self.spec_schema, self.matches)
        self.assertEqual(len(testcases), 1)

        TEST_GENERATORS.clear()
        generator(
            paths=[
                "serviceAccountToken/expirationSeconds",
                "volumes/ITEM/quobyte/user",
            ]
        )(gen)
        testcases = get_testcases(self.spec_schema, self.matches)
        self.assertEqual(len(testcases), 2)

    def test_k8s_schema_name(self):
        TEST_GENERATORS.clear()
        generator(k8s_schema_name="v1.NodeAffinity")(gen)
        testcases = get_testcases(self.spec_schema, self.matches)
        self.assertEqual(len(testcases), 2)

        TEST_GENERATORS.clear()
        generator(k8s_schema_name="HTTPHeader")(gen)
        testcases = get_testcases(self.spec_schema, self.matches)
        self.assertEqual(len(testcases), 15)

    def test_field_name(self):
        TEST_GENERATORS.clear()
        generator(field_name="ports")(gen)
        testcases = get_testcases(self.spec_schema, self.matches)
        self.assertEqual(len(testcases), 4)

        TEST_GENERATORS.clear()
        generator(field_name="image")(gen)
        testcases = get_testcases(self.spec_schema, self.matches)
        self.assertEqual(len(testcases), 5)

    def test_field_type(self):
        TEST_GENERATORS.clear()
        generator(field_type="AnyOf")(gen)
        testcases = get_testcases(self.spec_schema, self.matches)
        self.assertEqual(len(testcases), 38)

        TEST_GENERATORS.clear()
        generator(field_type="Array")(gen)
        testcases = get_testcases(self.spec_schema, self.matches)
        self.assertEqual(len(testcases), 173)

        TEST_GENERATORS.clear()
        generator(field_type="Boolean")(gen)
        testcases = get_testcases(self.spec_schema, self.matches)
        self.assertEqual(len(testcases), 73)

        TEST_GENERATORS.clear()
        generator(field_type="Integer")(gen)
        testcases = get_testcases(self.spec_schema, self.matches)
        self.assertEqual(len(testcases), 106)

        TEST_GENERATORS.clear()
        generator(field_type="Number")(gen)
        testcases = get_testcases(self.spec_schema, self.matches)
        self.assertEqual(len(testcases), 106)

        TEST_GENERATORS.clear()
        generator(field_type="Object")(gen)
        testcases = get_testcases(self.spec_schema, self.matches)
        self.assertEqual(len(testcases), 368)

        # TEST_GENERATORS.clear()
        # generator(field_type="OneOf")(gen)
        # testcases = get_testcases(self.spec_schema, self.matches)
        # self.assertEqual(len(testcases), 0)

        # TEST_GENERATORS.clear()
        # generator(field_type="Opaque")(gen)
        # testcases = get_testcases(self.spec_schema, self.matches)
        # self.assertEqual(len(testcases), 0)

        TEST_GENERATORS.clear()
        generator(field_type="String")(gen)
        testcases = get_testcases(self.spec_schema, self.matches)
        self.assertEqual(len(testcases), 550)

    def test_priority(self):
        TEST_GENERATORS.clear()

        @generator(field_type="Integer", priority=0)
        def gen0(_):
            return [
                TestCase(
                    "integer-test",
                    lambda x: True,
                    lambda x: None,
                    lambda x: None,
                )
            ]

        @generator(field_name="replicas", priority=1)
        def gen1(_):
            return [
                TestCase(
                    "replicas-test",
                    lambda x: True,
                    lambda x: None,
                    lambda x: None,
                )
            ]

        testcases = get_testcases(self.spec_schema, self.matches)
        for path, tests in testcases:
            if path[-1] == "replicas":
                self.assertEqual(tests[0].name, "replicas-test")
            else:
                self.assertEqual(tests[0].name, "integer-test")
