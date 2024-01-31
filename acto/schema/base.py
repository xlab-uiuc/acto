from abc import abstractmethod
from typing import Any, Callable, List, Optional, Tuple

import jsonschema
import jsonschema.exceptions

from acto.utils.thread_logger import get_thread_logger


class TreeNode:
    """Tree node for schema tree"""

    def __init__(self, path: list) -> None:
        self.path = list(path)
        self.parent: Optional[TreeNode] = None
        self.children: dict[str, "TreeNode"] = {}

    def add_child(self, key: str, child: "TreeNode"):
        """Add a child to the node"""
        self.children[key] = child
        child.set_parent(self)
        child.path = self.path + [key]

    def set_parent(self, parent: "TreeNode"):
        """Set parent of the node"""
        self.parent = parent

    def get_node_by_path(self, path: list) -> Optional["TreeNode"]:
        """Get node by path"""
        logger = get_thread_logger(with_prefix=True)

        if len(path) == 0:
            return self

        key = path.pop(0)
        if key in self:
            return self[key].get_node_by_path(path)
        else:
            logger.error("%s not in children", key)
            logger.error("%s", self.children)
            return None

    def get_children(self) -> dict:
        """Get children of the node"""
        return self.children

    def get_path(self) -> list:
        """Get path of the node"""
        return self.path

    def traverse_func(self, func: Callable):
        """Traverse the tree and apply func to each node"""
        if func(self):
            for child in self.children.values():
                child.traverse_func(func)

    def __getitem__(self, key):
        if key not in self.children:
            if "ITEM" in self.children and key == "INDEX":
                return self.children["ITEM"]
            if isinstance(key, int) and "ITEM" in self.children:
                return self.children["ITEM"]
            elif "additional_properties" in self.children and isinstance(
                key, str
            ):
                return self.children["additional_properties"]
            else:
                raise KeyError(f"key: {key}")
        else:
            return self.children[key]

    def __contains__(self, key) -> bool:
        if key not in self.children:
            if "ITEM" in self.children and key == "INDEX":
                return True
            if "ITEM" in self.children and isinstance(key, int):
                return True
            elif "additional_properties" in self.children and isinstance(
                key, str
            ):
                return True
            else:
                return False
        else:
            return True

    def __str__(self) -> str:
        return str(self.path)

    def deepcopy(self, path: list):
        """Deep copy the node and its children"""
        ret = TreeNode(path)
        for key, child in self.children.items():
            ret.add_child(key, child.deepcopy(path + [key]))

        return ret


class SchemaInterface:
    """Interface for schemas"""

    @abstractmethod
    def get_all_schemas(
        self,
    ) -> Tuple[List["BaseSchema"], List["BaseSchema"], List["BaseSchema"]]:
        """Returns a tuple of normal schemas, schemas pruned by over-specified, schemas pruned by
        copied-over"""
        # FIXME: this method needs to be redefined.
        # Its return type is a legacy from previous abandoned design
        raise NotImplementedError

    @abstractmethod
    def get_normal_semantic_schemas(
        self,
    ) -> Tuple[List["BaseSchema"], List["BaseSchema"]]:
        """Returns a tuple of normal schemas, semantic schemas"""
        raise NotImplementedError

    @abstractmethod
    def to_tree(self) -> TreeNode:
        """Returns tree structure, used for input generation"""
        raise NotImplementedError

    @abstractmethod
    def load_examples(self, example: Any):
        """Load example into schema and subschemas"""
        raise NotImplementedError

    @abstractmethod
    def set_default(self, instance):
        """Set default value of the schema"""
        raise NotImplementedError

    @abstractmethod
    def empty_value(self):
        """Get empty value of the schema"""
        raise NotImplementedError


class BaseSchema(SchemaInterface):
    """Base class for schemas

    Handles some keywords used for any types
    """

    def __init__(self, path: list, schema: dict) -> None:
        self.path = path
        self.raw_schema = schema
        self.default = None if "default" not in schema else schema["default"]
        self.enum = None if "enum" not in schema else schema["enum"]
        self.examples: list[Any] = []

        self.copied_over = False
        self.over_specified = False
        self.problematic = False
        self.patch = False
        self.mapped = False
        self.used_fields: list[SchemaInterface] = []

    def get_path(self) -> list:
        """Get path of the schema"""
        return self.path

    def validate(self, instance: Any) -> bool:
        """Validate instance against schema"""
        try:
            jsonschema.validate(instance, self.raw_schema)
            return True
        except jsonschema.exceptions.ValidationError:
            return False

    @abstractmethod
    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        """Generate instance from schema"""
        raise NotImplementedError
