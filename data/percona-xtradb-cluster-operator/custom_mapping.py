from acto.input.property_attribute import (
    PropertyAttribute,
    tag_property_attribute,
)
from acto.input.test_generators.generator import test_generator
from acto.input.test_generators.service import service_type_tests
from acto.input.test_generators.stateful_set import replicas_tests

tag_property_attribute(["spec", "pmm"], PropertyAttribute.Prune)
tag_property_attribute(["spec", "backup"], PropertyAttribute.Prune)
tag_property_attribute(["spec", "proxysql"], PropertyAttribute.Prune)
tag_property_attribute(["spec", "updateStrategy"], PropertyAttribute.Prune)
tag_property_attribute(["spec", "upgradeOptions"], PropertyAttribute.Prune)

test_generator(paths=["haproxy/size"])(replicas_tests)
test_generator(paths=["proxysql/size"])(replicas_tests)
test_generator(paths=["pxc/size"])(replicas_tests)

test_generator(property_name="replicasServiceType")(service_type_tests)
