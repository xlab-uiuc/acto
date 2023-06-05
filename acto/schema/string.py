from typing import List, Tuple

from .base import BaseSchema, TreeNode


class StringSchema(BaseSchema):
    '''Representation of a string node
    
    It handles
        - minLength
        - maxLength
        - pattern
    '''
    default_max_length = 10

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)
        self.min_length = None if 'minLength' not in schema else schema['minLength']
        self.max_length = self.default_max_length if 'maxLength' not in schema else schema[
            'maxLength']
        self.pattern = None if 'pattern' not in schema else schema['pattern']

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

    def load_examples(self, example: str):
        self.examples.append(example)

    def set_default(self, instance):
        self.default = str(instance)

    def empty_value(self):
        return ""

    def __str__(self) -> str:
        return 'String'