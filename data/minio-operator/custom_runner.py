from typing import Self

import kubernetes

from acto.input.input import CustomPropertySchemaMapping
from acto.runner.runner import RunnerHookType
from acto.schema.base import BaseSchema
from acto.schema.under_specified import UnderSpecifiedSchema

NEXT_CONFIG: dict = {}
SECRET_NAME: str = "custom-minio-secret"


class MinIOConfigSchema(UnderSpecifiedSchema):
    """Under-specified schema for MinIO config

    Currently a workaround using a module-level variable to store the config,
        as we do not have good support to consider ConfigMap/Secret as inputs
    """

    def encode(self, value: dict) -> str:
        # Set the global variable
        global NEXT_CONFIG  # pylint: disable=global-statement
        NEXT_CONFIG = value
        return SECRET_NAME

    def decode(self, value: str) -> dict:
        return NEXT_CONFIG

    @classmethod
    def from_original_schema(cls, original_schema: BaseSchema) -> Self:
        # with open(
        #     "data/tidb-operator/v1-6-0/tidb_config.json",
        #     "r",
        #     encoding="utf-8",
        # ) as file:
        #     config_schema = json.load(file)

        # return cls(
        #     original_schema.path, original_schema.raw_schema, config_schema
        # )
        raise NotImplementedError("Not implemented")


def minio_config_hook(api_client: kubernetes.client.ApiClient) -> None:
    """Custom runner hook for Minio"""
    print("Custom runner hook for Minio")

    # Create Secret based on the global variable
    # NEXT_CONFIG

    # SECRET_NAME
    _ = api_client


CUSTOM_RUNNER_HOOKS: list[RunnerHookType] = [minio_config_hook]

CUSTOM_PROPERTY_SCHEMA_MAPPING = [
    CustomPropertySchemaMapping(
        schema_path=["spec", "tidb", "config"], custom_schema=MinIOConfigSchema
    )
]
