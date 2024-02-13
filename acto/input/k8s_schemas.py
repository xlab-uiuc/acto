"""A module that contains the Kubernetes schema matcher

This module contains the Kubernetes schema matcher that matches acto schemas
to Kubernetes schemas. It is used for generating Kubernetes CRD schemas from
acto schemas.
"""

# pylint: disable=redefined-outer-name

import json
import sys
from abc import ABC, abstractmethod
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Callable, Optional

import requests

from acto.schema import (
    AnyOfSchema,
    ArraySchema,
    BaseSchema,
    BooleanSchema,
    IntegerSchema,
    NumberSchema,
    ObjectSchema,
    OpaqueSchema,
    StringSchema,
)


class KubernetesSchema(ABC):
    """Base class for Kubernetes schema matching"""

    def __init__(
        self,
        schema_spec: dict,
        schema_name: Optional[str] = None,
    ) -> None:
        self.k8s_schema_name = schema_name
        self.schema_spec = schema_spec

    @abstractmethod
    def match(self, schema: BaseSchema) -> bool:
        """Determines if the schema matches the Kubernetes schema"""

    @abstractmethod
    def dump_schema(self) -> dict:
        """Dumps the Kubernetes schema into a dictionary (for debugging)"""

    @abstractmethod
    def update(self, resolve: Callable[[dict], "KubernetesSchema"]) -> None:
        """Resolves k8s schema properties into k8s schema objects"""


class KubernetesUninitializedSchema(KubernetesSchema):
    """Class for uninitialized Kubernetes schema matching"""

    def __init__(self) -> None:
        super().__init__({})

    def match(self, schema) -> bool:
        raise RuntimeError("Uninitialized schema")

    def dump_schema(self) -> dict:
        raise RuntimeError("Uninitialized schema")

    def update(self, resolve: Callable[[dict], "KubernetesSchema"]) -> None:
        raise RuntimeError("Uninitialized schema")


class KubernetesObjectSchema(KubernetesSchema):
    """Class for Kubernetes object schema matching"""

    def __init__(
        self, schema_spec: dict, schema_name: Optional[str] = None
    ) -> None:
        super().__init__(schema_spec, schema_name)
        self.properties: dict[str, KubernetesSchema] = {}

    def update(self, resolve: Callable[[dict], "KubernetesSchema"]) -> None:
        """Resolves k8s schema properties into k8s schema objects"""
        if "properties" not in self.schema_spec:
            return
        for property_name, property_spec in self.schema_spec[
            "properties"
        ].items():
            self.properties[property_name] = resolve(property_spec)
            self.properties[property_name].update(resolve)

    def match(self, schema) -> bool:
        if (
            not isinstance(schema, ObjectSchema)
            or len(self.properties) == 0
            or len(self.properties) != len(schema.properties)
        ):
            return False
        num_mismatch = 0
        for property_name, property_schema in self.properties.items():
            if property_name not in schema.properties:
                # not a match if property is not in schema
                num_mismatch += 1
            elif not property_schema.match(schema.properties[property_name]):
                # not a match if schema does not match property schema
                num_mismatch += 1

        # TODO: How to do approximate matching?
        return bool(num_mismatch == 0)

    def dump_schema(self) -> dict:
        properties = {}
        try:
            for property_name, property_schema in self.properties.items():
                properties[property_name] = property_schema.dump_schema()
        except RecursionError:
            print(f"Recursion error in {self.k8s_schema_name}")
            sys.exit(1)
        return {
            "type": "object",
            "properties": properties,
        }


class KubernetesStringSchema(KubernetesSchema):
    """Class for Kubernetes string schema matching"""

    def match(self, schema) -> bool:
        if isinstance(schema, StringSchema):
            return True
        elif isinstance(schema, AnyOfSchema):
            return any(
                self.match(sub_schema) for sub_schema in schema.possibilities
            )
        else:
            return isinstance(schema, StringSchema)

    def dump_schema(self) -> dict:
        return {"type": "string"}

    def update(self, resolve: Callable[[dict], "KubernetesSchema"]) -> None:
        pass


