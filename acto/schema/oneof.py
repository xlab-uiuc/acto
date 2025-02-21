import random
from copy import deepcopy
from typing import List, Tuple

from .array import ArraySchema
from .base import BaseSchema, TreeNode
from .object import ObjectSchema


class OneOfSchema(BaseSchema):
    """Representing a schema with AnyOf keyword in it"""

    def __init__(self, path: list, schema: dict) -> None:
        # This is to fix the circular import
        # pylint: disable=import-outside-toplevel, cyclic-import
        from .schema import extract_schema

        super().__init__(path, schema)
        self.possibilities = []
        for index, v in enumerate(schema["oneOf"]):
            base_schema = deepcopy(schema)
            del base_schema["oneOf"]
            self.__recursive_update(base_schema, v)
            self.possibilities.append(extract_schema(self.path, base_schema))

    def __recursive_update(self, left: dict, right: dict):
        """Recursively update left dict with right dict"""
        for key, value in right.items():
            if (
                key in left
                and isinstance(left[key], dict)
                and isinstance(value, dict)
            ):
                self.__recursive_update(left[key], value)
            else:
                left[key] = value

    def get_possibilities(self):
        """Return all possibilities of the anyOf schema"""
        return self.possibilities

    def get_all_schemas(self) -> Tuple[list, list, list]:
        if self.problematic:
            return [], [], []
        return [self], [], []

    def get_normal_semantic_schemas(
        self,
    ) -> Tuple[List["BaseSchema"], List["BaseSchema"]]:
        normal_schemas: list[BaseSchema] = [self]
        semantic_schemas: list[BaseSchema] = []

        for possibility in self.possibilities:
            possibility_tuple = possibility.get_normal_semantic_schemas()
            normal_schemas.extend(possibility_tuple[0])
            semantic_schemas.extend(possibility_tuple[1])

        return normal_schemas, semantic_schemas

    def empty_value(self):
        return None

    def to_tree(self) -> TreeNode:
        return TreeNode(self.path)

    def load_examples(self, example: list):
        for possibility in self.possibilities:
            if possibility.validate(example):
                possibility.load_examples(example)

    def set_default(self, instance):
        self.default = instance

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        schema = random.choice(self.possibilities)
        return schema.gen(exclude_value=exclude_value, minimum=minimum)

    def __str__(self) -> str:
        ret = "["
        for i in self.possibilities:
            ret += str(i)
            ret += ", "
        ret += "]"
        return ret

    def __getitem__(self, key):
        if isinstance(key, int):
            for i in self.possibilities:
                if isinstance(i, ArraySchema):
                    return i[key]
            raise RuntimeError("No array schema found in oneOf")
        if isinstance(key, str):
            for i in self.possibilities:
                if isinstance(i, ObjectSchema):
                    return i[key]
            raise RuntimeError("No object schema found in oneOf")
        raise TypeError("Key must be either int or str")

    def __setitem__(self, key, value):
        if isinstance(key, int):
            for i in self.possibilities:
                if isinstance(i, ArraySchema):
                    i[key] = value
                    return
            raise RuntimeError("No array schema found in oneOf")
        if isinstance(key, str):
            for i in self.possibilities:
                if isinstance(i, ObjectSchema):
                    i[key] = value
                    return
            raise RuntimeError("No object schema found in oneOf")
        raise TypeError("Key must be either int or str")
