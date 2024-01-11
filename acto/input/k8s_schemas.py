"""A module that contains the Kubernetes schema matcher

This module contains the Kubernetes schema matcher that matches acto schemas
to Kubernetes schemas. It is used for generating Kubernetes CRD schemas from
acto schemas.
"""
# pylint: disable=redefined-outer-name

import sys
from abc import ABC, abstractmethod
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Callable

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

    @abstractmethod
    def match(self, schema: BaseSchema) -> bool:
        """Determines if the schema matches the Kubernetes schema"""

    @abstractmethod
    def dump_schema(self) -> dict:
        """Dumps the Kubernetes schema into a dictionary (for debugging)"""


class KubernetesObjectSchema(KubernetesSchema):
    """Class for Kubernetes object schema matching"""

    def __init__(self, schema_name, schema_spec) -> None:
        self.k8s_schema_name: str = schema_name
        self.schema_spec = schema_spec
        self.properties: dict[str, KubernetesSchema] = {}

    def update(self, resolve: Callable[[dict], "KubernetesSchema"]) -> None:
        """Resolves k8s schema properties into k8s schema objects"""
        if "properties" not in self.schema_spec:
            return
        for property_name, property_spec in self.schema_spec[
            "properties"
        ].items():
            self.properties[property_name] = resolve(property_spec)

    def match(self, schema) -> bool:
        if (
            not isinstance(schema, ObjectSchema)
            or len(self.properties) != len(schema.properties)
            or len(self.properties) == 0
        ):
            return False
        for property_name, property_schema in self.properties.items():
            if property_name not in schema.properties:
                # not a match if property is not in schema
                return False
            elif not property_schema.match(schema.properties[property_name]):
                # not a match if schema does not match property schema
                return False
        return True

    def dump_schema(self) -> dict:
        schema = {
            "type": "object",
            "properties": {},
        }
        try:
            for property_name, property_schema in self.properties.items():
                schema["properties"][
                    property_name
                ] = property_schema.dump_schema()
        except RecursionError:
            print(f"Recursion error in {self.k8s_schema_name}")
            sys.exit(1)
        return schema


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


class KubernetesBooleanSchema(KubernetesSchema):
    """Class for Kubernetes boolean schema matching"""

    def match(self, schema) -> bool:
        return isinstance(schema, BooleanSchema)

    def dump_schema(self) -> dict:
        return {"type": "boolean"}


class KubernetesIntegerSchema(KubernetesSchema):
    """Class for Kubernetes integer schema matching"""

    def match(self, schema) -> bool:
        return isinstance(schema, IntegerSchema)

    def dump_schema(self) -> dict:
        return {"type": "integer"}


class KubernetesFloatSchema(KubernetesSchema):
    """Class for Kubernetes float schema matching"""

    def match(self, schema) -> bool:
        return isinstance(schema, NumberSchema)

    def dump_schema(self) -> dict:
        return {"type": "number"}


class KubernetesDictSchema(KubernetesSchema):
    """Class for Kubernetes dict schema matching"""

    def __init__(self, value_cls: KubernetesSchema) -> None:
        super().__init__()
        self.value: KubernetesSchema = value_cls

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


class KubernetesListSchema(KubernetesSchema):
    """Class for Kubernetes list schema matching"""

    def __init__(self, item_cls: KubernetesSchema) -> None:
        super().__init__()
        self.item: KubernetesSchema = item_cls

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


class KubernetesDatetimeSchema(KubernetesSchema):
    """Class for Kubernetes datetime schema matching"""

    def match(self, schema) -> bool:
        return isinstance(schema, StringSchema)

    def dump_schema(self) -> dict:
        return {"type": "string", "format": "date-time"}


class KubernetesOpaqueSchema(KubernetesSchema):
    """Class for Kubernetes opaque schema matching"""

    def match(self, schema) -> bool:
        return True

    def dump_schema(self) -> dict:
        return {"type": "object"}


class ObjectMetaSchema(KubernetesObjectSchema):
    """Class for Kubernetes ObjectMeta schema matching"""

    def match(self, schema) -> bool:
        if isinstance(schema, OpaqueSchema):
            return True
        if isinstance(schema, ObjectSchema):
            return super().match(schema)
        return False


KUBERNETES_SKIP_LIST = []


def fetch_k8s_schema_spec(version: str) -> dict:
    """Fetches the Kubernetes schema spec from the Kubernetes repo

    Args:
        version (str): the Kubernetes version e.g. "1.29"

    Returns:
        dict: the Kubernetes schema spec
    """
    # pylint: disable=line-too-long
    resp = requests.get(
        f"https://raw.githubusercontent.com/kubernetes/kubernetes/release-{version}/api/openapi-spec/swagger.json",
        timeout=5,
    )
    return resp.json()


