import random
import json
from typing import List

from test_case import TestCase
from thread_logger import get_thread_logger

class TreeNode():

    def __init__(self, path: list) -> None:
        self.path = list(path)

        self.parent: TreeNode = None
        self.children = {}
        self.testcases = []

        self.node_disabled = False
        self.subtree_disabled = False

        # for Overspecified fields analysis
        self.used = False

    def add_child(self, key: str, child: 'TreeNode'):
        self.children[key] = child
        child.set_parent(self)
        child.path = self.path + [key]

    def set_parent(self, parent: 'TreeNode'):
        self.parent = parent

    def set_used(self):
        self.used = True
        parent = self.parent

        while parent != None:
            parent.used = True
            parent = parent.parent

        return

    def add_testcases(self, testcases: list):
        self.testcases.extend(testcases)

    def add_testcases_by_path(self, testcases: list, path: list):
        if len(path) == 0:
            self.testcases.extend(testcases)
        else:
            key = path.pop(0)
            if key not in self.children:
                if 'ITEM' in self.children and isinstance(key, int):
                    concrete_node = self.children['ITEM'].deepcopy(self.path+[key])
                    concrete_node.path[-1] = key
                    concrete_node.add_testcases_by_path(testcases, path)
                    self.children[key] = concrete_node
                elif 'additional_properties' in self.children and isinstance(key, str):
                    concrete_node = self.children['additional_properties'].deepcopy(self.path+[key])
                    concrete_node.path[-1] = key
                    concrete_node.add_testcases_by_path(testcases, path)
                    self.children[key] = concrete_node
                else:
                    raise KeyError('key: %s, path %s' % (key, path))
            else:
                self.children[key].add_testcases_by_path(testcases, path)

    def enable_subtree(self):
        self.node_disabled = False
        self.subtree_disabled = False

        for child in self.children.values():
            child.enable_subtree()

    def disable_node(self):
        '''This node will not be selected at this step'''
        self.node_disabled = True

    def disable_subtree(self):
        '''This node and its children will not be selected at this step'''
        self.subtree_disabled = True

    def disable_ancestors(self):
        parent = self.parent

        while parent != None:
            parent.disable_node()
            parent = parent.parent

        return

    def discard_testcase(self, discarded_testcases: dict):
        '''Discard the current testcase, store the discarded testcase into the parameter
        
        Args:
            discarded_testcases: dict to store the discarded testcase
        '''
        encoded_path = json.dumps(self.path)
        if len(self.testcases) > 0:
            discarded_testcase = self.testcases.pop()
        else:
            discarded_testcase = {}
        if encoded_path in discarded_testcases:
            discarded_testcases[encoded_path].append(discarded_testcase)
        else:
            discarded_testcases[encoded_path] = [discarded_testcase]

    def get_node_by_path(self, path: list) -> 'TreeNode':
        logger = get_thread_logger(with_prefix=True)

        if len(path) == 0:
            return self
        
        key = path.pop(0)
        if key in self:
            return self[key].get_node_by_path(path)
        else:
            logger.error('%s not in children', key)
            logger.error('%s', self.children)
            return None

    def get_children(self) -> dict:
        return self.children

    def get_testcases(self) -> list:
        return self.testcases

    def get_next_testcase(self) -> TestCase:
        return self.testcases[-1]

    def get_path(self) -> list:
        return self.path

    def traverse_func(self, func: callable):
        if func(self):
            for child in self.children.values():
                child.traverse_func(func)

    def __getitem__(self, key):
        if key not in self.children:
            if 'ITEM' in self.children and key == 'INDEX':
                return self.children['ITEM']
            if isinstance(key, int) and 'ITEM' in self.children:
                return self.children['ITEM']
            elif 'additional_properties' in self.children and isinstance(key, str):
                return self.children['additional_properties']
            else:
                raise KeyError('key: %s' % key)
        else:
            return self.children[key]

    def __contains__(self, key) -> bool:
        if key not in self.children:
            if 'ITEM' in self.children and key == 'INDEX':
                return True
            if 'ITEM' in self.children and isinstance(key, int):
                return True
            elif 'additional_properties' in self.children and isinstance(key, str):
                return True
            else:
                return False
        else:
            return True

    def __str__(self) -> str:
        return str(self.path)

    def eligible_fields(self) -> List['TreeNode']:
        '''Returns all eligible fields of this subtree
        
        a field is eligible if it is not disabled and has at least one testcase
        '''
        if self.subtree_disabled:
            return []

        ret = []
        if not self.node_disabled and len(self.testcases) > 0:
            ret.append(self)

        for key, child in self.children.items():
            if key != 'ITEM' and key != 'additional_properties':
                ret.extend(child.eligible_fields())

        return ret

    def deepcopy(self, path: list):
        ret = TreeNode(path)
        for key, child in self.children.items():
            ret.add_child(key, child.deepcopy(path+[key]))

        ret.testcases = list(self.testcases)

        return ret


class TestPlan():

    def __init__(self, root: TreeNode) -> None:
        self.root = root

    def select_fields(self, num_cases: int = 1) -> List[TreeNode]:
        logger = get_thread_logger(with_prefix=True)
        ret = []

        for i in range(num_cases):
            eligible_fields = self.root.eligible_fields()
            if len(eligible_fields) == 0:
                break

            field = random.choice(eligible_fields)
            field.disable_subtree()
            field.disable_ancestors()
            ret.append(field)
            logger.info('TestPlan: selected %s', field.get_path())

        self.root.enable_subtree()

        return ret

    def add_testcases_by_path(self, testcases: list, path: list):
        node = self.root.add_testcases_by_path(testcases, path)

    def __len__(self):
        return sum([len(i.get_testcases()) for i in self.root.eligible_fields()])
