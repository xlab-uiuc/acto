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

Copy one CR into the port directory, and specify the path of the copied CR in the `seed_custom_resource` property.

**Important** Please specify the `metadata.name` as `test-cluster` in the CR YAML.

### Extending and customizing Acto
Please refer to [https://github.com/xlab-uiuc/acto/blob/main/docs/test_generator.md](https://github.com/xlab-uiuc/acto/blob/main/docs/test_generator.md)


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

Hold your horses, before launching a full test campaign, you may want to validate that your operator config. You wouldn’t want to run Acto for overnight and realize the operator was crashing all the time.

### Run the “learn” phase of Acto

Acto has a pre-flight “learn” phase, which does some first-time information collection and checking.

To only run the “learn” phase:

```bash
python3 -m acto --config CONFIG --learn
```

It does the following tasks:

1. Create a “learn” Kubernetes cluster
2. Parse the Operator deployment steps to figure out which namespace the operator is deployed to.
3. Deploy the Operator according to the Deploy section of the operator config.
4. Get the CRD from the Kubernetes cluster, which should be created at step 3.
5. Deploy the CR.
6. Inspect the Kubernetes nodes to get the list of images being used. These images will be preloaded to the Kubernetes nodes during the test campaign to avoid the Docker’s pull rate limit.
7. Conduct pre-flight checking to make sure the system state is at least healthy. It also checks whether the pods have “IfNotPresent” as the ImagePullPolicy.

At the end, it produces a `context.json` file in the same directory with the seed CR. The context.json file will be used for the actual test campaign, so that the above “learn” phase is only one-time effort.

### Kick-off Acto’s Test Campaign

Now you are all set to test your operator!
Invoke `acto`
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

### Babysitting Acto

Acto is still a research prototype, and it is very likely to have problems when being applied to different operators.

Since the testing usually takes hours, it is recommended to monitor Acto’s log at the beginning to make sure it does not crash (to avoid the bad experience where you waited for one day to check the result, and realize that Acto crashed after 10 mins after starting). When Acto crashes, it dumps the stacktrace with all the local variable values. Acto prints log at `CRTICIAL` level when it crashes. To check whether Acto has crashed, simply do a keyword search of `CRITICAL` in Acto’s log.

Acto writes the test log to `{WORKDIR}/test.log` . If you did not specify the `--workdir` command line argument, `{WORKDIR}` would be `testrun-{TIMESTAMP` in the current directory.

## Interpreting Acto's test result

Acto will first generate a test plan using the operator's CRD and the semantic information. The test plan is serialized at `testrun-cass/testplan.json` (You don't need to manually inspect the `testplan.json`, it is just to give an overview of the tests going to be run). Note that Acto does not run the tests according to the order in the `testplan.json`, the tests are run in a random order at runtime.

Acto then constructs the number of Kubernetes clusters according to the `--num-workers` argument, and start to run tests. Tests are run in parallel in separate Kubernetes clusters. Under the `testrun-cass` directory, Acto creates directories `trial-XX-YYYY`. `XX` corresponds to the worker ID, i.e. `XX` ranges from `0` to `3` if there are 4 workers. `YYYY` starts from `0000`, and Acto increments `YYYY` every time it has to restart the cluster. This means every step inside the same `trial-xx-yyyy` directory runs in the same instance of Kubernetes cluster.

Acto takes steps to run the testcases over the previous CR one by one. One testcase is to change the current CR to provide the next CR to be applied. Acto starts from the sample CR given from the operator configuration.

At each step, Acto applies a test case over the existing CR to produce the next CR. It then uses `kubectl apply` to apply the CR in a declarative fashion. Acto waits for the operator to reconcile the system to match the CR, then collects a "snapshot" of the system state at this point of time. It then runs a collection of oracles(checkers) over the snapshot to detect bugs. Acto serializes the "snapshot" and the runtime result from the oracles in the `trial-xx-yyyy` directory.

