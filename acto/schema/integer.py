from typing import List, Tuple

from .base import BaseSchema, TreeNode
from .number import NumberSchema


class IntegerSchema(NumberSchema):
    '''Special case of NumberSchema'''

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)
        if self.default == None:
            self.default = 0

    def get_all_schemas(self) -> Tuple[list, list, list]:
        if self.problematic:
            return [], [], []
        return [self], [], []

    def get_normal_semantic_schemas(self) -> Tuple[List['BaseSchema'], List['BaseSchema']]:
        if self.problematic:
            return [], []
        return [self], []

    def to_tree(self) -> TreeNode:
        return TreeNode(self.path)

    def load_examples(self, example: int):
        self.examples.append(example)

    def set_default(self, instance):
        self.default = int(instance)

    def empty_value(self):
        return 0

    def __str__(self) -> str:
        return 'Integer'