# Acto: Automatic, Continuous Testing for (Kubernetes/OpenShift) Operators

## Prerequisites
- Golang
- Python dependencies
    - `pip3 install -r requirements.txt`
- [k8s Kind cluster](https://kind.sigs.k8s.io/)  
    - `go install sigs.k8s.io/kind@v0.14.0`
- kubectl
    - [Installation](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/)
- helm
    - [Installing Helm](https://helm.sh/docs/intro/install/)

## Usage
To run the test:  
```
python3 acto.py \
  --config CONFIG, -c CONFIG
                        Operator port config path
  --duration DURATION, -d DURATION
                        Number of hours to run
  --preload-images [PRELOAD_IMAGES [PRELOAD_IMAGES ...]]
                        Docker images to preload into Kind cluster
  --helper-crd HELPER_CRD
                        generated CRD file that helps with the input generation
  --context CONTEXT     Cached context data
  --num-workers NUM_WORKERS
                        Number of concurrent workers to run Acto with
  --dryrun              Only generate test cases without executing them
```

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
    "seed_custom_resource": "data/rabbitmq-operator/cr.yaml",
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

## Known Issues
- ([A Known Issue of Kind](https://kind.sigs.k8s.io/docs/user/known-issues/#pod-errors-due-to-too-many-open-files)) Failed cluster creation when using the multiple worker functionality by specifying `--num-workers`.

  This may be caused by running out of inotify resources. Resource limits are defined by fs.inotify.max_user_watches and fs.inotify.max_user_instances system variables. For example, in Ubuntu these default to 8192 and 128 respectively, which is not enough to create a cluster with many nodes.
  
  To increase these limits temporarily, run the following commands on the host:
  ```shell
  sudo sysctl fs.inotify.max_user_watches=524288
  sudo sysctl fs.inotify.max_user_instances=512
  ```
  To make the changes persistent, edit the file /etc/sysctl.conf and add these lines:
  ```shell
  fs.inotify.max_user_watches = 524288
  fs.inotify.max_user_instances = 512
  ```

## Example:   
**rabbitmq-operator**:  
```console
python3 acto.py --seed data/rabbitmq-operator/config.json
                --num-workers 4
```

## Porting operators
Acto aims to automate the E2E testing as much as possible to minimize users' labor.

Currently, porting operators still requires some manual effort, we need:
1. A way to deploy the operator, the deployment method needs to handle all the necessary prerequisites to deploy the operator, e.g. CRD, namespace creation, RBAC, etc. Current we support three deploy methods: `yaml`, `helm`, and `kustomize`. For example, rabbitmq-operator uses `yaml` for deployment, and the [example is shown here](data/rabbitmq-operator/operator.yaml)
2. A seed CR yaml serving as the initial cr input. This can be any valid CR for your application. [Example](data/rabbitmq-operator/cr.yaml)

## Known Limitations 
* https://github.com/xlab-uiuc/acto/issues/121
* https://github.com/xlab-uiuc/acto/issues/120

## Next Steps 
* https://github.com/xlab-uiuc/acto/issues/131
