from typing_extensions import Self

import kubernetes
from kubernetes.client.rest import ApiException

from acto.input.input import CustomPropertySchemaMapping
from acto.runner.runner import RunnerHookType
from acto.schema.base import BaseSchema
from acto.schema.under_specified import UnderSpecifiedSchema
from acto.utils.thread_logger import get_thread_logger

import base64
import json
import yaml

NEXT_CONFIG: dict = {}
SECRET_NAME: str = "storage-configuration"


class MinIOConfigSchema(UnderSpecifiedSchema):
    """Under-specified schema for MinIO config

    Currently a workaround using a module-level variable to store the config,
        as we do not have good support to consider ConfigMap/Secret as inputs
    """

    def encode(self, value: dict) -> str:
        # Set the global variable
        global NEXT_CONFIG  # pylint: disable=global-statement
        NEXT_CONFIG = value
        logger = get_thread_logger()
        logger.info("encoding")
        logger.info(NEXT_CONFIG)
        return SECRET_NAME

    def decode(self, value: str) -> dict:
        logger = get_thread_logger()
        logger.info("decoding")
        logger.info(value)
        return NEXT_CONFIG

    @classmethod
    def from_original_schema(cls, original_schema: BaseSchema) -> Self:
        with open(
            "data/minio-operator/v7-0-0/minio_config.json",
            "r",
            encoding="utf-8",
        ) as file:
            config_schema = json.load(file)

        return cls(
            original_schema.path, original_schema.raw_schema, config_schema
        )
        # raise NotImplementedError("Not implemented")


def minio_config_hook(api_client: kubernetes.client.ApiClient) -> None:
    """Custom runner hook for Minio"""
    logger = get_thread_logger()
    logger.info("Custom runner hook for Minio")
    print("Custom runner hook for Minio")

    # Create Secret based on the global variable
    # NEXT_CONFIG
    env_exports = "export MINIO_ROOT_USER=\"minio\"\nexport MINIO_ROOT_PASSWORD=\"minio123\"\nexport MINIO_BROWSER=\"on\"\n"
    for key, value in NEXT_CONFIG.items():
        env_exports += f"export {key}={value}\n"
    logger.info(env_exports)
    print(env_exports)
    # secret = { "config.env": base64.b64encode(env_exports.encode("ascii")).decode("ascii") }
    secret = {
        "apiVersion": "v1",
        "kind": "Secret",
        "stringData": { "config.env" : env_exports },
        "metadata": {"name": "storage-configuration", "namespace": "minio-operator"},
        "type": "Opaque"
    }
    v1_api = kubernetes.client.CoreV1Api(api_client)
    try:
        v1_api.patch_namespaced_secret(name=SECRET_NAME, namespace="minio-operator", body=secret)
        logger.info(f"Secret '{SECRET_NAME}' patched successfully.")
        print(f"Secret '{SECRET_NAME}' patched successfully.")
        print(v1_api.read_namespaced_secret(SECRET_NAME, namespace="minio-operator"))
    except ApiException as e:
        logger.info("Exception when calling CoreV1Api->patch_namespaced_resource_quota_status: %s\n" % e)
        print("Exception when calling CoreV1Api->patch_namespaced_resource_quota_status: %s\n" % e)
    


CUSTOM_RUNNER_HOOKS: list[RunnerHookType] = [minio_config_hook]

CUSTOM_PROPERTY_SCHEMA_MAPPING = [
    CustomPropertySchemaMapping(
        schema_path=["spec", "configuration", "name"], custom_schema=MinIOConfigSchema
    )
]