class KubernetesBooleanSchema(KubernetesSchema):
    """Class for Kubernetes boolean schema matching"""

    def match(self, schema) -> bool:
        return isinstance(schema, BooleanSchema)

    def dump_schema(self) -> dict:
        return {"type": "boolean"}

    def update(self, resolve: Callable[[dict], "KubernetesSchema"]) -> None:
        pass


class KubernetesIntegerSchema(KubernetesSchema):
    """Class for Kubernetes integer schema matching"""

    def match(self, schema) -> bool:
        return isinstance(schema, IntegerSchema)

    def dump_schema(self) -> dict:
        return {"type": "integer"}

    def update(self, resolve: Callable[[dict], "KubernetesSchema"]) -> None:
        pass


class KubernetesFloatSchema(KubernetesSchema):
    """Class for Kubernetes float schema matching"""

    def match(self, schema) -> bool:
        return isinstance(schema, NumberSchema)

    def dump_schema(self) -> dict:
        return {"type": "number"}

    def update(self, resolve: Callable[[dict], "KubernetesSchema"]) -> None:
        pass


class KubernetesMapSchema(KubernetesSchema):
    """Class for Kubernetes map schema matching"""

    def __init__(
        self, schema_spec: dict, schema_name: Optional[str] = None
    ) -> None:
        super().__init__(schema_spec, schema_name)
        self.value: KubernetesSchema = KubernetesUninitializedSchema()

    def match(self, schema) -> bool:
        # Dict schema requires additional_properties to be set
        # and the value of additional_properties to match the
        # additional_properties schema
        if isinstance(schema, ObjectSchema):
            if schema.additional_properties is None:
                return False
            elif not self.value.match(schema.additional_properties):
                return False
            else:
                return True
        else:
            return False

    def dump_schema(self) -> dict:
        return {
            "type": "object",
            "additionalProperties": self.value.dump_schema(),
        }

    def update(self, resolve: Callable[[dict], "KubernetesSchema"]) -> None:
        self.value = resolve(self.schema_spec["additionalProperties"])
        self.value.update(resolve)


class KubernetesArraySchema(KubernetesSchema):
    """Class for Kubernetes array schema matching"""

    def __init__(
        self, schema_spec: dict, schema_name: Optional[str] = None
    ) -> None:
        super().__init__(schema_spec, schema_name)
        self.item: KubernetesSchema = KubernetesUninitializedSchema()

    def match(self, schema) -> bool:
        # List schema requires items to be set
        # and the value of items to match the
        # items schema
        if isinstance(schema, ArraySchema):
            if schema.item_schema is None:
                return False
            elif not self.item.match(schema.item_schema):
                return False
            else:
                return True
        else:
            return False

    def dump_schema(self) -> dict:
        return {"type": "array", "items": self.item.dump_schema()}

    def update(self, resolve: Callable[[dict], KubernetesSchema]) -> None:
        self.item = resolve(self.schema_spec["items"])
        self.item.update(resolve)


class KubernetesDatetimeSchema(KubernetesSchema):
    """Class for Kubernetes datetime schema matching"""

    def match(self, schema) -> bool:
        return isinstance(schema, StringSchema)

    def dump_schema(self) -> dict:
        return {"type": "string", "format": "date-time"}

    def update(self, resolve: Callable[[dict], "KubernetesSchema"]) -> None:
        pass


class KubernetesOpaqueSchema(KubernetesSchema):
    """Class for Kubernetes opaque schema matching"""

    def match(self, schema) -> bool:
        return True

    def dump_schema(self) -> dict:
        return {"type": "object"}

    def update(self, resolve: Callable[[dict], "KubernetesSchema"]) -> None:
        pass


class ObjectMetaSchema(KubernetesObjectSchema):
    """Class for Kubernetes ObjectMeta schema matching"""

    def match(self, schema) -> bool:
        if isinstance(schema, OpaqueSchema):
            return True
        if isinstance(schema, ObjectSchema):
            # ObjectMeta is a special case
            # Its schema is generated specially by controller-gen
            if "name" in schema.properties and "namespace" in schema.properties:
                for key, sub_schema in schema.properties.items():
                    if key not in self.properties:
                        return False
                    if not self.properties[key].match(sub_schema):
                        return False
                return True
        return False


