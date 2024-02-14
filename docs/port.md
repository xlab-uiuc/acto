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
                "description": "A step of deploying a resource",
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
                                        "description": "The container name of the operator in the operator pod, required if there are multiple containers in the operator pod",
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
}
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

<details>
  <summary>Full JsonSchema for the Operator Config</summary>

  ```json
{
    "$defs": {
        "AnalysisConfig": {
            "additionalProperties": false,
            "description": "Configuration for static analysis",
            "properties": {
                "github_link": {
                    "description": "HTTPS URL for cloning the operator repo",
                    "title": "Github Link",
                    "type": "string"
                },
                "commit": {
                    "description": "Commit hash to specify the version to conduct static analysis",
                    "title": "Commit",
                    "type": "string"
                },
                "type": {
                    "description": "Type name of the CR",
                    "title": "Type",
                    "type": "string"
                },
                "package": {
                    "description": "Package name in which the type of the CR is defined",
                    "title": "Package",
                    "type": "string"
                },
                "entrypoint": {
                    "anyOf": [
                        {
                            "type": "string"
                        },
                        {
                            "type": "null"
                        }
                    ],
                    "description": "The relative path of the main package for the operator, required if the main is not in the root directory",
                    "title": "Entrypoint"
                }
            },
            "required": [
                "github_link",
                "commit",
                "type",
                "package",
                "entrypoint"
            ],
            "title": "AnalysisConfig",
            "type": "object"
        },
        "ApplyStep": {
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
                    "description": "The container name of the operator in the operator pod, required if there are multiple containers in the operator pod",
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
        },
        "DeployConfig": {
            "additionalProperties": false,
            "description": "Configuration for deploying the operator",
            "properties": {
                "steps": {
                    "description": "Steps to deploy the operator",
                    "items": {
                        "additionalProperties": false,
                        "description": "A step of deploying a resource",
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
                                                "description": "The container name of the operator in the operator pod, required if there are multiple containers in the operator pod",
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
        "DeployStep": {
            "additionalProperties": false,
            "description": "A step of deploying a resource",
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
                                    "description": "The container name of the operator in the operator pod, required if there are multiple containers in the operator pod",
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
        "KubernetesEngineConfig": {
            "additionalProperties": false,
            "description": "Configuration for Kubernetes",
            "properties": {
                "feature_gates": {
                    "additionalProperties": {
                        "type": "boolean"
                    },
                    "default": null,
                    "description": "Path to the feature gates file",
                    "title": "Feature Gates",
                    "type": "object"
                }
            },
            "title": "KubernetesEngineConfig",
            "type": "object"
        },
        "WaitStep": {
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
    },
    "additionalProperties": false,
    "description": "Configuration for porting operators to Acto",
    "properties": {
        "deploy": {
            "additionalProperties": false,
            "description": "Configuration for deploying the operator",
            "properties": {
                "steps": {
                    "description": "Steps to deploy the operator",
                    "items": {
                        "additionalProperties": false,
                        "description": "A step of deploying a resource",
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
                                                "description": "The container name of the operator in the operator pod, required if there are multiple containers in the operator pod",
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
        "analysis": {
            "anyOf": [
                {
                    "additionalProperties": false,
                    "description": "Configuration for static analysis",
                    "properties": {
                        "github_link": {
                            "description": "HTTPS URL for cloning the operator repo",
                            "title": "Github Link",
                            "type": "string"
                        },
                        "commit": {
                            "description": "Commit hash to specify the version to conduct static analysis",
                            "title": "Commit",
                            "type": "string"
                        },
                        "type": {
                            "description": "Type name of the CR",
                            "title": "Type",
                            "type": "string"
                        },
                        "package": {
                            "description": "Package name in which the type of the CR is defined",
                            "title": "Package",
                            "type": "string"
                        },
                        "entrypoint": {
                            "anyOf": [
                                {
                                    "type": "string"
                                },
                                {
                                    "type": "null"
                                }
                            ],
                            "description": "The relative path of the main package for the operator, required if the main is not in the root directory",
                            "title": "Entrypoint"
                        }
                    },
                    "required": [
                        "github_link",
                        "commit",
                        "type",
                        "package",
                        "entrypoint"
                    ],
                    "title": "AnalysisConfig",
                    "type": "object"
                },
                {
                    "type": "null"
                }
            ],
            "default": null,
            "description": "Configuration for static analysis"
        },
        "seed_custom_resource": {
            "description": "Path to the seed CR file",
            "title": "Seed Custom Resource",
            "type": "string"
        },
        "num_nodes": {
            "default": 4,
            "description": "Number of workers in the Kubernetes cluster",
            "title": "Num Nodes",
            "type": "integer"
        },
        "wait_time": {
            "default": 60,
            "description": "Timeout duration (seconds) for the resettable timer for system convergence",
            "title": "Wait Time",
            "type": "integer"
        },
        "collect_coverage": {
            "default": false,
            "title": "Collect Coverage",
            "type": "boolean"
        },
        "custom_oracle": {
            "anyOf": [
                {
                    "type": "string"
                },
                {
                    "type": "null"
                }
            ],
            "default": null,
            "description": "Path to the custom oracle file",
            "title": "Custom Oracle"
        },
        "diff_ignore_fields": {
            "anyOf": [
                {
                    "items": {
                        "type": "string"
                    },
                    "type": "array"
                },
                {
                    "type": "null"
                }
            ],
            "title": "Diff Ignore Fields"
        },
        "kubernetes_version": {
            "default": "v1.28.0",
            "description": "Kubernetes version",
            "title": "Kubernetes Version",
            "type": "string"
        },
        "kubernetes_engine": {
            "allOf": [
                {
                    "additionalProperties": false,
                    "description": "Configuration for Kubernetes",
                    "properties": {
                        "feature_gates": {
                            "additionalProperties": {
                                "type": "boolean"
                            },
                            "default": null,
                            "description": "Path to the feature gates file",
                            "title": "Feature Gates",
                            "type": "object"
                        }
                    },
                    "title": "KubernetesEngineConfig",
                    "type": "object"
                }
            ],
            "default": {
                "feature_gates": null
            },
            "description": "Configuration for the Kubernetes engine"
        },
        "monkey_patch": {
            "anyOf": [
                {
                    "type": "string"
                },
                {
                    "type": "null"
                }
            ],
            "default": null,
            "description": "Path to the monkey patch file",
            "title": "Monkey Patch"
        },
        "custom_module": {
            "anyOf": [
                {
                    "type": "string"
                },
                {
                    "type": "null"
                }
            ],
            "default": null,
            "description": "Path to the custom module, in the Python module path format",
            "title": "Custom Module"
        },
        "crd_name": {
            "anyOf": [
                {
                    "type": "string"
                },
                {
                    "type": "null"
                }
            ],
            "default": null,
            "description": "Name of the CRD, required if there are multiple CRDs",
            "title": "Crd Name"
        },
        "example_dir": {
            "anyOf": [
                {
                    "type": "string"
                },
                {
                    "type": "null"
                }
            ],
            "default": null,
            "description": "Path to the example dir",
            "title": "Example Dir"
        },
        "context": {
            "anyOf": [
                {
                    "type": "string"
                },
                {
                    "type": "null"
                }
            ],
            "default": null,
            "description": "Path to the context file",
            "title": "Context"
        },
        "focus_fields": {
            "anyOf": [
                {
                    "items": {
                        "items": {
                            "type": "string"
                        },
                        "type": "array"
                    },
                    "type": "array"
                },
                {
                    "type": "null"
                }
            ],
            "default": null,
            "description": "List of focus fields",
            "title": "Focus Fields"
        }
    },
    "required": [
        "deploy",
        "seed_custom_resource"
    ],
    "title": "OperatorConfig",
    "type": "object"
}
  ```

