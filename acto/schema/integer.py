import random
from typing import Any, List, Tuple

from .base import BaseSchema, TreeNode
from .number import NumberSchema


class IntegerSchema(NumberSchema):
    """Special case of NumberSchema"""

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)
        if self.default is None:
            self.default = 0

    def get_all_schemas(self) -> Tuple[list, list, list]:
        if self.problematic:
            return [], [], []
        return [self], [], []

    def get_normal_semantic_schemas(
        self,
    ) -> Tuple[List["BaseSchema"], List["BaseSchema"]]:
        if self.problematic:
            return [], []
        return [self], []

    def to_tree(self) -> TreeNode:
        return TreeNode(self.path)

    def load_examples(self, example: Any):
        if isinstance(example, int):
            self.examples.append(example)

    def set_default(self, instance):
        self.default = int(instance)

    def empty_value(self):
        return 0

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs) -> int:
        # TODO: Use exclusive_minimum, exclusive_maximum
        if self.enum is not None:
            if exclude_value is not None:
                return random.choice(
                    [x for x in self.enum if x != exclude_value]
                )
            else:
                return random.choice(self.enum)
        elif self.multiple_of is not None:
            return random.randrange(
                self.minimum, self.maximum + 1, self.multiple_of
            )
        else:
            if exclude_value is not None:
                return random.choice(
                    [
                        x
                        for x in range(self.minimum + 1, self.maximum + 1)
                        if x != exclude_value
                    ]
                )
            else:
                return random.randrange(self.minimum + 1, self.maximum + 1)

    def __str__(self) -> str:
        return "Integer"
