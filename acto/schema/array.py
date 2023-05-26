from typing import List, Tuple

from .base import BaseSchema, TreeNode
from .schema import extract_schema


class ArraySchema(BaseSchema):
    '''Representation of an array node
    
    It handles
        - minItems
        - maxItems
        - items
        - uniqueItems
    '''
    default_min_items = 0
    default_max_items = 5

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)
        self.item_schema = extract_schema(self.path + ['ITEM'], schema['items'])
        self.min_items = self.default_min_items if 'minItems' not in schema else schema['minItems']
        self.max_items = self.default_max_items if 'maxItems' not in schema else schema['maxItems']
        self.unique_items = None if 'uniqueItems' not in schema else schema['exclusiveMinimum']

    def get_item_schema(self):
        return self.item_schema

    def get_all_schemas(self) -> Tuple[list, list, list]:
        if self.problematic:
            return [], [], []

        normal_schemas = []
        pruned_by_overspecified = []
        pruned_by_copiedover = []

        child_schema_tuple = self.item_schema.get_all_schemas()
        normal_schemas.extend(child_schema_tuple[0])
        pruned_by_overspecified.extend(child_schema_tuple[1])
        pruned_by_copiedover.extend(child_schema_tuple[2])

        if self.copied_over:
            if len(self.used_fields) == 0:
                keep = [normal_schemas.pop()]
            else:
                keep = []
            for schema in normal_schemas:
                if schema.path in self.used_fields:
                    keep.append(schema)
                else:
                    pruned_by_copiedover.append(schema)
            normal_schemas = keep
        elif self.over_specified:
            if len(self.used_fields) == 0:
                keep = [normal_schemas.pop()]
            else:
                keep = []
            for schema in normal_schemas:
                if schema.path in self.used_fields:
                    keep.append(schema)
                else:
                    pruned_by_overspecified.append(schema)
            normal_schemas = keep

        if self not in normal_schemas:
            normal_schemas.append(self)

        return normal_schemas, pruned_by_overspecified, pruned_by_copiedover
    
    def get_normal_semantic_schemas(self) -> Tuple[List['BaseSchema'], List['BaseSchema']]:
        normal_schemas = [self]
        semantic_schemas = []

        child_schema_tuple = self.item_schema.get_normal_semantic_schemas()
        normal_schemas.extend(child_schema_tuple[0])
        semantic_schemas.extend(child_schema_tuple[1])

        return normal_schemas, semantic_schemas

    def to_tree(self) -> TreeNode:
        node = TreeNode(self.path)
        node.add_child('ITEM', self.item_schema.to_tree())
        return node

    def load_examples(self, example: list):
        self.examples.append(example)
        for item in example:
            self.item_schema.load_examples(item)

    def set_default(self, instance):
        self.default = instance

    def empty_value(self):
        return []

    def __str__(self) -> str:
        return 'Array'

    def __getitem__(self, key):
        return self.item_schema

    def __setitem__(self, key, value):
        self.item_schema = value
