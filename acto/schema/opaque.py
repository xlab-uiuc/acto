from typing import Any, List, Optional, Tuple

from acto.common import HashableDict, HashableList
from acto.utils.thread_logger import get_thread_logger

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

    def load_examples(self, example: Optional[Any]):
        if example is None:
            return
        logger = get_thread_logger(with_prefix=True)
        logger.debug("Loading example %s into %s", example, self.path)
        if isinstance(example, dict):
            self.examples.add(HashableDict(example))
        elif isinstance(example, list):
            self.examples.add(HashableList(example))
        else:
            self.examples.add(example)

    def set_default(self, instance):
        self.default = instance

    def empty_value(self):
        return None

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        return None

    def __str__(self) -> str:
        return "any"
