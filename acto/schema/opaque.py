from typing import List, Tuple

from .base import BaseSchema, TreeNode


class OpaqueSchema(BaseSchema):
    """Opaque schema to handle the fields that do not have a schema"""

    def get_all_schemas(self) -> Tuple[list, list, list]:
        return [], [], []

    def get_normal_semantic_schemas(
        self,
    ) -> Tuple[List["BaseSchema"], List["BaseSchema"]]:
        return [], []

    def to_tree(self) -> TreeNode:
        return TreeNode(self.path)

    def load_examples(self, example):
        pass

    def set_default(self, instance):
        self.default = instance

    def empty_value(self):
        return None

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        return None

    def __str__(self) -> str:
        return "any"
