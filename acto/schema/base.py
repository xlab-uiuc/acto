import random
from abc import abstractmethod
from typing import List, Tuple

from jsonschema import validate

from acto.utils.thread_logger import get_thread_logger


class TreeNode():

    def __init__(self, path: list) -> None:
        self.path = list(path)
        self.parent: TreeNode = None
        self.children = {}

    def add_child(self, key: str, child: 'TreeNode'):
        self.children[key] = child
        child.set_parent(self)
        child.path = self.path + [key]

    def set_parent(self, parent: 'TreeNode'):
        self.parent = parent

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

    def deepcopy(self, path: list):
        ret = TreeNode(path)
        for key, child in self.children.items():
            ret.add_child(key, child.deepcopy(path + [key]))

        ret.testcases = list(self.testcases)

        return ret


class SchemaInterface():
    @abstractmethod
    def get_all_schemas(self) -> Tuple[List['BaseSchema'], List['BaseSchema'], List['BaseSchema']]:
        '''Returns a tuple of normal schemas, schemas pruned by over-specified, schemas pruned by 
        copied-over'''
        #FIXME: this method needs to be redefined. Its return type is a legacy from previous abandoned design
        raise NotImplementedError

    @abstractmethod
    def get_normal_semantic_schemas(self) -> Tuple[List['BaseSchema'], List['BaseSchema']]:
        '''Returns a tuple of normal schemas, semantic schemas'''
        raise NotImplementedError

    @abstractmethod
    def to_tree(self) -> TreeNode:
        '''Returns tree structure, used for input generation'''
        raise NotImplementedError

    @abstractmethod
    def load_examples(self, example):
        '''Load example into schema and subschemas'''
        raise NotImplementedError

    @abstractmethod
    def set_default(self, instance):
        raise NotImplementedError

    @abstractmethod
    def empty_value(self):
        raise NotImplementedError


class BaseSchema(SchemaInterface):
    '''Base class for schemas
    
    Handles some keywords used for any types
    '''

    def __init__(self, path: list, schema: dict) -> None:
        self.path = path
        self.raw_schema = schema
        self.default = None if 'default' not in schema else schema['default']
        self.enum = None if 'enum' not in schema else schema['enum']
        self.examples = []

        self.copied_over = False
        self.over_specified = False
        self.problematic = False
        self.patch = False
        self.mapped = False
        self.used_fields = []

    def get_path(self) -> list:
        return self.path

    def validate(self, instance) -> bool:
        try:
            validate(instance, self.raw_schema)
            return True
        except:
            return False