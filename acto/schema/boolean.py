import random
from typing import List, Tuple

from .base import BaseSchema, TreeNode


class BooleanSchema(BaseSchema):
    """Representation of a boolean node"""

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)
        if self.default is None:
            self.default = False

    def get_all_schemas(self) -> Tuple[list, list, list]:
        if self.problematic:
            return [], [], []
        return [self], [], []

    def get_normal_semantic_schemas(
        self,
    ) -> Tuple[List["BaseSchema"], List["BaseSchema"]]:
        return [self], []

    def to_tree(self) -> TreeNode:
        return TreeNode(self.path)

    def load_examples(self, example: bool):
        pass

    def set_default(self, instance):
        if isinstance(instance, bool):
            self.default = instance
        elif isinstance(instance, str):
            self.default = instance.lower() in ["true", "True"]

    def empty_value(self):
        return False

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        """Generate a random boolean value"""
        if exclude_value is not None:
            return not exclude_value
        else:
            return random.choice([True, False])

    def __str__(self) -> str:
        return "boolean"
