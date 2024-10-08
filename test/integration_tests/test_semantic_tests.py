"""Integration tests for the semantic test generators."""

import json
import os
import pathlib
import unittest

import yaml

from acto import acto_config
from acto.engine import apply_testcase
from acto.input.input import DeterministicInputModel, InputModel
from acto.input.test_generators.pod import affinity_tests
from acto.input.value_with_schema import attach_schema_to_value
from acto.lib.operator_config import OperatorConfig
from acto.schema.schema import extract_schema

test_dir = pathlib.Path(__file__).parent.resolve()
test_data_dir = os.path.join(test_dir, "test_data")


class TestSemanticTests(unittest.TestCase):
    """Integration tests for the semantic test generators."""

    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)

        # prepare and load config
        config_path = os.path.join(
            test_dir.parent.parent, "data", "rabbitmq-operator", "config.json"
        )
        with open(config_path, "r", encoding="utf-8") as config_file:
            self.config = OperatorConfig(**json.load(config_file))

        # prepare context
        context_file = os.path.join(
            os.path.dirname(self.config.seed_custom_resource), "context.json"
        )
        with open(context_file, "r", encoding="utf-8") as context_fin:
            self.context = json.load(context_fin)
            self.context["preload_images"] = set(self.context["preload_images"])

        with open(
            self.config.seed_custom_resource, "r", encoding="utf-8"
        ) as cr_file:
            self.seed = yaml.load(cr_file, Loader=yaml.FullLoader)

        # prepare feature gate
        acto_config.load_config()

    def test_affinity_tests(self):
        """Test affinity tests."""

        crd = self.context["crd"]["body"]
        root_schema = extract_schema(
            [], crd["spec"]["versions"][-1]["schema"]["openAPIV3Schema"]
        )
        affinity_schema = root_schema["spec"]["affinity"]
        tests = affinity_tests(affinity_schema)

        value_with_schema = attach_schema_to_value(self.seed, root_schema)
        for test in tests:
            property_curr_value = value_with_schema.get_value_by_path(
                list(root_schema.path)
            )
            if not test.test_precondition(property_curr_value):
                apply_testcase(
                    value_with_schema, root_schema.path, test, setup=True
                )

            assert test.test_precondition(
                value_with_schema.get_value_by_path(list(root_schema.path))
            )

    def test_rbop_tests(self):
        """Test rbop tests."""

        input_model = DeterministicInputModel(
            crd=self.context["crd"]["body"],
            seed_input=self.seed,
            example_dir=self.config.example_dir,
            num_workers=1,
            num_cases=1,
            kubernetes_version=self.config.kubernetes_version,
            custom_module_path=self.config.custom_module,
        )

        input_model.generate_test_plan(focus_fields=None)
        input_model.set_worker_id(0)
        input_model.set_mode(InputModel.NORMAL)

        cr = self.seed

        while not input_model.is_empty():
            curr_input_with_schema = attach_schema_to_value(
                cr, input_model.get_root_schema()
            )
            test_groups = input_model.next_test()

            if test_groups is None:
                continue

            for group, testcase_with_path in test_groups:
                field_path_str, testcase = testcase_with_path
                field_path = json.loads(field_path_str)

                field_curr_value = curr_input_with_schema.get_value_by_path(
                    list(field_path)
                )

                if not testcase.test_precondition(field_curr_value):
                    apply_testcase(
                        curr_input_with_schema, field_path, testcase, setup=True
                    )

                if not testcase.test_precondition(
                    curr_input_with_schema.get_value_by_path(list(field_path))
                ):
                    raise AssertionError(
                        "Test precondition failed after applying the test case"
                        f" {testcase} to the field {field_path_str}"
                    )

                group.finish_testcase()


if __name__ == "__main__":
    unittest.main()
