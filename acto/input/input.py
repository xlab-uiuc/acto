import abc
import glob
import importlib
import json
import logging
import operator
import random
import threading
import sys
from functools import reduce
from typing import List, Optional, Tuple
from tqdm import tqdm

import pydantic
import yaml

from acto import DEFAULT_KUBERNETES_VERSION
from acto.common import is_subfield
from acto.input import k8s_schemas, property_attribute
from acto.input.get_matched_schemas import find_matched_schema
from acto.input.test_generators.generator import get_testcases
from acto.schema import BaseSchema
from acto.schema.schema import extract_schema
from acto.utils import get_thread_logger

from .testcase import TestCase
from .testplan import DeterministicTestPlan, TestGroup, TestPlan
from .value_with_schema import attach_schema_to_value


class CustomKubernetesMapping(pydantic.BaseModel):
    """Class for specifying custom mapping"""

    schema_path: list[str]
    kubernetes_schema_name: str


class InputMetadata(pydantic.BaseModel):
    """Metadata for the result of input model"""

    total_number_of_schemas: int = 0
    number_of_matched_kubernetes_schemas: int = 0
    total_number_of_test_cases: int = 0
    number_of_run_test_cases: int = 0
    number_of_primitive_test_cases: int = 0
    number_of_semantic_test_cases: int = 0
    number_of_misoperations: int = 0
    number_of_pruned_test_cases: int = 0


# The number of test cases to form a group
CHUNK_SIZE = 10


