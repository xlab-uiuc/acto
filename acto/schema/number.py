import random
from typing import List, Optional, Tuple

from .base import BaseSchema, TreeNode


class NumberSchema(BaseSchema):
    """Representation of a number node

    It handles
        - minimum
        - maximum
        - exclusiveMinimum
        - exclusiveMaximum
        - multipleOf
    """

    default_minimum = 0
    default_maximum = 5

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)
        self.minimum = (
            self.default_minimum
            if "minimum" not in schema
            else schema["minimum"]
        )
        self.maximum = (
            self.default_maximum
            if "maximum" not in schema
            else schema["maximum"]
        )
        self.exclusive_minimum = (
            None
            if "exclusiveMinimum" not in schema
            else schema["exclusiveMinimum"]
        )
        self.exclusive_maximum = (
            None
            if "exclusiveMaximum" not in schema
            else schema["exclusiveMaximum"]
        )
        self.multiple_of = (
            None if "multipleOf" not in schema else schema["multipleOf"]
        )

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

    def load_examples(self, example: Optional[float]):
        if isinstance(example, float):
            self.examples.add(example)
        else:
            raise TypeError(
                f"Expected float, got {type(example)} for property {self.path}"
            )

    def set_default(self, instance):
        self.default = float(instance)

    def empty_value(self):
        return 0

    def gen(self, exclude_value=None, minimum=False, **kwargs) -> float:
        # TODO: Use exclusive_minimum, exclusive_maximum, multiple_of
        if self.enum is not None:
            if exclude_value is not None:
                return random.choice(
                    [x for x in self.enum if x != exclude_value]
                )
            else:
                return random.choice(self.enum)
        return random.uniform(self.minimum, self.maximum)

    def __str__(self) -> str:
        return "Number"