def fetch_k8s_schema_spec(version: str) -> dict:
    """Fetches the Kubernetes schema spec from the Kubernetes repo

    Args:
        version (str): the Kubernetes version e.g. "v1.29.0"

    Returns:
        dict: the Kubernetes schema spec
    """
    # pylint: disable=line-too-long
    resp = requests.get(
        f"https://raw.githubusercontent.com/kubernetes/kubernetes/{version}/api/openapi-spec/swagger.json",
        timeout=5,
    )
    return resp.json()


class K8sSchemaMatcher:
    """Find Kubernetes schemas that match the given schema"""

    def __init__(
        self,
        schema_definitions: dict,
        custom_mappings: Optional[list[tuple[BaseSchema, str]]] = None,
    ) -> None:
        """Initializes the Kubernetes schema matcher with the kubernetes schema
        definitions

        Args:
            schema_definitions (dict): schema definitions from the Kubernetes schema spec
        """
        self._k8s_models = self._generate_k8s_models(schema_definitions)
        self._schema_name_to_property_name = (
            self._generate_schema_name_to_property_name_mapping(
                schema_definitions
            )
        )
        self._custom_mapping_dict = (
            {
                json.dumps(base_schema.path): kubernetes_schema
                for base_schema, kubernetes_schema in custom_mappings
            }
            if custom_mappings is not None
            else {}
        )  # mapping from the encoded schema path to the Kubernetes schema name

    @property
    def k8s_models(self) -> dict[str, KubernetesSchema]:
        """Returns the Kubernetes models"""
        return self._k8s_models

    @classmethod
    def from_version(
        cls,
        version: str,
        custom_mappings: Optional[list[tuple[BaseSchema, str]]] = None,
    ):
        """Factory method that creates a Kubernetes schema matcher from a
        Kubernetes version

        Args:
            version (str): the Kubernetes version e.g. "v1.29.0"

        Returns:
            K8sSchemaMatcher: the Kubernetes schema matcher
        """
        schema_definitions = fetch_k8s_schema_spec(version)["definitions"]
        return cls(schema_definitions, custom_mappings)

    def _generate_schema_name_to_property_name_mapping(
        self, schema_definitions: dict
    ) -> dict[str, set[str]]:
        """Builds a dictionary that maps property names to Kubernetes schema name"""
        schema_name_to_property_name = defaultdict(set)
        for schema_name, schema_spec in schema_definitions.items():
            if schema_name.startswith("io.k8s.apiextensions-apiserver"):
                continue

            properties = schema_spec.get("properties", {})
            for property_name, property_schema in properties.items():
                if ref := (
                    property_schema.get("$ref")
                    or property_schema.get("items", {}).get("$ref")
                ):
                    schema_name = ref.split("/")[-1]
                    schema_name_to_property_name[schema_name].add(property_name)

        return dict(schema_name_to_property_name)

    def _generate_k8s_models(
        self, schema_definitions: dict[str, dict]
    ) -> dict[str, KubernetesSchema]:
        """Generates a dictionary of Kubernetes models for schema matching"""
        k8s_models: dict[str, KubernetesSchema] = {}

        def resolve_named_kubernetes_schema(
            schema_name, schema_spec: dict
        ) -> KubernetesSchema:
            if schema_name.endswith("ObjectMeta"):
                return ObjectMetaSchema(schema_spec, schema_name)
            if schema_spec["type"] == "string":
                return KubernetesStringSchema(schema_spec, schema_name)
            if schema_spec["type"] == "boolean":
                return KubernetesBooleanSchema(schema_spec, schema_name)
            if schema_spec["type"] == "integer":
                return KubernetesIntegerSchema(schema_spec, schema_name)
            if schema_spec["type"] == "number":
                return KubernetesFloatSchema(schema_spec, schema_name)
            if schema_spec["type"] == "object":
                if (
                    "additionalProperties" in schema_spec
                    and "properties" in schema_spec
                ):
                    raise NotImplementedError(
                        "Object with both additional properties and properties"
                    )
                if "additionalProperties" in schema_spec:
                    return KubernetesMapSchema(schema_spec, schema_name)
                if "properties" in schema_spec:
                    return KubernetesObjectSchema(schema_spec, schema_name)
                return KubernetesOpaqueSchema(schema_spec, schema_name)
            if schema_spec["type"] == "array":
                return KubernetesArraySchema(schema_spec, schema_name)
            else:
                raise KeyError(f"Cannot resolve type {schema_spec}")

        def resolve(schema_spec: dict) -> KubernetesSchema:
            """Resolves schema type from k8s schema spec"""

            if "$ref" in schema_spec:
                type_str = schema_spec["$ref"].split("/")[-1]
                try:
                    return k8s_models[type_str]
                except KeyError as exc:
                    raise KeyError(f"Cannot resolve type {type_str}") from exc
            elif schema_spec["type"] == "string":
                return KubernetesStringSchema(schema_spec)
            elif schema_spec["type"] == "boolean":
                return KubernetesBooleanSchema(schema_spec)
            elif schema_spec["type"] == "integer":
                return KubernetesIntegerSchema(schema_spec)
            elif schema_spec["type"] == "number":
                return KubernetesFloatSchema(schema_spec)
            elif schema_spec["type"] == "object":
                if "additionalProperties" in schema_spec:
                    return KubernetesMapSchema(schema_spec)
                if "properties" in schema_spec:
                    return KubernetesObjectSchema(schema_spec)
                return KubernetesOpaqueSchema(schema_spec)
            elif schema_spec["type"] == "array":
                return KubernetesArraySchema(schema_spec)
            else:
                raise KeyError(f"Cannot resolve type {schema_spec}")

        # First initialize all k8s models
        for schema_name, schema_spec in schema_definitions.items():
            if schema_name.startswith("io.k8s.apiextensions-apiserver"):
                continue

            resolved_schema = resolve_named_kubernetes_schema(
                schema_name, schema_spec
            )
            k8s_models[schema_name] = resolved_schema

        # Second pass to resolve the references
        for k8s_schema in k8s_models.values():
            k8s_schema.update(resolve)

        return k8s_models

    def _rank_matched_k8s_schemas(
        self,
        schema: BaseSchema,
        matched_schemas: list[tuple[BaseSchema, KubernetesSchema]],
    ) -> int:
        """returns the index of the best matched schemas using heuristic"""
        # 1. Give priority to the schemas that have been used with the same
        #    property name in k8s schema specs
        if len(schema.path) < 2:
            raise RuntimeError(
                f"Schema path too short {schema.path} for "
                f"{[schema.k8s_schema_name for _, schema in matched_schemas]}"
            )
        schema_name = (
            schema.path[-2] if schema.path[-1] == "ITEM" else schema.path[-1]
        )
        name_matched = []
        for i, (_, k8s_schema) in enumerate(matched_schemas):
            if k8s_schema.k8s_schema_name is None:
                raise RuntimeError(
                    f"Kubernetes schema name not found for {k8s_schema}"
                )
            observed_schema_names = self._schema_name_to_property_name.get(
                k8s_schema.k8s_schema_name, set()
            )
            for observed_schema_name in observed_schema_names:
                if schema_name in observed_schema_name:
                    name_matched.append(i)

        # 2. Use the edit distance between the last salient segment of the
        #    schema path and the last salient segment of the k8s schema name
        #    to rank the matched schemas
        seq_matcher = SequenceMatcher()
        # set seq1 to the last salient segment of the schema path
        schema_name = "/".join(
            schema.path[-3:-1]
            if schema.path[-1] == "ITEM"
            else schema.path[-2:]
        )
        seq_matcher.set_seq1(schema_name)
        max_ratio = 0.0
        max_ratio_schema_idx = 0
        for i, (_, matched_schema) in enumerate(matched_schemas):
            if name_matched and i not in name_matched:
                continue
            if matched_schema.k8s_schema_name is None:
                raise RuntimeError(
                    f"Kubernetes schema name not found for {matched_schema}"
                )
            seq_matcher.set_seq2(matched_schema.k8s_schema_name.split(".")[-1])
            ratio = seq_matcher.ratio()
            if ratio > max_ratio:
                max_ratio = ratio
                max_ratio_schema_idx = i
        return max_ratio_schema_idx

    def find_all_matched_schemas(
        self, schema: BaseSchema
    ) -> list[tuple[BaseSchema, KubernetesSchema]]:
        """Finds all Kubernetes schemas that match the given schema
        including matches of anonymous Kubernetes schemas"""
        top_level_matches = self.find_top_level_matched_schemas(schema)
        return self.expand_top_level_matched_schemas(top_level_matches)

    def find_named_matched_schemas(
        self, schema: BaseSchema
    ) -> list[tuple[BaseSchema, KubernetesSchema]]:
        """Finds all named Kubernetes schemas that match the given schema,
        without anonymous Kubernetes schemas"""
        matched_schemas: list[tuple[BaseSchema, KubernetesSchema]] = []
        for kubernetes_schema in self._k8s_models.values():
            if not isinstance(kubernetes_schema, KubernetesObjectSchema):
                # Avoid Opaque schemas for Kubernetes named schemas
                continue
            if kubernetes_schema.match(schema):
                matched_schemas.append((schema, kubernetes_schema))
        if matched_schemas:
            idx = self._rank_matched_k8s_schemas(schema, matched_schemas)
            matched_schemas = [matched_schemas[idx]]
        if isinstance(schema, ObjectSchema):
            for sub_schema in schema.properties.values():
                matched_schemas.extend(
                    self.find_named_matched_schemas(sub_schema)
                )
        elif isinstance(schema, ArraySchema):
            matched_schemas.extend(
                self.find_named_matched_schemas(schema.get_item_schema())
            )

        return matched_schemas

    def find_top_level_matched_schemas(
        self, schema: BaseSchema
    ) -> list[tuple[BaseSchema, KubernetesSchema]]:
        """Finds all Kubernetes schemas that match the given schema
        at the top level, without returning the matched sub-schemas.
        The returned matches are guaranteed to be named Kubernetes schemas"""
        matched_schemas: list[tuple[BaseSchema, KubernetesSchema]] = []

        # First check the custom mapping
        if (schema_key := json.dumps(schema.path)) in self._custom_mapping_dict:
            kubernetes_schema_name = self._custom_mapping_dict[schema_key]
            return [(schema, self._k8s_models[kubernetes_schema_name])]

        # Look through the Kubernetes schemas
        for kubernetes_schema in self._k8s_models.values():
            if not isinstance(kubernetes_schema, KubernetesObjectSchema):
                # Avoid Opaque schemas for Kubernetes named schemas
                continue
            if kubernetes_schema.match(schema):
                matched_schemas.append((schema, kubernetes_schema))
        if matched_schemas:
            idx = self._rank_matched_k8s_schemas(schema, matched_schemas)
            matched_schemas = [matched_schemas[idx]]
        elif isinstance(schema, ObjectSchema):
            for sub_schema in schema.properties.values():
                matched_schemas.extend(
                    self.find_top_level_matched_schemas(sub_schema)
                )
        elif isinstance(schema, ArraySchema):
            matched_schemas.extend(
                self.find_top_level_matched_schemas(schema.get_item_schema())
            )

        return matched_schemas

    def expand_top_level_matched_schemas(
        self, top_level_matches: list[tuple[BaseSchema, KubernetesSchema]]
    ) -> list[tuple[BaseSchema, KubernetesSchema]]:
        """Expands the top level matches to include all sub-schemas"""
        matched_schemas: list[tuple[BaseSchema, KubernetesSchema]] = []
        # BFS to find all matches
        to_explore: list[tuple[BaseSchema, KubernetesSchema]] = list(
            top_level_matches
        )
        while to_explore:
            crd_schema, k8s_schema = to_explore.pop()

            # Handle custom mapping here, override the matched k8s_schema
            if (
                schema_key := json.dumps(crd_schema.path)
            ) in self._custom_mapping_dict:
                kubernetes_schema_name = self._custom_mapping_dict[schema_key]
                k8s_schema = self._k8s_models[kubernetes_schema_name]
            matched_schemas.append((crd_schema, k8s_schema))

            if isinstance(crd_schema, ObjectSchema):
                if isinstance(k8s_schema, KubernetesObjectSchema):
                    for key, sub_schema in crd_schema.properties.items():
                        if key not in k8s_schema.properties:
                            raise RuntimeError(
                                f"Property {key} not found"
                                f"in k8s schema {k8s_schema.k8s_schema_name}"
                            )
                        to_explore.append(
                            (sub_schema, k8s_schema.properties[key])
                        )
                elif (
                    isinstance(k8s_schema, KubernetesMapSchema)
                    and crd_schema.additional_properties is not None
                ):
                    to_explore.append(
                        (crd_schema.additional_properties, k8s_schema.value)
                    )
                else:
                    raise RuntimeError(
                        "CRD schema type does not match k8s schema type"
                        f"({crd_schema}, {k8s_schema})"
                    )
            elif isinstance(crd_schema, ArraySchema):
                if isinstance(k8s_schema, KubernetesArraySchema):
                    to_explore.append(
                        (crd_schema.get_item_schema(), k8s_schema.item)
                    )
                else:
                    raise RuntimeError(
                        "CRD schema type does not match k8s schema type"
                        f"({crd_schema}, {k8s_schema})"
                    )

        return matched_schemas

    def override_schema_matches(
        self,
        existing_matches: list[tuple[BaseSchema, KubernetesSchema]],
        override: list[tuple[BaseSchema, KubernetesSchema]],
    ) -> list[tuple[BaseSchema, KubernetesSchema]]:
        """Override the existing matches with a list of custom matches

        Args:
            existing_matches: a full list of matches, containing subproperties
            override: custom top-level schema matches

        Return:
            overriden full list of matches
        """
        matched_schema_map: dict[str, tuple[BaseSchema, KubernetesSchema]] = {}

        for schema, kubernetes_schema in existing_matches:
            matched_schema_map[json.dumps(schema.path)] = (
                schema,
                kubernetes_schema,
            )

        expanded_overrides = self.expand_top_level_matched_schemas(override)
        for schema, kubernetes_schema in expanded_overrides:
            matched_schema_map[json.dumps(schema.path)] = (
                schema,
                kubernetes_schema,
            )

        return list(matched_schema_map.values())

    def dump_k8s_schemas(self) -> dict:
        """Dumps all Kubernetes schemas into a dictionary (for debugging)"""
        return {
            schema_name: schema.dump_schema()
            for schema_name, schema in self._k8s_models.items()
        }