</details>

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

## Interpreting Acto's test result

Acto will first generate a test plan using the operator's CRD and the semantic information.
The test plan is serialized at `testrun-cass/testplan.json` (You don't need to manually inspect the `testplan.json`, it is just to give an overview of the tests going to be run).
Note that Acto does not run the tests according to the order in the `testplan.json`, the tests are run in a random order at runtime.

Acto then constructs the number of Kubernetes clusters according to the `--num-workers` argument,
  and start to run tests.
Tests are run in parallel in separate Kubernetes clusters.
Under the `testrun-cass` directory, Acto creates directories `trial-XX-YYYY`. `XX` corresponds to the worker ID, i.e. `XX` ranges from `0` to `3` if there are 4 workers.
`YYYY` starts from `0000`, and Acto increments `YYYY` every time it has to restart the cluster.
This means every step inside the same `trial-xx-yyyy` directory runs in the same instance of Kubernetes cluster.

Acto takes steps to run the testcases over the previous CR one by one.
One testcase is to change the current CR to provide the next CR to be applied.
Acto starts from the sample CR given from the operator configuration.

At each step, Acto applies a test case over the existing CR to produce the next CR.
It then uses `kubectl apply` to apply the CR in a declarative fashion.
Acto waits for the operator to reconcile the system to match the CR,
    then collects a "snapshot" of the system state at this point of time.
It then runs a collection of oracles(checkers) over the snapshot to detect bugs.
Acto serializes the "snapshot" and the runtime result from the oracles in the `trial-xx-yyyy` directory.

The schema of the "snapshot" is defined at [acto/snapshot.py](../acto/snapshot.py).
It is serialized to the following files:
- `mutated-*.yaml`: These files are the inputs Acto submitted to Kubernetes to run the state transitions. Concretely, Acto first applies `mutated-0.yaml`, and wait for the system to converge, and then applies `mutated-1.yaml`, and so on.
- `cli-output-*.log` and `operator-*.log`: These two files contain the command line result and operator log after submitting the input.
- `system-state-*.json`: After each step submitting `mutated-*.yaml`, Acto collects the system state and store it as `system-state-*.json`. This file contains the serialized state objects from Kubernetes.
- `events-*.log`: This file contains the list of detailed Kubernetes event objects happened after each step.
- `not-ready-pod-*.log`: Acto collects the log from pods which are in `unready` state. This information is helpful for debugging the reason the pod crashed or is unhealthy.

The schema of the runtime result is defined at [acto/result.py](../acto/result.py).
It is serialized to the `generation-XXX-runtime.json` files.
It mainly includes the result from the oracles:
- `crash`: if any container crashed or not
- `health`: if any StatefulSet or Deployment is unhealthy, by comparing the ready replicas in status and desired replicas in spec
- `consistency`: consistency oracle, checking if the desired system state matches the actual system state
- `operator_log`: if the log indicates invalid input
- `custom`: result of custom oracles, defined by users
- `differential`: if the recovery step is successful after the error state
