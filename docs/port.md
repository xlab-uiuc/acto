## Operator config example
```json
{
    "deploy": {
        "method": "YAML",
        "file": "data/rabbitmq-operator/operator.yaml",
        "init": null
    },
    "crd_name": null,
    "custom_fields": "data.rabbitmq-operator.prune",
    "blackbox_custom_fields": "data.rabbitmq-operator.prune_blackbox",
    "k8s_fields": "data.rabbitmq-operator.k8s_mapping",
    "seed_custom_resource": "data/rabbitmq-operator/cr.yaml",
    "example_dir": "data/rabbitmq-operator/examples",
    "analysis": {
        "github_link": "https://github.com/rabbitmq/cluster-operator.git",
        "commit": "f2ab5cecca7fa4bbba62ba084bfa4ae1b25d15ff",
        "entrypoint": null,
        "type": "RabbitmqCluster",
        "package": "github.com/rabbitmq/cluster-operator/api/v1beta1"
    }
}
```

## JSON schema for writing the operator porting config
```json
{
  "$schema": "http://json-schema.org/draft-04/schema#",
  "type": "object",
  "properties": {
    "deploy": {
      "type": "object",
      "properties": {
        "method": {
          "description": "One of three deploy methods [YAML HELM KUSTOMIZE]",
          "type": "string"
        },
        "file": {
          "description": "the deployment file",
          "type": "string"
        },
        "init": {
          "description": "any yaml to deploy for deploying the operator itself",
          "type": "string"
        }
      },
      "required": [
        "method",
        "file",
        "init"
      ]
    },
    "crd_name": {
      "description": "name of the CRD to test, optional if there is only one CRD",
      "type": "string"
    },
    "custom_fields": {
      "description": "file to guide the pruning",
      "type": "string"
    },
    "seed_custom_resource": {
      "description": "the seed CR file",
      "type": "string"
    },
    "analysis": {
      "type": "object",
      "properties": {
        "github_link": {
          "description": "github link for the operator repo",
          "type": "string"
        },
        "commit": {
          "description": "specific commit hash of the repo",
          "type": "string"
        },
        "entrypoint": {
          "description": "directory of the main file",
          "type": "string"
        },
        "type": {
          "description": "the root type of the CR",
          "type": "string"
        },
        "package": {
          "description": "package of the root type",
          "type": "string"
        }
      },
      "required": [
        "github_link",
        "commit",
        "entrypoint",
        "type",
        "package"
      ]
    }
  },
  "required": [
    "deploy",
    "crd_name",
    "custom_fields",
    "seed_custom_resource",
    "analysis"
  ]
}
```