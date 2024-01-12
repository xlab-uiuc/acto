import abc
import glob
import inspect
import json
import logging
import operator
import random
import threading
from functools import reduce
from typing import List, Optional, Tuple

import yaml

from acto.common import is_subfield, random_string
from acto.input import known_schemas
from acto.input.get_matched_schemas import find_matched_schema
from acto.input.valuegenerator import extract_schema_with_value_generator
from acto.schema import BaseSchema, IntegerSchema
from acto.utils import get_thread_logger, is_prefix

from .known_schemas import K8sField
from .testcase import TestCase
from .testplan import DeterministicTestPlan, TestGroup, TestPlan
from .value_with_schema import attach_schema_to_value


def covered_by_k8s(k8s_fields: list[list[str]], path: list[str]) -> bool:
    if path[-1] == "additional_properties":
        return True

    for k8s_path in k8s_fields:
        if is_prefix(k8s_path, path):
            return True
    return False


class CustomField:
    def __init__(self, path, used_fields: Optional[list]) -> None:
        self.path = path
        self.used_fields = used_fields


class CopiedOverField(CustomField):
    """For pruning the fields that are simply copied over to other resources

    All the subfields of this field (excluding this field) will be pruned
    """

    def __init__(
        self, path, used_fields: Optional[list] = None, array: bool = False
    ) -> None:
        super().__init__(path, used_fields)


class OverSpecifiedField(CustomField):
    """For pruning the fields that are simply copied over to other resources

    All the subfields of this field (excluding this field) will be pruned
    """

    def __init__(
        self, path, used_fields: Optional[list] = None, array: bool = False
    ) -> None:
        super().__init__(path, used_fields)


class ProblematicField(CustomField):
    """For pruning the field that can not be simply generated using Acto"s current generation mechanism.

    All the subfields of this field (including this field itself) will be pruned
    """

    def __init__(self, path, array: bool = False, string: bool = False) -> None:
        super().__init__(path, [])


class PatchField(CustomField):
    """For pruning the field that can not be simply generated using Acto"s current generation mechanism.

    All the subfields of this field (including this field itself) will be pruned
    """

    def __init__(self, path) -> None:
        super().__init__(path, None)


class MappedField(CustomField):
    """For annotating the field to be checked against the system state"""

    def __init__(self, path) -> None:
        super().__init__(path, None)


