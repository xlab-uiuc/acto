from acto.input.property_attribute import (
    PropertyAttribute,
    tag_property_attribute,
)

tag_property_attribute(["spec", "ingress", "istio"], PropertyAttribute.Prune)
tag_property_attribute(
    ["spec", "registry", "override"], PropertyAttribute.Prune
)