if __name__ == "__main__":
    # import os

    import pandas as pd
    import yaml

    with open(
        # "./test/integration_tests/test_data/cassop_crd.yaml",
        # "./test/integration_tests/test_data/kafka_crd.yaml",
        "./test/integration_tests/test_data/rabbitmq_crd.yaml",
        "r",
        encoding="utf-8",
    ) as f:
        crd = yaml.load(f, Loader=yaml.FullLoader)

    spec_schema = ObjectSchema(
        ["root"], crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"]
    )

    schema_matcher = K8sSchemaMatcher.from_version("1.29.0")
    matched = schema_matcher.find_all_matched_schemas(spec_schema)

    for schema, k8s_schema in matched:
        # pylint: disable-next=invalid-name
        path_ending = "/".join(schema.path[-2:])
        schema_name = k8s_schema.k8s_schema_name.split(".")[-1]
        print(f"Matched: '.../{path_ending}' -> {schema_name}")

    # # generate integration test code
    # for schema, k8s_schema in matched:
    #     # pylint: disable-next=invalid-name
    #     path_ending = "/".join(schema.path[-3:])
    #     schema_name = '.'.join(k8s_schema.k8s_schema_name.split(".")[-2:])
    #     print(f'self.assert_exists("{path_ending}", "{schema_name}", matches)')

    df = pd.DataFrame(
        [
            {
                "k8s_schema_name": k8s_schema.k8s_schema_name,
                "schema_path": "/".join(schema.path),
            }
            for schema, k8s_schema in matched
        ]
    )

    print(df["k8s_schema_name"].value_counts().to_string())
    print(f"{len(matched)} schemas matched in total")

    # print("Dumping k8s schemas to './schemas' ...")
    # os.makedirs("schemas", exist_ok=True)
    # for schema_name, schema in schema_matcher.dump_k8s_schemas().items():
    #     with open(f"schemas/{schema_name}.yaml", "w") as f:
    #         yaml.dump(schema, f, indent=2)