class InputModel(abc.ABC):
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
        used_fields: list,
        example_dir: Optional[str],
        num_workers: int,
        num_cases: int,
        mount: Optional[list] = None,
    ) -> None:
        if mount is not None:
            self.mount = mount
        else:
            self.mount = ["spec"]  # We model the cr.spec as the input
        self.root_schema = extract_schema_with_value_generator(
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

        self.used_fields = used_fields
        self.num_workers = num_workers
        self.num_cases = num_cases  # number of test cases to run at a time
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

        self.metadata = {
            "normal_schemas": 0,
            "pruned_by_overspecified": 0,
            "pruned_by_copied": 0,
            "num_normal_testcases": 0,
            "num_overspecified_testcases": 0,
            "num_copiedover_testcases": 0,
        }  # to fill in the generate_test_plan function

        self.normal_test_plan_partitioned: list[
            list[list[tuple[str, TestCase]]]
        ] = []
        self.overspecified_test_plan_partitioned: list[
            list[list[tuple[str, TestCase]]]
        ] = []
        self.copiedover_test_plan_partitioned: list[
            list[list[tuple[str, TestCase]]]
        ] = []
        self.semantic_test_plan_partitioned: list[
            list[tuple[str, list[TestCase]]]
        ] = []
        self.additional_semantic_test_plan_partitioned: list[
            list[list[tuple[str, TestCase]]]
        ] = []

        self.discarded_tests: dict[str, list] = {}

    def set_worker_id(self, worker_id: int):
        """Claim this thread"s id, so that we can split the test plan among threads"""

        if hasattr(self.thread_vars, "id"):
            # Avoid initialize twice
            return

        # Thread local variables
        self.thread_vars.id = worker_id
        # so that we can run the test case itself right after the setup
        self.thread_vars.normal_test_plan = DeterministicTestPlan()
        self.thread_vars.overspecified_test_plan = DeterministicTestPlan()
        self.thread_vars.copiedover_test_plan = DeterministicTestPlan()
        self.thread_vars.additional_semantic_test_plan = DeterministicTestPlan()
        self.thread_vars.semantic_test_plan = TestPlan(
            self.root_schema.to_tree()
        )

        for group in self.normal_test_plan_partitioned[worker_id]:
            self.thread_vars.normal_test_plan.add_testcase_group(
                TestGroup(group)
            )

        for group in self.overspecified_test_plan_partitioned[worker_id]:
            self.thread_vars.overspecified_test_plan.add_testcase_group(
                TestGroup(group)
            )

        for group in self.copiedover_test_plan_partitioned[worker_id]:
            self.thread_vars.copiedover_test_plan.add_testcase_group(
                TestGroup(group)
            )

        for group_ in self.additional_semantic_test_plan_partitioned[worker_id]:
            self.thread_vars.additional_semantic_test_plan.add_testcase_group(
                TestGroup(group_)
            )

        for key, value in self.semantic_test_plan_partitioned[worker_id]:
            path = json.loads(key)
            self.thread_vars.semantic_test_plan.add_testcases_by_path(
                value, path
            )

    def generate_test_plan(
        self,
        delta_from: Optional[str] = None,
        focus_fields: Optional[list] = None,
    ) -> dict:
        """Generate test plan based on CRD"""
        logger = get_thread_logger(with_prefix=False)

        existing_testcases = {}
        if delta_from is not None:
            with open(delta_from, "r", encoding="utf-8") as delta_from_file:
                existing_testcases = json.load(delta_from_file)[
                    "normal_testcases"
                ]

        # Calculate the unused fields using used_fields from static analysis
        # tree: TreeNode = self.root_schema.to_tree()
        # for field in self.used_fields:
        #     field = field[1:]
        #     node = tree.get_node_by_path(field)
        #     if node is None:
        #         logger.warning(f"Field {field} not found in CRD")
        #         continue

        #     node.set_used()

        # def func(overspecified_fields: list, unused_fields: list, node: TreeNode) -> bool:
        #     if len(node.children) == 0:
        #         return False

        #     if not node.used:
        #         return False

        #     used_child = []
        #     for child in node.children.values():
        #         if child.used:
        #             used_child.append(child)
        #         else:
        #             unused_fields.append(child.path)

        #     if len(used_child) == 0:
        #         overspecified_fields.append(node.path)
        #         return False
        #     elif len(used_child) == len(node.children):
        #         return True
        #     else:
        #         return True

        # overspecified_fields = []
        # unused_fields = []
        # tree.traverse_func(partial(func, overspecified_fields, unused_fields))
        # for field in overspecified_fields:
        #     logger.info("Overspecified field: %s", field)
        # for field in unused_fields:
        #     logger.info("Unused field: %s", field)

        ########################################
        # Get all K8s schemas
        ########################################
        k8s_int_tests = []
        k8s_str_tests = []
        for name, obj in inspect.getmembers(known_schemas):
            if inspect.isclass(obj):
                if issubclass(obj, known_schemas.K8sIntegerSchema):
                    for _, class_member in inspect.getmembers(obj):
                        if isinstance(class_member, known_schemas.K8sTestCase):
                            k8s_int_tests.append(class_member)
                elif issubclass(obj, known_schemas.K8sStringSchema):
                    for _, class_member in inspect.getmembers(obj):
                        if isinstance(class_member, known_schemas.K8sTestCase):
                            k8s_str_tests.append(class_member)

        logger.info("Got %d K8s integer tests", len(k8s_int_tests))
        logger.info("Got %d K8s string tests", len(k8s_str_tests))

        ########################################
        # Generate test plan
        ########################################

        planned_normal_testcases = {}
        normal_testcases = {}
        semantic_testcases = {}
        additional_semantic_testcases = {}
        overspecified_testcases = {}
        copiedover_testcases = {}
        num_normal_testcases = 0
        num_overspecified_testcases = 0
        num_copiedover_testcases = 0
        num_semantic_testcases = 0
        num_additional_semantic_testcases = 0

        num_total_semantic_tests = 0
        num_total_invalid_tests = 0

        mounted_schema = self.get_schema_by_path(self.mount)
        (
            normal_schemas,
            semantic_schemas,
        ) = mounted_schema.get_normal_semantic_schemas()
        logger.info("Got %d normal schemas", len(normal_schemas))
        logger.info("Got %d semantic schemas", len(semantic_schemas))

        (
            normal_schemas,
            pruned_by_overspecified,
            pruned_by_copied,
        ) = mounted_schema.get_all_schemas()
        for schema in normal_schemas:
            # Skip if the schema is not in the focus fields
            if focus_fields is not None:
                logger.info("focusing on %s", focus_fields)
                focused = False
                for focus_field in focus_fields:
                    logger.info(
                        "Comparing %s with %s", schema.path, focus_field
                    )
                    if is_subfield(schema.path, focus_field):
                        focused = True
                        break
                if not focused:
                    continue

            path = (
                json.dumps(schema.path)
                .replace('"ITEM"', "0")
                .replace("additional_properties", "ACTOKEY")
            )
            testcases, semantic_testcases_ = schema.test_cases()
            planned_normal_testcases[path] = testcases
            if len(semantic_testcases_) > 0:
                semantic_testcases[path] = semantic_testcases_
                num_semantic_testcases += len(semantic_testcases_)
            if path in existing_testcases:
                continue
            normal_testcases[path] = testcases
            num_normal_testcases += len(testcases)

            if isinstance(schema, known_schemas.K8sSchema):
                for testcase in testcases:
                    if isinstance(testcase, known_schemas.K8sInvalidTestCase):
                        num_total_invalid_tests += 1
                    num_total_semantic_tests += 1

                for semantic_testcase in semantic_testcases_:
                    if isinstance(
                        semantic_testcase, known_schemas.K8sInvalidTestCase
                    ):
                        num_total_invalid_tests += 1
                    num_total_semantic_tests += 1

            if not isinstance(
                schema, known_schemas.K8sSchema
            ) and not covered_by_k8s(self.k8s_paths, list(schema.path)):
                if isinstance(schema, IntegerSchema):
                    additional_semantic_testcases[path] = list(k8s_int_tests)
                    num_additional_semantic_testcases += len(k8s_int_tests)
                # elif isinstance(schema, StringSchema):
                #     additional_semantic_testcases[path] = list(k8s_str_tests)
                #     num_additional_semantic_testcases += len(k8s_str_tests)

        for schema in pruned_by_overspecified:
            # Skip if the schema is not in the focus fields
            if focus_fields is not None:
                logger.info(f"focusing on {focus_fields}")
                focused = False
                for focus_field in focus_fields:
                    logger.info(f"Comparing {schema.path} with {focus_field}")
                    if is_subfield(schema.path, focus_field):
                        focused = True
                        break
                if not focused:
                    continue

            testcases, semantic_testcases_ = schema.test_cases()
            path = (
                json.dumps(schema.path)
                .replace('"ITEM"', "0")
                .replace("additional_properties", random_string(5))
            )
            if len(semantic_testcases_) > 0:
                semantic_testcases[path] = semantic_testcases_
                num_semantic_testcases += len(semantic_testcases_)
            overspecified_testcases[path] = testcases
            num_overspecified_testcases += len(testcases)

            if isinstance(schema, known_schemas.K8sSchema):
                for testcase in testcases:
                    if isinstance(testcase, known_schemas.K8sInvalidTestCase):
                        num_total_invalid_tests += 1
                        num_total_semantic_tests += 1

                for semantic_testcase in semantic_testcases_:
                    if isinstance(
                        semantic_testcase, known_schemas.K8sInvalidTestCase
                    ):
                        num_total_invalid_tests += 1
                    num_total_semantic_tests += 1

        for schema in pruned_by_copied:
            # Skip if the schema is not in the focus fields
            if focus_fields is not None:
                logger.info(f"focusing on {focus_fields}")
                focused = False
                for focus_field in focus_fields:
                    logger.info(f"Comparing {schema.path} with {focus_field}")
                    if is_subfield(schema.path, focus_field):
                        focused = True
                        break
                if not focused:
                    continue

            testcases, semantic_testcases_ = schema.test_cases()
            path = (
                json.dumps(schema.path)
                .replace('"ITEM"', "0")
                .replace("additional_properties", random_string(5))
            )
            if len(semantic_testcases_) > 0:
                semantic_testcases[path] = semantic_testcases_
                num_semantic_testcases += len(semantic_testcases_)
            copiedover_testcases[path] = testcases
            num_copiedover_testcases += len(testcases)

            if isinstance(schema, known_schemas.K8sSchema):
                for testcase in testcases:
                    if isinstance(testcase, known_schemas.K8sInvalidTestCase):
                        num_total_invalid_tests += 1
                        num_total_semantic_tests += 1

                for semantic_testcase in semantic_testcases_:
                    if isinstance(
                        semantic_testcase, known_schemas.K8sInvalidTestCase
                    ):
                        num_total_invalid_tests += 1
                    num_total_semantic_tests += 1

        logger.info(
            "Parsed [%d] fields from normal schema", len(normal_schemas)
        )
        logger.info(
            "Parsed [%d] fields from over-specified schema",
            len(pruned_by_overspecified),
        )
        logger.info(
            "Parsed [%d] fields from copied-over schema", len(pruned_by_copied)
        )

        logger.info(
            "Generated [%d] test cases for normal schemas", num_normal_testcases
        )
        logger.info(
            "Generated [%d] test cases for overspecified schemas",
            num_overspecified_testcases,
        )
        logger.info(
            "Generated [%d] test cases for copiedover schemas",
            num_copiedover_testcases,
        )
        logger.info(
            "Generated [%d] test cases for semantic schemas",
            num_semantic_testcases,
        )
        logger.info(
            "Generated [%d] test cases for additional semantic schemas",
            num_additional_semantic_testcases,
        )

        logger.info("Generated [%d] semantic tests", num_total_semantic_tests)
        logger.info("Generated [%d] invalid tests", num_total_invalid_tests)

        self.metadata["pruned_by_overspecified"] = len(pruned_by_overspecified)
        self.metadata["pruned_by_copied"] = len(pruned_by_copied)
        self.metadata["semantic_schemas"] = len(semantic_testcases)
        self.metadata["num_normal_testcases"] = num_normal_testcases
        self.metadata[
            "num_overspecified_testcases"
        ] = num_overspecified_testcases
        self.metadata["num_copiedover_testcases"] = num_copiedover_testcases
        self.metadata["num_semantic_testcases"] = num_semantic_testcases
        self.metadata[
            "num_additional_semantic_testcases"
        ] = num_additional_semantic_testcases

        logger.info(
            f"Generated {num_normal_testcases + num_semantic_testcases} normal testcases"
        )

        normal_test_plan_items = list(normal_testcases.items())
        overspecified_test_plan_items = list(overspecified_testcases.items())
        copiedover_test_plan_items = list(copiedover_testcases.items())
        semantic_test_plan_items = list(semantic_testcases.items())
        # randomize to reduce skewness among workers
        random.shuffle(normal_test_plan_items)
        random.shuffle(overspecified_test_plan_items)
        random.shuffle(copiedover_test_plan_items)
        random.shuffle(semantic_test_plan_items)

        # run semantic testcases anyway
        normal_test_plan_items.extend(semantic_test_plan_items)

        CHUNK_SIZE = 10

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
        overspecified_subgroups = split_into_subgroups(
            overspecified_test_plan_items
        )
        copiedover_subgroups = split_into_subgroups(copiedover_test_plan_items)

        # Initialize the three test plans, and assign test cases to them
        # according to the number of workers
        for i in range(self.num_workers):
            self.normal_test_plan_partitioned.append([])
            self.overspecified_test_plan_partitioned.append([])
            self.copiedover_test_plan_partitioned.append([])
            self.semantic_test_plan_partitioned.append([])
            self.additional_semantic_test_plan_partitioned.append([])

        for i in range(0, len(normal_subgroups)):
            self.normal_test_plan_partitioned[i % self.num_workers].append(
                normal_subgroups[i]
            )

        for i in range(0, len(overspecified_subgroups)):
            self.overspecified_test_plan_partitioned[
                i % self.num_workers
            ].append(overspecified_subgroups[i])

        for i in range(0, len(copiedover_subgroups)):
            self.copiedover_test_plan_partitioned[i % self.num_workers].append(
                copiedover_subgroups[i]
            )

        for i in range(0, len(semantic_test_plan_items)):
            self.semantic_test_plan_partitioned[i % self.num_workers].append(
                semantic_test_plan_items[i]
            )

        # appending empty lists to avoid no test cases distributed to certain
        # work nodes
        assert self.num_workers == len(self.normal_test_plan_partitioned)
        assert self.num_workers == len(self.overspecified_test_plan_partitioned)
        assert self.num_workers == len(self.copiedover_test_plan_partitioned)

        return {
            "delta_from": delta_from,
            "existing_testcases": existing_testcases,
            "normal_testcases": normal_testcases,
            "overspecified_testcases": overspecified_testcases,
            "copiedover_testcases": copiedover_testcases,
            "semantic_testcases": semantic_testcases,
            "planned_normal_testcases": planned_normal_testcases,
            "normal_subgroups": normal_subgroups,
            "overspecified_subgroups": overspecified_subgroups,
            "copiedover_subgroups": copiedover_subgroups,
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

    def apply_custom_field(self, custom_field: CustomField):
        """Applies custom field to the input model

        Relies on the __setitem__ and __getitem__ methods of schema class
        """
        path = custom_field.path
        if len(path) == 0:
            self.root_schema = custom_field.custom_schema(
                self.root_schema, custom_field.used_fields
            )

        # fetch the parent schema
        curr = self.root_schema
        for idx in path:
            curr = curr[idx]

        if isinstance(custom_field, PatchField):
            curr.patch = True
            s1, s2, s3 = curr.get_all_schemas()
            for s in s1:
                s.patch = True
            for s in s2:
                s.patch = True
            for s in s3:
                s.patch = True

        if isinstance(custom_field, MappedField):
            curr.mapped = True
            s1, s2, s3 = curr.get_all_schemas()
            for s in s1:
                s.mapped = True
            for s in s2:
                s.mapped = True
            for s in s3:
                s.mapped = True

        if isinstance(custom_field, CopiedOverField):
            curr.copied_over = True
        elif isinstance(custom_field, OverSpecifiedField):
            curr.over_specified = True
            s1, s2, s3 = curr.get_all_schemas()
            for s in s1:
                s.over_specified = True
            for s in s2:
                s.over_specified = True
            for s in s3:
                s.over_specified = True
        elif isinstance(custom_field, ProblematicField):
            curr.problematic = True
        elif isinstance(custom_field, PatchField) or isinstance(
            custom_field, MappedField
        ):
            pass  # do nothing, already handled above
        else:
            raise Exception("Unknown custom field type")

    def apply_k8s_schema(self, k8s_field: K8sField):
        path = k8s_field.path
        if len(path) == 0:
            self.root_schema = k8s_field.custom_schema(self.root_schema)

        # fetch the parent schema
        curr = self.root_schema
        for idx in path[:-1]:
            curr = curr[idx]

        # construct new schema
        custom_schema = k8s_field.custom_schema(curr[path[-1]])

        # replace old schema with the new one
        curr[path[-1]] = custom_schema

    def apply_candidates(self, candidates: dict, path: list):
        """Apply candidates file onto schema"""
        # TODO
        candidates_list = self.candidates_dict_to_list(candidates, path)

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
                        "Setting default value for %s to %s"
                        % (path + [k], decoded_value[k])
                    )
                    self.get_schema_by_path(path + [k]).set_default(
                        decoded_value[k]
                    )
            else:
                logging.info(
                    "Setting default value for %s to %s" % (path, decoded_value)
                )
                self.get_schema_by_path(path).set_default(value)

    def candidates_dict_to_list(self, candidates: dict, path: list) -> list:
        if "candidates" in candidates:
            return [(path, candidates["candidates"])]
        else:
            ret = []
            for key, value in candidates.items():
                ret.extend(self.candidates_dict_to_list(value, path + [key]))
            return ret
