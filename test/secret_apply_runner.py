import kubernetes

from acto.kubectl_client.kubectl import KubectlClient
from acto.runner.runner import RunnerHookType
from acto.utils.thread_logger import get_thread_logger

SECRET_PATHS: list = []


def secret_config_hook(
    api_client: kubernetes.client.ApiClient, kubectl_client: KubectlClient
) -> None:
    """Custom runner hook for applying secrets"""
    _ = api_client
    logger = get_thread_logger()
    logger.info("Custom runner hook for applying secrets")
    print("Custom runner hook for applying secrets")

    # Create Secret based on the global variable
    global SECRET_PATHS  # pylint: disable=global-statement,global-variable-not-assigned
    next_secret = SECRET_PATHS.pop(0) if SECRET_PATHS else None
    if next_secret is None:
        logger.info("No more secrets to apply")
        return
    kubectl_client.kubectl(
        [
            "apply",
            "-f",
            next_secret,
        ],
        capture_output=True,
        text=True,
    )


CUSTOM_RUNNER_HOOKS: list[RunnerHookType] = [secret_config_hook]
