from typing import List, Tuple

from .base import BaseSchema, TreeNode


class OpaqueSchema(BaseSchema):
    '''Opaque schema to handle the fields that do not have a schema'''

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)

    def get_all_schemas(self) -> Tuple[list, list, list]:
        return [], [], []
    
    def get_normal_semantic_schemas(self) -> Tuple[List['BaseSchema'], List['BaseSchema']]:
        return [], []

    def to_tree(self) -> TreeNode:
        return TreeNode(self.path)

    def load_examples(self, example):
        pass

    def empty_value(self):
        return None

    def __str__(self) -> str:
        return 'any'
