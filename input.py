from functools import partial, reduce
import json
import logging
import operator
import random
import threading
from typing import List, Tuple
from deepdiff import DeepDiff
import glob
import yaml

from schema import OpaqueSchema, StringSchema, extract_schema, BaseSchema, ObjectSchema, ArraySchema
from test_case import TestCase
from testplan import TestPlan
from value_with_schema import attach_schema_to_value
from common import random_string
from thread_logger import get_thread_logger
from testplan import TreeNode


class CustomField:

    def __init__(self, path, schema, used_fields: list) -> None:
        self.path = path
        self.custom_schema = schema
        self.used_fields = used_fields


class CopiedOverField(CustomField):
    '''For pruning the fields that are simply copied over to other resources
    
    All the subfields of this field (excluding this field) will be pruned
    '''

    class PruneChildrenObjectSchema(ObjectSchema):

        def __init__(self, path: list, schema: dict) -> None:
            super().__init__(path, schema)

        def __init__(self, schema_obj: BaseSchema, used_fields: list) -> None:
            self.used_fields = used_fields
            super().__init__(schema_obj.path, schema_obj.raw_schema)

        def get_all_schemas(self) -> list:
            '''Return all the subschemas as a list'''
            normal_schemas = [self]
            pruned_by_overspecified = []
            pruned_by_copiedover = []

            if self.properties != None:
                for value in self.properties.values():
                    child_schema_tuple = value.get_all_schemas()
                    normal_schemas.extend(child_schema_tuple[0])
                    pruned_by_overspecified.extend(child_schema_tuple[1])
                    pruned_by_copiedover.extend(child_schema_tuple[2])
            if self.additional_properties != None:
                normal_schemas.append(self.additional_properties)

            if len(self.used_fields) == 0:
                keep = [normal_schemas.pop()]
            else:
                keep = []
            for schema in normal_schemas:
                if schema.path in self.used_fields:
                    keep.append(schema)
                else:
                    pruned_by_copiedover.append(schema)
            normal_schemas = keep

            return normal_schemas, pruned_by_overspecified, pruned_by_copiedover

        def __str__(self) -> str:
            return 'Children Pruned'

    class PruneChildrenArraySchema(ArraySchema):

        def __init__(self, path: list, schema: dict) -> None:
            super().__init__(path, schema)

        def __init__(self, schema_obj: BaseSchema, used_fields: list) -> None:
            self.used_fields = used_fields
            super().__init__(schema_obj.path, schema_obj.raw_schema)

        def get_all_schemas(self) -> list:
            '''Return all the subschemas as a list'''
            normal_schemas = [self]
            pruned_by_overspecified = []
            pruned_by_copiedover = []

            child_schema_tuple = self.item_schema.get_all_schemas()
            child_normal_schemas = child_schema_tuple[0]
            for child_schema in child_normal_schemas:
                if child_schema.path in self.used_fields:
                    normal_schemas.append(child_schema)
                else:
                    pruned_by_copiedover.append(child_schema)
            if len(self.used_fields) == 0:
                normal_schemas.append(child_schema_tuple[0].pop())
            pruned_by_overspecified.extend(child_schema_tuple[1])
            pruned_by_copiedover.extend(child_schema_tuple[2])

            return normal_schemas, pruned_by_overspecified, pruned_by_copiedover

        def __str__(self) -> str:
            return 'Children Pruned'

    def __init__(self, path, used_fields: list = None, array: bool = False) -> None:
        if array:
            super().__init__(path, self.PruneChildrenArraySchema,
                             used_fields if used_fields != None else [])
        else:
            super().__init__(path, self.PruneChildrenObjectSchema,
                             used_fields if used_fields != None else [])


