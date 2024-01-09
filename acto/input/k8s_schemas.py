from abc import ABC, abstractmethod
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
        ...

    @abstractmethod
    def dump_schema(self) -> dict:
        """Dumps the Kubernetes schema into a dictionary (for debugging)"""
        ...


class KubernetesObjectSchema(KubernetesSchema):
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

    def match(self, schema: BaseSchema) -> bool:
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
            exit(1)
        return schema


class KubernetesStringSchema(KubernetesSchema):
    def __init__(self) -> None:
        super().__init__()

    def match(self, schema: BaseSchema) -> bool:
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
    def match(self, schema: BaseSchema) -> bool:
        return isinstance(schema, BooleanSchema)

    def dump_schema(self) -> dict:
        return {"type": "boolean"}


class KubernetesIntegerSchema(KubernetesSchema):
    def match(self, schema: BaseSchema) -> bool:
        return isinstance(schema, IntegerSchema)

    def dump_schema(self) -> dict:
        return {"type": "integer"}


class KubernetesFloatSchema(KubernetesSchema):
    def match(self, schema: BaseSchema) -> bool:
        return isinstance(schema, NumberSchema)

    def dump_schema(self) -> dict:
        return {"type": "number"}


class KubernetesDictSchema(KubernetesSchema):
    def __init__(self, value_cls: KubernetesSchema) -> None:
        super().__init__()
        self.value: KubernetesSchema = value_cls

    def match(self, schema: BaseSchema) -> bool:
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
    def __init__(self, item_cls: KubernetesSchema) -> None:
        super().__init__()
        self.item: KubernetesSchema = item_cls

    def match(self, schema: BaseSchema) -> bool:
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
    def match(self, schema: BaseSchema) -> bool:
        return isinstance(schema, StringSchema)

    def dump_schema(self) -> dict:
        return {"type": "string", "format": "date-time"}


class KubernetesOpaqueSchema(KubernetesSchema):
    def match(self, schema: BaseSchema) -> bool:
        return True

    def dump_schema(self) -> dict:
        return {"type": "object"}


class ObjectMetaSchema(KubernetesObjectSchema):
    def match(self, schema: BaseSchema) -> bool:
        if isinstance(schema, OpaqueSchema):
            return True
        elif isinstance(schema, ObjectSchema):
            return super().match(schema)


KUBERNETES_SKIP_LIST = []


def fetch_k8s_schema_spec(version: str) -> dict:
    """Fetches the Kubernetes schema spec from the Kubernetes repo

    Args:
        version (str): the Kubernetes version e.g. "1.29"

    Returns:
        dict: the Kubernetes schema spec
    """
    r = requests.get(
        f"https://raw.githubusercontent.com/kubernetes/kubernetes/release-{version}/api/openapi-spec/swagger.json"
    )
    return r.json()


class K8sSchemaMatcher:
    """Find Kubernetes schemas that match the given schema"""

    def __init__(self, schema_definitions: dict) -> None:
        """Initializes the Kubernetes schema matcher with the kubernetes schema
        definitions

        Args:
            schema_definitions (dict): schema definitions from the Kubernetes schema spec
        """
        self._k8s_models = self._generate_k8s_models(schema_definitions)

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

    def _generate_k8s_models(self, schema_definitions: dict) -> dict:
        """Generates a dictionary of Kubernetes models for schema matching"""
        k8s_models = dict()

        def resolve(schema_spec: dict) -> KubernetesSchema:
            """Resolves schema type from k8s schema spec"""

            if "$ref" in schema_spec:
                type_str = schema_spec["$ref"].split("/")[-1]
                try:
                    return k8s_models[type_str]
                except KeyError:
                    raise KeyError(f"Cannot resolve type {type_str}")
            elif schema_spec["type"] == "string":
                return KubernetesStringSchema()
            elif schema_spec["type"] == "boolean":
                return KubernetesBooleanSchema()
            elif schema_spec["type"] == "integer":
                return KubernetesIntegerSchema()
            elif schema_spec["type"] == "number":
                return KubernetesFloatSchema()
            elif schema_spec["type"] == "object":
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

    def find_matched_schemas(self, schema: BaseSchema) -> BaseSchema:
        """Finds all Kubernetes schemas that match the given schema"""
        matched_schemas = []
        for kubernetes_schema in self._k8s_models.values():
            if kubernetes_schema.match(schema):
                matched_schemas.append((schema, kubernetes_schema))
                return matched_schemas
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
    import yaml
    import pandas as pd
    import os

    # with open("kafka-crd.yml", "r") as f:
    with open("./test/integration_tests/test_data/rabbitmq_crd.yaml", "r") as f:
        crd = yaml.load(f, Loader=yaml.FullLoader)

    spec_schema = ObjectSchema(
        ["root"], crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"]
    )

    schema_matcher = K8sSchemaMatcher.from_version("1.29")
    matched = schema_matcher.find_matched_schemas(spec_schema)

    for schema, k8s_schema in matched:
        print(
            f"Matched: '.../{'/'.join(schema.path[-2:])}' -> {k8s_schema.k8s_schema_name}"
        )

    df = pd.DataFrame(
        [
            {
                "k8s_schema_name": k8s_schema.k8s_schema_name,
                "schema_path": "/".join(schema.path),
            }
            for schema, k8s_schema in matched
        ]
    )

    print(df["k8s_schema_name"].value_counts())
    print(f"{len(matched)} schemas matched in total")

    print("Dumping k8s schemas to './schemas' ...")
    os.makedirs("schemas", exist_ok=True)
    for schema_name, schema in schema_matcher.dump_k8s_schemas().items():
        with open(f"schemas/{schema_name}.json", "w") as f:
            yaml.dump(schema, f, indent=2)
