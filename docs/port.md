# Testing a new operator

## Porting an operator to Acto
To port a new operator to Acto and test it, users would need to create a configuration file in JSON 
  format following the steps below.

### Providing the steps to deploy the operator
The minimum requirement for Acto to test an operator is to provide a way to deploy the operator.

Acto supports three different ways for specifying the deployment method: YAML, Helm, and Kustomize.
  (Helm and Kustomize is lacking support right now, please first use YAML)
To specify operators' deployment method in a YAML way, users need to bundle all the required 
  resources into a YAML file, e.g. Namespace, ClusterRole, ServiceAccount, and Deployment.

Deploying operator can be expressed as a sequence of steps to be applied through
  the `deploy` property.
You would need to specify the Step which contains the operator Deployment resource
    by setting the `operator` property in the `Step` to `true`.

For example, to deploy the cass-operator, we need to first apply the `init.yaml`
  which deploys the cert-manager required by the cass-operator,
  and then apply the `bundle.yaml` which contains all the required resource
  definitions for deploying the cass-operator.
  The `deploy` property would be written as:
```json
"deploy": {
    "steps": [
        {
            "apply": {
                "file": "data/cass-operator/init.yaml",
                "namespace": null
            }
        },
        {
            "wait": {
                "duration": 10
            }
        },
        {
            "apply": {
                "file": "data/cass-operator/bundle.yaml",
                "operator": true
            }
        }
    ]
}
```

In case there are more than one container in the operator Pod (e.g. metrics exporter),
    you would need to specify the actual operator container's name through
    the `operator_container_name` property in the `Step`.

<details>
  <summary>Full JsonSchema for the deploy property</summary>
  
  ```json
"deploy": {
    "additionalProperties": false,
    "description": "Configuration for deploying the operator",
    "properties": {
        "steps": {
            "description": "Steps to deploy the operator",
            "items": {
                "additionalProperties": false,
                "properties": {
                    "apply": {
                        "allOf": [
                            {
                                "additionalProperties": false,
                                "description": "Configuration for each step of kubectl apply",
                                "properties": {
                                    "file": {
                                        "description": "Path to the file for kubectl apply",
                                        "title": "File",
                                        "type": "string"
                                    },
                                    "operator": {
                                        "default": false,
                                        "description": "If the file contains the operator deployment",
                                        "title": "Operator",
                                        "type": "boolean"
                                    },
                                    "operator_container_name": {
                                        "anyOf": [
                                            {
                                                "type": "string"
                                            },
                                            {
                                                "type": "null"
                                            }
                                        ],
                                        "default": null,
                                        "description": "The container name of the operator in the operator pod",
                                        "title": "Operator Container Name"
                                    },
                                    "namespace": {
                                        "anyOf": [
                                            {
                                                "type": "string"
                                            },
                                            {
                                                "type": "null"
                                            }
                                        ],
                                        "default": "__DELEGATED__",
                                        "description": "Namespace for applying the file. If not specified, use the namespace in the file or Acto namespace. If set to null, use the namespace in the file",
                                        "title": "Namespace"
                                    }
                                },
                                "required": [
                                    "file"
                                ],
                                "title": "ApplyStep",
                                "type": "object"
                            }
                        ],
                        "default": null,
                        "description": "Configuration for each step of kubectl apply"
                    },
                    "wait": {
                        "allOf": [
                            {
                                "additionalProperties": false,
                                "description": "Configuration for each step of waiting for the operator",
                                "properties": {
                                    "duration": {
                                        "default": 10,
                                        "description": "Wait for the specified seconds",
                                        "title": "Duration",
                                        "type": "integer"
                                    }
                                },
                                "title": "WaitStep",
                                "type": "object"
                            }
                        ],
                        "default": null,
                        "description": "Configuration for each step of waiting for the operator"
                    }
                },
                "title": "DeployStep",
                "type": "object"
            },
            "minItems": 1,
            "title": "Steps",
            "type": "array"
        }
    },
    "required": [
        "steps"
    ],
    "title": "DeployConfig",
    "type": "object"
},
  ```
</details>

### Providing the name of the CRD to be tested
Only required if the operator defines multiple CRDs.
Some operator developers define separate CRDs for other purposes, e.g., backup tasks to be run.
In case there are more than one CRD in the deploy steps, you need to specify the full name of
    the CRD to be tested.

Specify the name of the CRD to be tested in the configuration through the `crd_name` property. 
E.g.:
```json
{
  "crd_name": "cassandradatacenters.cassandra.datastax.com"
}
```

### Providing a seed CR for Acto to start with
Provide a sample CR which will be used by Acto as the seed. 
This can be any valid CR, usually operator repos contain multiple sample CRs.
Specify this through the `seed_custom_resource` property in the configuration.

For example, cass-operator provides a list of sample CRs in their [repo](https://github.com/k8ssandra/cass-operator/tree/master/config/samples)

Copy one CR into the port directory, and specify the path of the copied CR in the `seed_custom_resource` property

### Providing source code information for whitebox mode (advanced)
Acto supports a whitebox mode to enable more accurate testing by utilizing source code information.
To provide the source code information to Acto, users need to specify the following fields in the port config file:
- `github_link`: the Github link to the operator repo
- `commit`: the commit hash to test
- `entrypoint`: [optional] the location of the operator's main function if it is not at the root
- `type`: the type name of the managed resource (e.g. `CassandraDatacenter` for the rabbitmq's cluster-operator)
- `package`: the package name where the type of the managed resource is defined (e.g. `github.com/k8ssandra/cass-operator/apis/cassandra/v1beta1`)
Acto uses these information to accurately find the type in the source corresponding to the tested CR.

Example:
```json
{
  "analysis": {
      "github_link": "https://github.com/k8ssandra/cass-operator.git",
      "commit": "241e71cdd32bd9f8a7e5c00d5427cdcaf9f55497",
      "entrypoint": null,
      "type": "CassandraDatacenter",
      "package": "github.com/k8ssandra/cass-operator/apis/cassandra/v1beta1"
  }
}
```

## Run Acto's test campaign
After creating the configuration file for the operator,
  users can start the test campaign by invoking Acto:
First run `make` to build the required shared object:
```sh
make
```

Then invoke `acto`
```sh
python3 -m acto
  --config CONFIG, -c CONFIG
                        Operator port config path
  --num-workers NUM_WORKERS
                        Number of concurrent workers to run Acto with
  --workdir WORK_DIR
                        The directory where Acto writes test results
```

Example:
```sh
python3 -m acto --config data/cass-operator/config.json --num-workers 4 --workdir testrun-cass
```

Acto records the runtime information and test result in the workdir.
To focus on the alarms which indicate potential bugs, run
```sh
python3 -m acto.checker.checker --config data/cass-operator/config.json --num-workers 8 --testrun-dir testrun-cass
python3 scripts/feature_results_to_csv.py --testrun-dir testrun-cass
```
It generates the `result.xlsx` file under the `testrun-cass` which contains
  all the oracle results.
You can easily inspect the alarms by importing it into Google Sheet or Excel
  and filter by `alarm==True`.