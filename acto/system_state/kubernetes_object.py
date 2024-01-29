"""Base class for all Kubernetes objects."""


import abc
from typing import Any, Callable, Literal, TypeAlias

import deepdiff
import deepdiff.model as deepdiff_model
import kubernetes
import kubernetes.client
import kubernetes.client.models as kubernetes_models
import pydantic
from deepdiff.helper import NotPresent
from typing_extensions import Self

from acto.common import (
    EXCLUDE_PATH_REGEX,
    Diff,
    PropertyPath,
    flatten_dict,
    flatten_list,
)


class KubernetesResourceInterface(pydantic.BaseModel):
    """Helper interface shared by all Kubernetes resources"""

    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)

    metadata: kubernetes_models.V1ObjectMeta


class KubernetesListNamespacedObjectMethodReturnType(abc.ABC):
    """Kubernetes list namespaced object method return type"""

    @property
    @abc.abstractmethod
    def items(self) -> list[KubernetesResourceInterface]:
        """Return Kubernetes list namespaced object method items"""


KubernetesListNamespacedObjectMethod: TypeAlias = Callable[
    ..., KubernetesListNamespacedObjectMethodReturnType
]

DiffType: TypeAlias = Literal[
    "type_changes",
    "values_changed",
    "iterable_item_added",
    "iterable_item_removed",
    "dictionary_item_added",
    "dictionary_item_removed",
    "set_item_added",
    "set_item_removed",
    "attribute_added",
    "attribute_removed",
]

# ObjectDiff: TypeAlias = dict[DiffType, dict[str, Diff]]


class ObjectDiff(pydantic.RootModel):
    """Object diff, based on TreeView of deepdiff"""

    root: dict[DiffType, dict[str, Diff]]

    @classmethod
    def from_deepdiff(cls, diff: deepdiff_model.TreeResult) -> Self:
        """Create ObjectDiff from deepdiff.DeepDiff"""
        data: dict[TypeAlias, dict[str, Diff]] = {}

        for category, changes in diff.items():
            data[category] = {}
            for change in changes:
                # Heuristic
                # When an entire dict/list is added or removed, flatten this
                # dict/list to help field matching and value comparison in oracle

                if (isinstance(change.t1, (dict, list))) and (
                    change.t2 is None or isinstance(change.t2, NotPresent)
                ):
                    if isinstance(change.t1, dict):
                        flattened_changes = flatten_dict(change.t1, [])
                    else:
                        flattened_changes = flatten_list(change.t1, [])
                    for path, value in flattened_changes:
                        if value is None or isinstance(value, NotPresent):
                            continue
                        str_path = change.path()
                        for i in path:
                            str_path += f"[{i}]"
                        data[category][str_path] = Diff(
                            prev=value,
                            curr=change.t2,
                            path=PropertyPath(
                                change.path(output_format="list") + path
                            ),
                        )
                elif (isinstance(change.t2, (dict, list))) and (
                    change.t1 is None or isinstance(change.t1, NotPresent)
                ):
                    if isinstance(change.t2, dict):
                        flattened_changes = flatten_dict(change.t2, [])
                    else:
                        flattened_changes = flatten_list(change.t2, [])
                    for path, value in flattened_changes:
                        if value is None or isinstance(value, NotPresent):
                            continue
                        str_path = change.path()
                        for i in path:
                            str_path += f"[{i}]"
                        data[category][str_path] = Diff(
                            prev=change.t1,
                            curr=value,
                            path=PropertyPath(
                                change.path(output_format="list") + path
                            ),
                        )
                else:
                    data[category][change.path()] = Diff(
                        prev=change.t1,
                        curr=change.t2,
                        path=PropertyPath(change.path(output_format="list")),
                    )

        return cls.model_validate(data)


class KubernetesObject(abc.ABC, pydantic.RootModel):
    """Base class for all Kubernetes objects."""

    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)

    root: Any

    @classmethod
    @abc.abstractmethod
    def from_api_client(cls, api_client: kubernetes.client.ApiClient) -> Self:
        """Create Kubernetes object from ApiClient"""
        raise NotImplementedError()

    def diff_from(self, other: Self) -> ObjectDiff:
        """Diff with other Kubernetes object"""
        return ObjectDiff.from_deepdiff(
            deepdiff.DeepDiff(
                self,
                other,
                exclude_regex_paths=EXCLUDE_PATH_REGEX,
                view="tree",
            )
        )

    @abc.abstractmethod
    def check_health(self) -> tuple[bool, str]:
        """Check if object is healthy

        Returns:
            tuple[bool, str]: (is_healthy, reason)
        """
        raise NotImplementedError()

    @pydantic.model_serializer
    def serialize(self) -> dict:
        """Serialize Kubernetes object"""
        raise NotImplementedError()


class KubernetesNamespacedObject(KubernetesObject):
    """Base class for all Kubernetes namespaced objects."""

    @classmethod
    @abc.abstractmethod
    def from_api_client_namespaced(
        cls, api_client: kubernetes.client.ApiClient, namespace: str
    ) -> Self:
        """Create Kubernetes object from ApiClient"""
        raise NotImplementedError()

    @classmethod
    def from_api_client(cls, api_client: kubernetes.client.ApiClient) -> Self:
        return cls.from_api_client_namespaced(api_client, "default")


class KubernetesListObject(KubernetesObject):
    """Base class for all Kubernetes objects stored as a list."""

    root: list[Any]

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, key: int) -> Any:
        return self.root[key]


class KubernetesDictObject(KubernetesObject):
    """Base class for all Kubernetes objects stored as a dict."""

    root: dict[str, Any]

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, key: str) -> Any:
        return self.root[key]


class KubernetesNamespacedListObject(KubernetesNamespacedObject):
    """Base class for all Kubernetes namespaced objects stored as a list."""

    root: list[Any]

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, key: int) -> Any:
        return self.root[key]


class KubernetesNamespacedDictObject(KubernetesNamespacedObject):
    """Base class for all Kubernetes namespaced objects stored as a dict."""

    root: dict[str, Any]

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, key: str) -> Any:
        return self.root[key]


def list_object_helper(
    method: KubernetesListNamespacedObjectMethod,
) -> dict[str, KubernetesResourceInterface]:
    """List object helper"""
    result = {}
    for obj in method(watch=False).items:
        result[obj.metadata.name] = obj
    return result


def list_namespaced_object_helper(
    method: KubernetesListNamespacedObjectMethod,
    namespace: str,
) -> dict[str, KubernetesResourceInterface]:
    """List namespaced object helper"""
    result = {}
    for obj in method(namespace=namespace, watch=False).items:
        result[obj.metadata.name] = obj
    return result
