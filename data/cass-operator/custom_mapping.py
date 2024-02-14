from acto.input.property_attribute import (
    PropertyAttribute,
    tag_property_attribute,
)
from acto.input.test_generators.generator import test_generator
from acto.input.test_generators.stateful_set import replicas_tests

tag_property_attribute(
    ["spec", "managementApiAuth", "manual"], PropertyAttribute.Prune
)

test_generator(property_name="size")(replicas_tests)