class OverSpecifiedField(CustomField):
    '''For pruning the fields that are simply copied over to other resources
    
    All the subfields of this field (excluding this field) will be pruned
    '''

    class OverSpecifiedObjectSchema(ObjectSchema):

        def __init__(self, path: list, schema: dict) -> None:
            super().__init__(path, schema)

        def __init__(self, schema_obj: BaseSchema, used_fields: list) -> None:
            self.used_fields = used_fields
            super().__init__(schema_obj.path, schema_obj.raw_schema)

        def get_all_schemas(self) -> list:
            '''Return all the subschemas as a list'''
            normal_schemas = [self]
            pruned_by_overspecified = []
            pruned_by_copiedover = []

            if self.properties != None:
                for value in self.properties.values():
                    child_schema_tuple = value.get_all_schemas()
                    normal_schemas.extend(child_schema_tuple[0])
                    pruned_by_overspecified.extend(child_schema_tuple[1])
                    pruned_by_copiedover.extend(child_schema_tuple[2])
            if self.additional_properties != None:
                normal_schemas.append(self.additional_properties)

            if len(self.used_fields) == 0:
                keep = [normal_schemas.pop()]
            else:
                keep = []
            for schema in normal_schemas:
                if schema.path in self.used_fields:
                    logging.debug('Keeping %s' % schema.path)
                    keep.append(schema)
                else:
                    pruned_by_overspecified.append(schema)
            normal_schemas = keep

            return normal_schemas, pruned_by_overspecified, pruned_by_copiedover

        def __str__(self) -> str:
            return 'Children Pruned'

    class OverSpecifiedArraySchema(ArraySchema):

        def __init__(self, path: list, schema: dict) -> None:
            super().__init__(path, schema)

        def __init__(self, schema_obj: BaseSchema, used_fields: list) -> None:
            self.used_fields = used_fields
            super().__init__(schema_obj.path, schema_obj.raw_schema)

        def get_all_schemas(self) -> list:
            '''Return all the subschemas as a list'''
            normal_schemas = [self]
            pruned_by_overspecified = []
            pruned_by_copiedover = []

            child_schema_tuple = self.item_schema.get_all_schemas()
            child_normal_schemas = child_schema_tuple[0]
            for child_schema in child_normal_schemas:
                if child_schema.path in self.used_fields:
                    normal_schemas.append(child_schema)
                else:
                    pruned_by_overspecified.append(child_schema)
            if len(self.used_fields) == 0:
                normal_schemas.append(child_schema_tuple[0].pop())
            pruned_by_overspecified.extend(child_schema_tuple[1])
            pruned_by_copiedover.extend(child_schema_tuple[2])

            return normal_schemas, pruned_by_overspecified, pruned_by_copiedover

        def __str__(self) -> str:
            return 'Children Pruned'

    def __init__(self, path, used_fields: list = None, array: bool = False) -> None:
        if array:
            super().__init__(path, self.OverSpecifiedArraySchema,
                             used_fields if used_fields != None else [])
        else:
            super().__init__(path, self.OverSpecifiedObjectSchema,
                             used_fields if used_fields != None else [])


class ProblematicField(CustomField):
    '''For pruning the field that can not be simply generated using Acto's current generation mechanism.
    
    All the subfields of this field (including this field itself) will be pruned
    '''

    class PruneEntireStringSchema(StringSchema):

        def __init__(self, path: list, schema: dict) -> None:
            super().__init__(path, schema)

        def __init__(self, schema_obj: BaseSchema) -> None:
            super().__init__(schema_obj.path, schema_obj.raw_schema)

        def get_all_schemas(self) -> Tuple[list, list, list]:
            return [], [], []

        def __str__(self):
            return "Field Pruned"

    class PruneEntireObjectSchema(ObjectSchema):

        def __init__(self, path: list, schema: dict) -> None:
            super().__init__(path, schema)

        def __init__(self, schema_obj: BaseSchema) -> None:
            super().__init__(schema_obj.path, schema_obj.raw_schema)

        def get_all_schemas(self) -> Tuple[list, list, list]:
            return [], [], []

        def __str__(self):
            return "Field Pruned"

    class PruneEntireArraySchema(ArraySchema):

        def __init__(self, path: list, schema: dict) -> None:
            super().__init__(path, schema)

        def __init__(self, schema_obj: BaseSchema) -> None:
            super().__init__(schema_obj.path, schema_obj.raw_schema)

        def get_all_schemas(self) -> Tuple[list, list, list]:
            return [], [], []

        def __str__(self):
            return "Field Pruned"

    def __init__(self, path, array: bool = False, string: bool = False) -> None:
        if array:
            super().__init__(path, self.PruneEntireArraySchema)
        elif string:
            super().__init__(path, self.PruneEntireStringSchema)
        else:
            super().__init__(path, self.PruneEntireObjectSchema)


