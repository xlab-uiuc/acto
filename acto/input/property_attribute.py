from collections import defaultdict
from enum import Flag, auto

from acto.common import PropertyPath


class PropertyAttribute(Flag):
    """PropertyAttribute is a flag that represents the attribute of a property"""

    # pylint: disable=invalid-name
    # Patch is a flag that represents the property behaves as a patch
    Patch = auto()

    # Mapped is a flag that represents the property is mapped to Kubernetes
    # core resource and should be checked by consistency checker
    Mapped = auto()

    # Prune is a flag that represents the property should not generate tests
    Prune = auto()


PROPERTY_ATTRIBUTES: dict[PropertyPath, PropertyAttribute] = defaultdict(
    lambda: PropertyAttribute(0)
)


def tag_property_attribute(
    property_path: list[str], attribute: PropertyAttribute
):
    """Tag a property with attribute"""
    PROPERTY_ATTRIBUTES[PropertyPath(property_path)] |= attribute