class InputModel(abc.ABC):
    """An abstract class for input model"""

    NORMAL = "NORMAL"
    OVERSPECIFIED = "OVERSPECIFIED"
    COPIED_OVER = "COPIED_OVER"
    SEMANTIC = "SEMANTIC"
    ADDITIONAL_SEMANTIC = "ADDITIONAL_SEMANTIC"

    @abc.abstractmethod
    def set_worker_id(self, worker_id: int):
        """Claim this thread"s id, so that we can split the test plan among threads"""
        raise NotImplementedError

    @abc.abstractmethod
    def generate_test_plan(
        self,
        delta_from: Optional[str] = None,
        focus_fields: Optional[list] = None,
    ) -> dict:
        """Generate test plan based on CRD"""
        raise NotImplementedError

    @abc.abstractmethod
    def set_mode(self, mode: str):
        """Set the mode of the test plan"""
        raise NotImplementedError

    @abc.abstractmethod
    def is_empty(self):
        """if test plan is empty"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_seed_input(self) -> dict:
        """Get the raw value of the seed input"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_schema_by_path(self, path: list) -> BaseSchema:
        """Get the schema by path"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_all_schemas(self):
        """Get all the schemas as a list"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_root_schema(self) -> BaseSchema:
        """Get the root schema"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_discarded_tests(self) -> dict:
        """Get the discarded tests"""
        raise NotImplementedError

    @abc.abstractmethod
    def discard_test_case(self):
        """Discard the test case that was selected"""
        raise NotImplementedError

    @abc.abstractmethod
    def next_test(
        self,
    ) -> Optional[List[Tuple[TestGroup, tuple[str, TestCase]]]]:
        """Selects next test case to run from the test plan

        Instead of random, it selects the next test case from the group.
        If the group is exhausted, it returns None, and will move to next group.

        Returns:
            Tuple of (new value, if this is a setup)
        """
        raise NotImplementedError


class DeterministicInputModel(InputModel):
    """A concrete input model that generates input deterministically"""

    def __init__(
        self,
        crd: dict,
        seed_input: Optional[dict],
        example_dir: Optional[str],
        num_workers: int,
        num_cases: int,
        mount: Optional[list] = None,
        kubernetes_version: str = DEFAULT_KUBERNETES_VERSION,
        custom_module_path: Optional[str] = None,
    ) -> None:
        # Mount allows to only test a subtree of the CRD
        if mount is not None:
            self.mount = mount
        else:
            self.mount = ["spec"]  # We model the cr.spec as the input

        # Load the CRD
        self.root_schema = extract_schema(
            [], crd["spec"]["versions"][-1]["schema"]["openAPIV3Schema"]
        )

        # Load all example documents
        self.example_dir = example_dir
        example_docs = []
        if self.example_dir is not None:
            for example_filepath in glob.glob(self.example_dir + "*.yaml"):
                with open(
                    example_filepath, "r", encoding="utf-8"
                ) as example_file:
                    docs = yaml.load_all(example_file, Loader=yaml.FullLoader)
                    for doc in docs:
                        example_docs.append(doc)
        for example_doc in example_docs:
            self.root_schema.load_examples(example_doc)

        self.p_bar_intialized = False
        self.p_bar = None
        self.num_workers = num_workers
        self.num_cases = num_cases  # number of test cases to run at a time

        # Initialize the seed input
        if seed_input is not None:
            initial_value = seed_input
            initial_value["metadata"]["name"] = "test-cluster"
            self.seed_input = attach_schema_to_value(
                initial_value, self.root_schema
            )
        else:
            self.seed_input = None

        self.k8s_paths = find_matched_schema(self.root_schema)

        self.thread_vars = threading.local()

        # Initialize the metadata, to be filled in the generate_test_plan
        self.metadata = InputMetadata()
        self.normal_test_plan_partitioned: list[
            list[list[tuple[str, TestCase]]]
        ] = []
        self.discarded_tests: dict[str, list] = {}

        override_matches: Optional[list[tuple[BaseSchema, str]]] = None
        if custom_module_path is not None:
            custom_module = importlib.import_module(custom_module_path)

            # We need to do very careful sanitization here because we are
            # loading user-provided module
            if hasattr(custom_module, "KUBERNETES_TYPE_MAPPING"):
                custum_kubernetes_type_mapping = (
                    custom_module.KUBERNETES_TYPE_MAPPING
                )
                if isinstance(custum_kubernetes_type_mapping, list):
                    override_matches = []
                    for custom_mapping in custum_kubernetes_type_mapping:
                        if isinstance(custom_mapping, CustomKubernetesMapping):
                            try:
                                schema = self.get_schema_by_path(
                                    custom_mapping.schema_path
                                )
                            except KeyError as exc:
                                raise RuntimeError(
                                    "Schema path of the custom mapping is invalid: "
                                    f"{custom_mapping.schema_path}"
                                ) from exc

                            override_matches.append(
                                (schema, custom_mapping.kubernetes_schema_name)
                            )
                        else:
                            raise TypeError(
                                "Expected CustomKubernetesMapping in KUBERNETES_TYPE_MAPPING, "
                                f"but got {type(custom_mapping)}"
                            )

        # Do the matching from CRD to Kubernetes schemas
        mounted_schema = self.get_schema_by_path(self.mount)
        self.metadata.total_number_of_schemas = len(
            mounted_schema.get_all_schemas()[0]
        )

        # Match the Kubernetes schemas to subproperties of the root schema
        kubernetes_schema_matcher = k8s_schemas.K8sSchemaMatcher.from_version(
            kubernetes_version, override_matches
        )
        top_matched_schemas = (
            kubernetes_schema_matcher.find_top_level_matched_schemas(
                mounted_schema
            )
        )
        for base_schema, k8s_schema_name in top_matched_schemas:
            logging.info(
                "Matched schema %s to k8s schema %s",
                base_schema.get_path(),
                k8s_schema_name,
            )
        self.full_matched_schemas = (
            kubernetes_schema_matcher.expand_top_level_matched_schemas(
                top_matched_schemas
            )
        )

        for base_schema, k8s_schema_name in self.full_matched_schemas:
            base_schema.attributes |= (
                property_attribute.PropertyAttribute.Mapped
            )

        # Apply custom property attributes based on the property_attribute module
        self.apply_custom_field()

    def set_worker_id(self, worker_id: int):
        """Claim this thread"s id, so that we can split the test plan among threads"""

        if hasattr(self.thread_vars, "id"):
            # Avoid initialize twice
            return

        # Thread local variables
        self.thread_vars.id = worker_id
        # so that we can run the test case itself right after the setup
        self.thread_vars.normal_test_plan = DeterministicTestPlan()
        self.thread_vars.semantic_test_plan = TestPlan(
            self.root_schema.to_tree()
        )

        for group in self.normal_test_plan_partitioned[worker_id]:
            self.thread_vars.normal_test_plan.add_testcase_group(
                TestGroup(group)
            )

    def generate_test_plan(
        self,
        delta_from: Optional[str] = None,
        focus_fields: Optional[list] = None,
    ) -> dict:
        """Generate test plan based on CRD"""
        logger = get_thread_logger(with_prefix=False)

        ########################################
        # Generate test plan
        ########################################

        normal_testcases = {}

        test_cases = get_testcases(
            self.get_schema_by_path(self.mount), self.full_matched_schemas
        )

        num_test_cases = 0
        num_run_test_cases = 0
        num_primitive_test_cases = 0
        num_semantic_test_cases = 0
        num_misoperations = 0
        num_pruned_test_cases = 0
        for path, test_case_list in test_cases:
            # First, check if the path is in the focus fields
            if focus_fields is not None:
                focused = False
                for focus_field in focus_fields:
                    if is_subfield(path, focus_field):
                        focused = True
                        break
                if not focused:
                    continue

            path_str = (
                json.dumps(path)
                .replace('"ITEM"', "0")
                .replace("additional_properties", "ACTOKEY")
            )

            # Filter by test case attributes
            filtered_test_case_list = []
            for test_case in test_case_list:
                num_test_cases += 1
                if test_case.primitive:
                    num_primitive_test_cases += 1
                if test_case.kubernetes_schema and test_case.primitive:
                    # This is a primitive test case for a k8s schema
                    # Primitive test cases are pruned for k8s schemas
                    num_pruned_test_cases += 1
                    continue
                if test_case.semantic:
                    num_semantic_test_cases += 1
                if test_case.invalid:
                    num_misoperations += 1
                filtered_test_case_list.append(test_case)
                num_run_test_cases += 1

            normal_testcases[path_str] = filtered_test_case_list

        self.metadata.total_number_of_test_cases = num_test_cases
        self.metadata.number_of_run_test_cases = num_run_test_cases
        self.metadata.number_of_primitive_test_cases = num_pruned_test_cases
        self.metadata.number_of_semantic_test_cases = num_semantic_test_cases
        self.metadata.number_of_misoperations = num_misoperations
        self.metadata.number_of_pruned_test_cases = num_pruned_test_cases

        logger.info("Generated %d test cases in total", num_test_cases)
        logger.info("Generated %d test cases to run", num_run_test_cases)
        logger.info(
            "Generated %d primitive test cases", num_primitive_test_cases
        )
        logger.info("Generated %d semantic test cases", num_semantic_test_cases)
        logger.info("Generated %d misoperations", num_misoperations)
        logger.info("Generated %d pruned test cases", num_pruned_test_cases)

        normal_test_plan_items = list(normal_testcases.items())
        # randomize to reduce skewness among workers
        random.shuffle(normal_test_plan_items)

        def split_into_subgroups(
            test_plan_items,
        ) -> list[list[Tuple[str, TestCase]]]:
            all_testcases = []
            for path, testcases in test_plan_items:
                for testcase in testcases:
                    all_testcases.append((path, testcase))

            subgroups = []
            for i in range(0, len(all_testcases), CHUNK_SIZE):
                subgroups.append(all_testcases[i : i + CHUNK_SIZE])
            return subgroups

        normal_subgroups = split_into_subgroups(normal_test_plan_items)

        # Initialize the three test plans, and assign test cases to them
        # according to the number of workers
        for i in range(self.num_workers):
            self.normal_test_plan_partitioned.append([])

        for i in range(0, len(normal_subgroups)):
            self.normal_test_plan_partitioned[i % self.num_workers].append(
                normal_subgroups[i]
            )

        # appending empty lists to avoid no test cases distributed to certain
        # work nodes
        assert self.num_workers == len(self.normal_test_plan_partitioned)

        return {
            "normal_testcases": normal_testcases,
        }

    def next_test(
        self,
    ) -> Optional[List[Tuple[TestGroup, tuple[str, TestCase]]]]:
        """Selects next test case to run from the test plan

        Instead of random, it selects the next test case from the group.
        If the group is exhausted, it returns None, and will move to next group.

        Returns:
            Tuple of (new value, if this is a setup)
        """
        logger = get_thread_logger(with_prefix=True)
        if self.p_bar_intialized:
            self.p_bar.update(1)
            self.p_bar.refresh()
        else:
            self.p_bar = tqdm(total=self.metadata.number_of_run_test_cases, initial=1, position=0, leave=True)
            self.p_bar_intialized = True
        
        logger.info("Progress [%d] cases left", len(self.thread_vars.test_plan))

        selected_group: TestGroup = self.thread_vars.test_plan.next_group()

        if selected_group is None:
            return None
        elif len(selected_group) == 0:
            return None
        else:
            testcase = selected_group.get_next_testcase()
            return [(selected_group, testcase)]

    def set_mode(self, mode: str):
        if mode == InputModel.NORMAL:
            self.thread_vars.test_plan = self.thread_vars.normal_test_plan
        elif mode == "OVERSPECIFIED":
            self.thread_vars.test_plan = (
                self.thread_vars.overspecified_test_plan
            )
        elif mode == "COPIED_OVER":
            self.thread_vars.test_plan = self.thread_vars.copiedover_test_plan
        elif mode == InputModel.SEMANTIC:
            self.thread_vars.test_plan = self.thread_vars.semantic_test_plan
        elif mode == InputModel.ADDITIONAL_SEMANTIC:
            self.thread_vars.test_plan = (
                self.thread_vars.additional_semantic_test_plan
            )
        else:
            raise ValueError(mode)

    def is_empty(self):
        """if test plan is empty"""
        return len(self.thread_vars.test_plan) == 0

    def get_seed_input(self) -> dict:
        """Get the raw value of the seed input"""
        return self.seed_input.raw_value()

    def get_schema_by_path(self, path: list) -> BaseSchema:
        return reduce(operator.getitem, path, self.root_schema)  # type: ignore

    def get_all_schemas(self):
        """Get all the schemas as a list"""
        return self.root_schema.get_all_schemas()

    def get_root_schema(self) -> BaseSchema:
        return self.root_schema

    def get_discarded_tests(self) -> dict:
        return self.discarded_tests

    def discard_test_case(self):
        """Discard the test case that was selected"""
        logger = get_thread_logger(with_prefix=True)

        discarded_case = self.thread_vars.test_plan[
            self.thread_vars.curr_field
        ].pop()

        # Log it to discarded_tests
        if self.thread_vars.curr_field in self.discarded_tests:
            self.discarded_tests[self.thread_vars.curr_field].append(
                discarded_case
            )
        else:
            self.discarded_tests[self.thread_vars.curr_field] = [discarded_case]
        logger.info(
            "Setup failed due to invalid, discard this testcase %s",
            discarded_case,
        )

        if len(self.thread_vars.test_plan[self.thread_vars.curr_field]) == 0:
            del self.thread_vars.test_plan[self.thread_vars.curr_field]
        self.thread_vars.curr_field = None

    def apply_custom_field(self):
        """Applies custom field to the input model

        Relies on the __setitem__ and __getitem__ methods of schema class
        """

        for (
            property_path,
            attribute,
        ) in property_attribute.PROPERTY_ATTRIBUTES.items():
            schema = reduce(
                operator.getitem, property_path.path, self.root_schema
            )

            s1, s2, s3 = schema.get_all_schemas()
            for s in s1:
                s.attributes |= attribute
            for s in s2:
                s.attributes |= attribute
            for s in s3:
                s.attributes |= attribute

    def apply_default_value(self, default_value_result: dict):
        """Takes default value result from static analysis and apply to schema

        Args:
            default_value_result: default_value_map in static analysis result
        """
        for key, value in default_value_result.items():
            path = json.loads(key)[1:]  # get rid of leading "root"
            decoded_value = json.loads(value)
            if isinstance(decoded_value, dict):
                for k, v in decoded_value.items():
                    decoded_value[k] = json.loads(v)
                    logging.info(
                        "Setting default value for %s to %s",
                        path + [k],
                        decoded_value[k],
                    )
                    self.get_schema_by_path(path + [k]).set_default(
                        decoded_value[k]
                    )
            else:
                logging.info(
                    "Setting default value for %s to %s", path, decoded_value
                )
                self.get_schema_by_path(path).set_default(value)
