from copy import deepcopy
from typing import List, Tuple

from .base import BaseSchema, TreeNode
from .schema import extract_schema


class AnyOfSchema(BaseSchema):
    '''Representing a schema with AnyOf keyword in it
    '''

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)
        self.possibilities: List[BaseSchema] = []
        for index, v in enumerate(schema['anyOf']):
            base_schema = deepcopy(schema)
            del base_schema['anyOf']
            base_schema.update(v)
            self.possibilities.append(extract_schema(self.path + ['%s' % str(index)], base_schema))

    def get_possibilities(self):
        return self.possibilities

    def get_all_schemas(self) -> Tuple[list, list, list]:
        if self.problematic:
            return [], [], []
        return [self], [], []
    
    def get_normal_semantic_schemas(self) -> Tuple[List['BaseSchema'], List['BaseSchema']]:
        normal_schemas = [self]
        semantic_schemas = []

        for possibility in self.possibilities:
            possibility_tuple = possibility.get_normal_semantic_schemas()
            normal_schemas.extend(possibility_tuple[0])
            semantic_schemas.extend(possibility_tuple[1])

        return normal_schemas, semantic_schemas

    def empty_value(self):
        return None

    def to_tree(self) -> TreeNode:
        return TreeNode(self.path)

    def load_examples(self, example: list):
        for possibility in self.possibilities:
            if possibility.validate(example):
                possibility.load_examples(example)

    def set_default(self, instance):
        self.default = instance

    def __str__(self) -> str:
        ret = '['
        for i in self.possibilities:
            ret += str(i)
            ret += ', '
        ret += ']'
        return ret
