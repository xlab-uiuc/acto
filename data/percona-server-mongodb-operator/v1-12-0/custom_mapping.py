from acto.input.property_attribute import (
    PropertyAttribute,
    tag_property_attribute,
)

tag_property_attribute(["spec", "pmm"], PropertyAttribute.Prune)
tag_property_attribute(["spec", "crVersion"], PropertyAttribute.Prune)
tag_property_attribute(["spec", "mongod", "security"], PropertyAttribute.Prune)
tag_property_attribute(
    ["spec", "mongod", "setParameter"], PropertyAttribute.Prune
)
tag_property_attribute(
    ["spec", "mongod", "replication"], PropertyAttribute.Prune
)
tag_property_attribute(
    ["spec", "mongod", "operationProfiling"], PropertyAttribute.Prune
)
tag_property_attribute(["spec", "mongod", "storage"], PropertyAttribute.Mapped)
