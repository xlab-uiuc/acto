# Test Generator

## Introduction

Acto creates test cases for each type of CRD schemas using a set of builtin test generator functions. These functions provide:

- Primitive test cases for primitive property types such as string, number, and boolean.
- Semantic test cases for matched kubernetes schemas.
  such as `v1.Pod` and `v1.StatefulSet`.

Additional custom test generators can be specified to

- [Add semantic test cases for operator specific schemas.](#custom-semantic-test-generator)
- [Override or extend the default test generation testcases.](#override-or-extend-default-test-generator)
- [Apply built-in test generators to more schemas.](#apply-built-in-test-generators-to-more-schemas)

## Test Generator Functions

Test generators are functions that takes a schema as argument and returns a list of test cases. 
  
```python
@test_generator(...)
def test_generator_function(schema: BaseSchema) -> List[TestCase]:
    ...
```

To specify which schema in the CRD should the test generator function handle, annotate the function with the `@test_generator` decorator and pass schema contraints as arguments. A schema would be handled by a test generator function if all constraints are satified and the function has the highest priority out of all matched functions. The properties of the schema that can be constrained are:

- `k8s_schema_name` - `str | None`

  The name suffix of the kubernetes schema if the schema matches to one.

- `property_name` - `str | None`

  The name of the property within the CRD schema.

- `property_type` - `str | None`

  The type of the property within the CRD schema. The type can be one of the following: `AnyOf`, `Array`, `Boolean`, `Integer`, `Number`, `Object`, `OneOf`, `Opaque`, `String`

- `paths` - `List[str] | None`

  The list of path suffixes of the schema within the CRD schema. For example, the path `spec.cluster.replicas` would be specified with `['spec.cluster.replicas']` or `['cluster.resplicas']`.

- `priority` - `Priority`
  
  The priority of the test generator. The priority is used to determine which test generator to apply to a schema when multiple test generators are matched to the same schema. The priority can be one of the following (shown in increasing order of priority):

  - `Priority.PRIMITIVE`
  - `Priority.SEMANTIC`
  - `Priority.CUSTOM` (default value)

## Examples

### Custom Semantic Test Generator

For operator specific schemas, you can implement custom test generators to add semantic test cases. For example, the following is a test generator for the `updateStrategy` property in the Percona XtraDB Cluster Operator CRD. This schema is of type `string` and could be configured with `SmartUpdate`, `RollingUpdate`, or `OnDelete`.

```python
from acto.input.test_generators import test_generator
from acto.input.testcase import TestCase
from acto.schema import StringSchema

@test_generator(property_name='updateStrategy', property_type="String")
def update_strategy_tests(schema: StringSchema) -> List[TestCase]:
    return [
        TestCase(
            name='update-strategy-smart-update',
            preconditions=lambda x: x != 'SmartUpdate',
            mutators=lambda x: 'SmartUpdate',
            setup=lambda x: None,
        ),
        TestCase(
            name='update-strategy-rolling-update',
            preconditions=lambda x: x != 'RollingUpdate',
            mutators=lambda x: 'RollingUpdate',
            setup=lambda x: None,
        ),
        TestCase(
            name='update-strategy-on-delete',
            preconditions=lambda x: x != 'OnDelete',
            mutators=lambda x: 'OnDelete',
            setup=lambda x: None,
        ),
        TestCase(
            name='update-strategy-invalid',
            preconditions=lambda x: x in ['SmartUpdate', 'RollingUpdate', 'OnDelete'],
            mutators=lambda x: 'InvalidUpdateStrategy',
            setup=lambda x: None,
            invalid=True,
        ),
    ]
```

The generator function will attach to any schemas with property name `updateStrategy` and is of type `String`. Since the property name `updateStrategy` is unique in the Percona XtraDB Cluster Operator CRD, the generator function will only be applied to that schema. In the case where the property name is not unique, `paths` can be used to specify the schema path directly.

Notice that an additional test case `InvalidUpdateStrategy` is added to test the behavior when the property is set to an invalid value. This is a common pattern for test generators to include a test case that tests the behavior when the property is set to an invalid value. This allows Acto to also test for misoperations (e.g. from typos).

### Override or Extend Default Test Generator

Sometimes, you want to add addtional test cases to the default test generator. For example, the default test generator for `v1.StatefulSet.spec.replicas` only generates test cases for integer values but many CRDs allow string values as well. The following test generator inherites the test cases from the default test generator using function composition and adds additional test cases for string values.

```python
from acto.input.test_generators import test_generator, replicas_tests
from acto.input.testcase import TestCase
from acto.schema import StringSchema

@test_generator(property_name='updateStrategy')
def custom_replicas_tests(schema) -> List[TestCase]:
    return [
        *replicas_tests(schema), # inherit test cases from the builtin replicas test generator
        TestCase(
            name='replicas-string-1',
            preconditions=lambda x: x is not None and isinstance(x, int),
            mutators=lambda x: '1',
            setup=lambda x: None,
        ),
        TestCase(
            name='replicas-string-invalid',
            preconditions=lambda x: x != "-1",
            mutators=lambda x: '-1',
            setup=lambda x: None,
            invalid=True,
        ),
    ]
```

### Apply Built-in Test Generators to More Schemas

You can also apply built-in test generators to a wider range of schemas. For example, the `replicas_tests` test generator only applies to properties of name `replicas`. The following test generator applies the test to `minReplicas` schema as well.

```python
from acto.input.test_generators import test_generator, replicas_tests

@test_generator(property_name='minReplicas')
def extended_replicas_test(schema) -> List[TestCase]:
    return replicas_tests(schema)
```