The schema of the "snapshot" is defined at [acto/snapshot.py](https://github.com/xlab-uiuc/acto/blob/main/acto/snapshot.py). It is serialized to the following files:

- `mutated-*.yaml`: These files are the inputs Acto submitted to Kubernetes to run the state transitions. Concretely, Acto first applies `mutated-0.yaml`, and wait for the system to converge, and then applies `mutated-1.yaml`, and so on.
- `cli-output-*.log` and `operator-*.log`: These two files contain the command line result and operator log after submitting the input.
- `system-state-*.json`: After each step submitting `mutated-*.yaml`, Acto collects the system state and store it as `system-state-*.json`. This file contains the serialized state objects from Kubernetes.
- `events-*.log`: This file contains the list of detailed Kubernetes event objects happened after each step.
- `not-ready-pod-*.log`: Acto collects the log from pods which are in `unready` state. This information is helpful for debugging the reason the pod crashed or is unhealthy.

The schema of the runtime result is defined at [acto/result.py](https://github.com/xlab-uiuc/acto/blob/main/acto/result.py). It is serialized to the `generation-XXX-runtime.json` files. It mainly includes the result from the oracles:

- `crash`: if any container crashed or not
- `health`: if any StatefulSet or Deployment is unhealthy, by comparing the ready replicas in status and desired replicas in spec
- `consistency`: consistency oracle, checking if the desired system state matches the actual system state
- `operator_log`: if the log indicates invalid input
- `custom`: result of custom oracles, defined by users
- `differential`: if the recovery step is successful after the error state

### Gathering Test Results

After Acto finishes all the tests, you can use the following script to collect all the test results into a .csv file and inspect them in Google Sheet.

Run the following command in the Acto repo, it will produce a csv file under the testrun directory(workdir).
```sh
python3 -m acto.post_process.collect_test_result --config OPERATOR_CONFIG --testrun-dir TESTRUN_DIR
```

Usage documentation:
```sh
usage: collect_test_result.py [-h] --config CONFIG --testrun-dir TESTRUN_DIR

Collect all test results into a CSV file for analysis.

options:
  -h, --help            show this help message and exit
  --config CONFIG       Path to the operator config file
  --testrun-dir TESTRUN_DIR
                        Path to the testrun dir which contains the testing result
```

## FAQ
Please refer to [FAQ](./FAQ.md) for frequently asked questions.
### Example of A True Alarm

Let’s take a look at one example how we analyzed one alarm produced by Acto and found the https://github.com/k8ssandra/cass-operator/issues/330

You can find the trial which produced the result [here](alarm_examples/true_alarm/), and the alarm is raise inside [this file](alarm_examples/true_alarm/generation-002-runtime.json)

Inside the [generation-002-runtime.json](alarm_examples/true_alarm/generation-002-runtime.json), you can find the following the alarm:

```json
"consistency": {
    "message": "Found no matching fields for input",
    "input_diff": {
        "prev": "ACTOKEY",
        "curr": "NotPresent",
        "path": {
            "path": [
                "spec",
                "additionalServiceConfig",
                "seedService",
                "additionalLabels",
                "ACTOKEY"
            ]
        }
    },
    "system_state_diff": null
},
```

This shows that the alarm is raised by Acto’s consistency oracle. In the alarm description, you can see three fields: `message`, `input_diff`, and `system_state_diff`. In the `input_diff`, it shows the following information:

- In this step, Acto changed the property of path `spec.additionalServiceConfig.seedService.additionalLabels.ACTOKEY` from `ACTOKEY` to `NotPresent`. This basically means that Acto deleted the `spec.additionalServiceConfig.seedService.additionalLabels.ACTOKEY` from the CR.
- Acto checked through the system state change, and could not find a matching change.

To look deeper into this alarm, we can check the [delta-002.log](alarm_examples/true_alarm/delta-002.log) file. The `delta-002.log` file contains two sections: `INPUT DELTA` and `SYSTEM DELTA`. In the `INPUT DELTA`, you can see the diff from the `mutated-001.yaml` to `mutated-002.yaml`. In the `SYSTEM DELTA`, you can see the diff from `system-state-001.json` to `system-state-002.json`. You can also view the `mutated-*.yaml` and `system-state-*.json` files directly to see the full CR or full states.

These files tell us the behavior of the operator when reacting to the CR transition. Next, we need to understand why the operator behaves in this way. We need to look into the operator source code to understand the behavior.

The operator codebase may be large, so we need to pinpoint the subset of the operator source code which is related to the `spec.additionalServiceConfig.seedService.additionalLabels.ACTOKEY` property.

We first need to find the places in the source code which reference the property.

- We can find the type definition for the property at [https://github.com/k8ssandra/cass-operator/blob/9d320dd1960706adb092541a2dc30f186a76338e/apis/cassandra/v1beta1/cassandradatacenter_types.go#L342.](https://github.com/k8ssandra/cass-operator/blob/53c637c22f0d5f1e2f4c09156591a47f7919e0b5/apis/cassandra/v1beta1/cassandradatacenter_types.go#L299)
- Then we trace through the code to find the uses of this field, and eventually we arrive at this line: [https://github.com/k8ssandra/cass-operator/blob/9d320dd1960706adb092541a2dc30f186a76338e/pkg/reconciliation/construct_service.go#L91.](https://github.com/k8ssandra/cass-operator/blob/53c637c22f0d5f1e2f4c09156591a47f7919e0b5/pkg/reconciliation/construct_service.go#L90)
- Tracing backward to see how the returned values are used, we arrive at this line: https://github.com/k8ssandra/cass-operator/blob/53c637c22f0d5f1e2f4c09156591a47f7919e0b5/pkg/reconciliation/reconcile_services.go#L59.
- We can see that the operator always merge the existing annotations with the annotations specified in the CR. This “merge” behavior causes the old annotations to be never deleted: https://github.com/k8ssandra/cass-operator/blob/53c637c22f0d5f1e2f4c09156591a47f7919e0b5/pkg/reconciliation/reconcile_services.go#L104.

### Example of Misoperation

Let’s take a look at one example of an alarm caused by a misoperation vulnerability in the tidb-operator. A misoperation vulnerability means that the operator failed to reject an erroneous desired state, and caused the system to be in an error state.

You can look at the example alarm [here](alarm_examples/misoperation/)

Inside the [alarm file](alarm_examples/misoperation/generation-001-runtime.json), you can find the following alarm message:

```json
"health": {
    "message": "statefulset: test-cluster-tidb replicas [3] ready_replicas [2]"
},
```

This shows the alarm is raised by the health oracle, which checks if the Kubernetes resources have desired number of replicas. In this alarm, Acto found that the StatefulSet object named `test-cluster-tidb` only has two ready replicas, whereas the desired number of replicas is three.

To find out what happened, we can take a look at the [delta-001.log](alarm_examples/misoperation/delta-001.log) . It tells us that from the previous step, Acto added an Affinity rule to the tidb’s CR. And in the system state, the tidb-2 pod is recreated with the Affinity rule.

Next, we need to figure out why the tidb-2 pod is recreated, but cannot be scheduled. After taking a look at the [events-001.json](alarm_examples/misoperation/events-001.json) file, we can find an error event issued by the `Pod` with the message: `"0/4 nodes are available: 1 node(s) had untolerated taint {node-role.kubernetes.io/control-plane: }, 3 node(s) didn't match Pod's node affinity/selector. preemption: 0/4 nodes are available: 4 Preemption is not helpful for scheduling.."` indicating that the new Pod cannot be properly scheduled to nodes.

The root cause is because the desired Affinity specified in the TiDB CR cannot be satisfied in the current cluster state. The tidb-operator fails to reject the erroneous desired state, updates the TiDB cluster with the unsatisfiable Affinity rule, causing the cluster to lose one replica.

### Example of False Alarm

Acto’s oracles are not sound, meaning that Acto may report an alarm, but the operator’s behavior is correct. [Here](alarm_examples/false_alarm/) is an example of false alarms produced by Acto.

Looking at the [generation-002-runtime.json](alarm_examples/false_alarm/generation-002-runtime.json), you can find the following error message from the consistency oracle:

```json
"oracle_result": {
    "crash": null,
    "health": null,
    "operator_log": null,
    "consistency": {
        "message": "Found no matching fields for input",
        "input_diff": {
            "prev": "1Gi",
            "curr": "2Gi",
            "path": {
                "path": [
                    "spec",
                    "ephemeral",
                    "emptydirvolumesource",
                    "sizeLimit"
                ]
            }
        },
        "system_state_diff": null
    },
    "differential": null,
    "custom": null
},
```

This indicates that Acto expects a corresponding system state change for the input delta of path `spec.ephemeral.emptydirvolumesource.sizeLimit`. To understand the operator’s behavior, we trace through the operator source. We can see that the property has a control-flow dependency on another property: https://github.com/pravega/zookeeper-operator/blob/9fc6151757018cd99acd7b73c24870dce24ba3d5/pkg/zk/generators.go#L48C1-L52C54. And in the CR generated by Acto, the property `spec.storageType` is set to `persistent` instead of `ephemeral`.

This alarm is thus a false alarm. The operator’s behavior is correct. It did not update the system state because the storageType is not set to `ephemeral`. Acto raised this alarm because it fails to recognize the control-flow dependency among the properties `spec.ephemeral.emptydirvolumesource.sizeLimit` and `spec.storageType`.
