from abc import abstractmethod
from typing import Any, List, Tuple

from typing_extensions import Self

from .base import BaseSchema
from .schema import extract_schema


class UnderSpecifiedSchema(BaseSchema):
    """An under-specified schema with a more complete underlying schema"""

    def __init__(self, path: list, schema: dict, underlying_raw_schema) -> None:
        super().__init__(path, schema)
        self._original_schema = extract_schema(path, schema)
        self._underlying_schema = extract_schema([], underlying_raw_schema)

    @abstractmethod
    def encode(self, value: dict) -> Any:
        """Convert the value generated using the underlying schema to the original schema"""

    @abstractmethod
    def decode(self, value: Any) -> dict:
        """Encode the value generated using the original schema to the underlying schema"""

    @classmethod
    @abstractmethod
    def from_original_schema(cls, original_schema: BaseSchema) -> Self:
        """Create an under-specified schema from an original schema"""

    @property
    def original_schema(self):
        """Accessor to the original schema"""
        return self._original_schema

    @property
    def underlying_schema(self):
        """Accessor to the underlying schema"""
        return self._underlying_schema

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs) -> dict:
        return self.encode(
            self._underlying_schema.gen(
                exclude_value=exclude_value, minimum=minimum, **kwargs
            )
        )

    def empty_value(self):
        return self._original_schema.empty_value()

    def to_tree(self):
        return self._original_schema.to_tree()

    def load_examples(self, example: Any):
        self._original_schema.load_examples(example)

    def set_default(self, instance):
        self._original_schema.set_default(instance)

    def get_all_schemas(
        self,
    ) -> Tuple[List[BaseSchema], List[BaseSchema], List[BaseSchema]]:
        return self._original_schema.get_all_schemas()

    def get_normal_semantic_schemas(
        self,
    ) -> Tuple[List[BaseSchema], List[BaseSchema]]:
        return self._original_schema.get_normal_semantic_schemas()
