from acto.input.test_generators.generator import test_generator
from acto.input.test_generators.stateful_set import replicas_tests

test_generator(property_name="nodes")(replicas_tests)
