import logging
import random
from typing import List, Optional, Tuple

import exrex

from acto.common import random_string

from .base import BaseSchema, TreeNode


class StringSchema(BaseSchema):
    """Representation of a string node

    It handles
        - minLength
        - maxLength
        - pattern
    """

    default_max_length = 10

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)
        self.min_length = (
            None if "minLength" not in schema else schema["minLength"]
        )
        self.max_length = (
            self.default_max_length
            if "maxLength" not in schema
            else schema["maxLength"]
        )
        self.pattern = None if "pattern" not in schema else schema["pattern"]

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

    def load_examples(self, example: str):
        logging.debug(f"Loading example {example} into {self}")
        self.examples.append(example)

    def set_default(self, instance):
        self.default = str(instance)

    def empty_value(self):
        return ""

    def gen(
        self,
        exclude_value: Optional[str] = None,
        minimum: bool = False,
        **kwargs,
    ):
        # TODO: Use minLength: the exrex does not support minLength
        if self.enum is not None:
            if exclude_value is not None:
                return random.choice(
                    [x for x in self.enum if x != exclude_value]
                )
            else:
                return random.choice(self.enum)
        if self.examples:
            if exclude_value is not None:
                example_without_exclude = [
                    x for x in self.examples if x != exclude_value
                ]
                if len(example_without_exclude) > 0:
                    return random.choice(example_without_exclude)
        if self.pattern is not None:
            # Since it's random, we don't need to exclude the value
            return exrex.getone(self.pattern, self.max_length)
        if minimum:
            return random_string(self.min_length)  # type: ignore
        return "ACTOSTRING"

    def __str__(self) -> str:
        return "String"