class K8sSchemaMatcher:
    """Find Kubernetes schemas that match the given schema"""

    def __init__(self, schema_definitions: dict) -> None:
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

    @classmethod
    def from_version(cls, version: str):
        """Factory method that creates a Kubernetes schema matcher from a
        Kubernetes version

        Args:
            version (str): the Kubernetes version e.g. "1.29"

        Returns:
            K8sSchemaMatcher: the Kubernetes schema matcher
        """
        schema_definitions = fetch_k8s_schema_spec(version)["definitions"]
        return cls(schema_definitions)

    def _generate_schema_name_to_property_name_mapping(
        self, schema_definitions: dict
    ) -> dict:
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

        return schema_name_to_property_name

    def _generate_k8s_models(self, schema_definitions: dict) -> dict:
        """Generates a dictionary of Kubernetes models for schema matching"""
        k8s_models = {}

        def resolve(schema_spec: dict) -> KubernetesSchema:
            """Resolves schema type from k8s schema spec"""

            if "$ref" in schema_spec:
                type_str = schema_spec["$ref"].split("/")[-1]
                try:
                    return k8s_models[type_str]
                except KeyError as exc:
                    raise KeyError(f"Cannot resolve type {type_str}") from exc
            elif schema_spec["type"] == "string":
                return KubernetesStringSchema()
            elif schema_spec["type"] == "boolean":
                return KubernetesBooleanSchema()
            elif schema_spec["type"] == "integer":
                return KubernetesIntegerSchema()
            elif schema_spec["type"] == "number":
                return KubernetesFloatSchema()
            elif schema_spec["type"] == "object":
                if "additionalProperties" in schema_spec:
                    return KubernetesDictSchema(
                        resolve(schema_spec["additionalProperties"])
                    )
                return KubernetesOpaqueSchema()
            elif schema_spec["type"] == "array":
                return KubernetesListSchema(resolve(schema_spec["items"]))
            else:
                raise KeyError(f"Cannot resolve type {schema_spec}")

        for schema_name, schema_spec in schema_definitions.items():
            if schema_name.startswith("io.k8s.apiextensions-apiserver"):
                continue

            if schema_name.endswith("ObjectMeta"):
                schema = ObjectMetaSchema(schema_name, schema_spec)
            else:
                schema = KubernetesObjectSchema(schema_name, schema_spec)

            k8s_models[schema_name] = schema

        for schema in k8s_models.values():
            schema.update(resolve)

        return k8s_models

    def _rank_matched_k8s_schemas(
        self,
        schema: BaseSchema,
        matched_schemas: [tuple[BaseSchema, KubernetesSchema]],
    ) -> int:
        """returns the index of the best matched schemas using heuristic"""
        # 1. Give priority to the schemas that have been used with the same
        #    property name in k8s schema specs
        schema_name = (
            schema.path[-2] if schema.path[-1] == "ITEM" else schema.path[-1]
        )
        name_matched = []
        for i, (_, k8s_schema) in enumerate(matched_schemas):
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
        max_ratio = 0
        max_ratio_schema_idx = 0
        for i, (_, matched_schema) in enumerate(matched_schemas):
            if name_matched and i not in name_matched:
                continue
            seq_matcher.set_seq2(matched_schema.k8s_schema_name.split(".")[-1])
            ratio = seq_matcher.ratio()
            if ratio > max_ratio:
                max_ratio = ratio
                max_ratio_schema_idx = i
        return max_ratio_schema_idx

    def find_matched_schemas(self, schema: BaseSchema) -> BaseSchema:
        """Finds all Kubernetes schemas that match the given schema"""
        matched_schemas = []
        for kubernetes_schema in self._k8s_models.values():
            if kubernetes_schema.match(schema):
                matched_schemas.append((schema, kubernetes_schema))
        if matched_schemas:
            idx = self._rank_matched_k8s_schemas(schema, matched_schemas)
            matched_schemas = [matched_schemas[idx]]
        if isinstance(schema, ObjectSchema):
            for sub_schema in schema.properties.values():
                matched_schemas.extend(self.find_matched_schemas(sub_schema))
        elif isinstance(schema, ArraySchema):
            matched_schemas.extend(
                self.find_matched_schemas(schema.get_item_schema())
            )

        return matched_schemas

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

    schema_matcher = K8sSchemaMatcher.from_version("1.29")
    matched = schema_matcher.find_matched_schemas(spec_schema)

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
    #     with open(f"schemas/{schema_name}.json", "w") as f:
    #         yaml.dump(schema, f, indent=2)