class InputModel:

    NORMAL = 'NORMAL'
    OVERSPECIFIED = 'OVERSPECIFIED'
    COPIED_OVER = 'COPIED_OVER'

    def __init__(self,
                 crd: dict,
                 used_fields: list,
                 example_dir: str,
                 num_workers: int,
                 num_cases: int,
                 reproduce_dir: str,
                 mount: list = None) -> None:
        if mount is not None:
            self.mount = mount
        else:
            self.mount = ['spec']  # We model the cr.spec as the input
        self.root_schema = extract_schema([],
                                          crd['spec']['versions'][-1]['schema']['openAPIV3Schema'])

        # Load all example documents
        self.example_dir = example_dir
        example_docs = []
        for example_filepath in glob.glob(example_dir + '*.yaml'):
            with open(example_filepath, 'r') as example_file:
                docs = yaml.load_all(example_file, Loader=yaml.FullLoader)
                for doc in docs:
                    example_docs.append(doc)

        for example_doc in example_docs:
            self.root_schema.load_examples(example_doc)

        self.used_fields = used_fields
        self.num_workers = num_workers
        self.num_cases = num_cases  # number of test cases to run at a time
        self.seed_input = None
        self.normal_test_plan_partitioned = None
        self.overspecified_test_plan_partitioned = None
        self.copiedover_test_plan_partitioned = None

        self.thread_vars = threading.local()

        self.metadata = {
            'normal_schemas': 0,
            'pruned_by_overspecified': 0,
            'pruned_by_copied': 0,
            'num_normal_testcases': 0,
            'num_overspecified_testcases': 0,
            'num_copiedover_testcases': 0,
        }  # to fill in the generate_test_plan function

    def initialize(self, initial_value: dict):
        initial_value['metadata']['name'] = 'test-cluster'
        self.initial_value = initial_value
        self.seed_input = attach_schema_to_value(initial_value, self.root_schema)

    def set_worker_id(self, id: int):
        '''Claim this thread's id, so that we can split the test plan among threads'''

        if hasattr(self.thread_vars, 'id'):
            # Avoid initialize twice
            return

        # Thread local variables
        self.thread_vars.id = id
        # so that we can run the test case itself right after the setup
        self.thread_vars.normal_test_plan = TestPlan(self.root_schema.to_tree())
        self.thread_vars.overspecified_test_plan = TestPlan(self.root_schema.to_tree())
        self.thread_vars.copiedover_test_plan = TestPlan(self.root_schema.to_tree())

        for key, value in dict(self.normal_test_plan_partitioned[id]).items():
            path = json.loads(key)
            self.thread_vars.normal_test_plan.add_testcases_by_path(value, path)

        for key, value in dict(self.overspecified_test_plan_partitioned[id]).items():
            path = json.loads(key)
            self.thread_vars.overspecified_test_plan.add_testcases_by_path(value, path)

        for key, value in dict(self.copiedover_test_plan_partitioned[id]).items():
            path = json.loads(key)
            self.thread_vars.copiedover_test_plan.add_testcases_by_path(value, path)

    def set_mode(self, mode: str):
        if mode == 'NORMAL':
            self.thread_vars.test_plan: TestPlan = self.thread_vars.normal_test_plan
        elif mode == 'OVERSPECIFIED':
            self.thread_vars.test_plan: TestPlan = self.thread_vars.overspecified_test_plan
        elif mode == 'COPIED_OVER':
            self.thread_vars.test_plan: TestPlan = self.thread_vars.copiedover_test_plan
        else:
            raise ValueError(mode)

    def is_empty(self):
        '''if test plan is empty'''
        return len(self.thread_vars.test_plan) == 0

    def get_seed_input(self) -> dict:
        '''Get the raw value of the seed input'''
        return self.seed_input.raw_value()

    def get_schema_by_path(self, path: list) -> BaseSchema:
        return reduce(operator.getitem, path, self.root_schema)

    def get_all_schemas(self):
        '''Get all the schemas as a list'''
        return self.root_schema.get_all_schemas()

    def get_root_schema(self) -> BaseSchema:
        return self.root_schema

    def get_discarded_tests(self) -> dict:
        return self.discarded_tests

    def generate_test_plan(self, delta_from: str = None) -> dict:
        '''Generate test plan based on CRD'''
        logger = get_thread_logger(with_prefix=False)

        existing_testcases = {}
        if delta_from is not None:
            with open(delta_from, 'r') as delta_from_file:
                existing_testcases = json.load(delta_from_file)['normal_testcases']

        tree: TreeNode = self.root_schema.to_tree()
        for field in self.used_fields:
            field = field[1:]
            node = tree.get_node_by_path(field)
            if node is None:
                logger.warning(f'Field {field} not found in CRD')
                continue

            node.set_used()

        def func(overspecified_fields: list, unused_fields: list, node: TreeNode) -> bool:
            if len(node.children) == 0:
                return False

            if not node.used:
                return False

            used_child = []
            for child in node.children.values():
                if child.used:
                    used_child.append(child)
                else:
                    unused_fields.append(child.path)

            if len(used_child) == 0:
                overspecified_fields.append(node.path)
                return False
            elif len(used_child) == len(node.children):
                return True
            else:
                return True

        overspecified_fields = []
        unused_fields = []
        tree.traverse_func(partial(func, overspecified_fields, unused_fields))
        for field in overspecified_fields:
            logger.info('Overspecified field: %s', field)
        for field in unused_fields:
            logger.info('Unused field: %s', field)

        planned_normal_testcases = {}
        normal_testcases = {}
        overspecified_testcases = {}
        copiedover_testcases = {}
        num_normal_testcases = 0
        num_overspecified_testcases = 0
        num_copiedover_testcases = 0

        mounted_schema = self.get_schema_by_path(self.mount)
        normal_schemas, pruned_by_overspecified, pruned_by_copied = mounted_schema.get_all_schemas()
        for schema in normal_schemas:
            path = json.dumps(schema.path).replace('\"ITEM\"',
                                                   '0').replace('additional_properties', 'ACTOKEY')
            testcases = schema.test_cases()
            planned_normal_testcases[path] = testcases
            if path in existing_testcases:
                continue
            normal_testcases[path] = testcases
            num_normal_testcases += len(testcases)

        for schema in pruned_by_overspecified:
            testcases = schema.test_cases()
            path = json.dumps(schema.path).replace('\"ITEM\"',
                                                   '0').replace('additional_properties',
                                                                random_string(5))
            overspecified_testcases[path] = testcases
            num_overspecified_testcases += len(testcases)

        for schema in pruned_by_copied:
            testcases = schema.test_cases()
            path = json.dumps(schema.path).replace('\"ITEM\"',
                                                   '0').replace('additional_properties',
                                                                random_string(5))
            copiedover_testcases[path] = testcases
            num_copiedover_testcases += len(testcases)

        logger.info('Parsed [%d] fields from normal schema' % len(normal_schemas))
        logger.info('Parsed [%d] fields from over-specified schema' % len(pruned_by_overspecified))
        logger.info('Parsed [%d] fields from copied-over schema' % len(pruned_by_copied))

        logger.info('Generated [%d] test cases for normal schemas', num_normal_testcases)
        logger.info('Generated [%d] test cases for overspecified schemas',
                    num_overspecified_testcases)
        logger.info('Generated [%d] test cases for copiedover schemas', num_copiedover_testcases)

        self.metadata['normal_schemas'] = len(normal_schemas)
        self.metadata['pruned_by_overspecified'] = len(pruned_by_overspecified)
        self.metadata['pruned_by_copied'] = len(pruned_by_copied)
        self.metadata['num_normal_testcases'] = num_normal_testcases
        self.metadata['num_overspecified_testcases'] = num_overspecified_testcases
        self.metadata['num_copiedover_testcases'] = num_copiedover_testcases

        normal_test_plan_items = list(normal_testcases.items())
        overspecified_test_plan_items = list(overspecified_testcases.items())
        copiedover_test_plan_items = list(copiedover_testcases.items())
        random.shuffle(normal_test_plan_items)  # randomize to reduce skewness among workers
        random.shuffle(overspecified_test_plan_items)
        random.shuffle(copiedover_test_plan_items)

        # Initialize the three test plans, and assign test cases to them according to the number of
        # workers
        self.normal_test_plan_partitioned = []
        self.overspecified_test_plan_partitioned = []
        self.copiedover_test_plan_partitioned = []

        for i in range(self.num_workers):
            self.normal_test_plan_partitioned.append([])
            self.overspecified_test_plan_partitioned.append([])
            self.copiedover_test_plan_partitioned.append([])

        for i in range(0, len(normal_test_plan_items)):
            self.normal_test_plan_partitioned[i % self.num_workers].append(
                normal_test_plan_items[i])

        for i in range(0, len(overspecified_test_plan_items)):
            self.overspecified_test_plan_partitioned[i % self.num_workers].append(
                overspecified_test_plan_items[i])

        for i in range(0, len(copiedover_test_plan_items)):
            self.copiedover_test_plan_partitioned[i % self.num_workers].append(
                copiedover_test_plan_items[i])

        # appending empty lists to avoid no test cases distributed to certain work nodes
        assert (self.num_workers == len(self.normal_test_plan_partitioned))
        assert (self.num_workers == len(self.overspecified_test_plan_partitioned))
        assert (self.num_workers == len(self.copiedover_test_plan_partitioned))
        assert (sum(
            len(p) for p in self.normal_test_plan_partitioned) == len(normal_test_plan_items))
        assert (sum(len(p) for p in self.overspecified_test_plan_partitioned) == len(
            overspecified_test_plan_items))
        assert (sum(
            len(p)
            for p in self.copiedover_test_plan_partitioned) == len(copiedover_test_plan_items))

        return {
            'delta_from': delta_from,
            'existing_testcases': existing_testcases,
            'normal_testcases': normal_testcases,
            'overspecified_testcases': overspecified_testcases,
            'copiedover_testcases': copiedover_testcases,
        }

    def next_test(self) -> List[Tuple[TreeNode, TestCase]]:
        '''Selects next test case to run from the test plan
        
        Randomly select a test field, and fetch the tail of the test case list
        Check if the precondition of the test case satisfies, if not, try to
        set up for the test case this time
        
        Returns:
            Tuple of (new value, if this is a setup)
        '''
        logger = get_thread_logger(with_prefix=True)

        logger.info('Progress [%d] cases left' % len(self.thread_vars.test_plan))

        ret = []

        # TODO: multi-testcase
        selected_fields: List[TreeNode] = self.thread_vars.test_plan.select_fields(
            num_cases=self.num_cases)

        for selected_field in selected_fields:
            logger.info('Selected field [%s]', selected_field.get_path())
            ret.append(tuple([selected_field, selected_field.get_next_testcase()]))

        return ret

    def get_input_delta(self):
        '''Compare the current input with the previous input
        
        Returns
            a delta object in tree view
        '''
        cr_diff = DeepDiff(self.thread_vars.previous_input.raw_value(),
                           self.thread_vars.current_input.raw_value(),
                           ignore_order=True,
                           report_repetition=True,
                           view='tree')
        return cr_diff

    def discard_test_case(self):
        '''Discard the test case that was selected'''
        logger = get_thread_logger(with_prefix=True)

        discarded_case = self.thread_vars.test_plan[self.thread_vars.curr_field].pop()

        # Log it to discarded_tests
        if self.thread_vars.curr_field in self.discarded_tests:
            self.discarded_tests[self.thread_vars.curr_field].append(discarded_case)
        else:
            self.discarded_tests[self.thread_vars.curr_field] = [discarded_case]
        logger.info('Setup failed due to invalid, discard this testcase %s' % discarded_case)

        if len(self.thread_vars.test_plan[self.thread_vars.curr_field]) == 0:
            del self.thread_vars.test_plan[self.thread_vars.curr_field]
        self.thread_vars.curr_field = None

    def apply_custom_field(self, custom_field: CustomField):
        '''Applies custom field to the input model
        
        Relies on the __setitem__ and __getitem__ methods of schema class
        '''
        path = custom_field.path
        if len(path) == 0:
            self.root_schema = custom_field.custom_schema(self.root_schema,
                                                          custom_field.used_fields)

        # fetch the parent schema
        curr = self.root_schema
        for idx in path[:-1]:
            curr = curr[idx]

        # construct new schema
        custom_schema = custom_field.custom_schema(curr[path[-1]], custom_field.used_fields)

        # replace old schema with the new one
        curr[path[-1]] = custom_schema

    def apply_candidates(self, candidates: dict, path: list):
        '''Apply candidates file onto schema'''
        # TODO
        candidates_list = self.candidates_dict_to_list(candidates, path)

    def apply_default_value(self, default_value_result: dict):
        '''Takes default value result from static analysis and apply to schema
        
        Args:
            default_value_result: default_value_map in static analysis result
        '''
        for key, value in default_value_result.items():
            path = json.loads(key)[1:]  # get rid of leading "root"
            self.get_schema_by_path(path).set_default(value)

    def candidates_dict_to_list(self, candidates: dict, path: list) -> list:
        if 'candidates' in candidates:
            return [(path, candidates['candidates'])]
        else:
            ret = []
            for key, value in candidates.items():
                ret.extend(self.candidates_dict_to_list(value, path + [key]))
            return ret
