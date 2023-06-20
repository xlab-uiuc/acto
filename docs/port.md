# Testing a new operator

## Porting
To port a new operator to Acto and test it, users would need to create a configuration file in JSON 
  following the steps below.

### Providing operator deployment script
The minimum requirement for Acto to test an operator is to provide a way to deploy the operator.

Acto supports three different ways for specifying the deployment method: YAML, Helm, and Kustomize.
To specify operators' deployment method in a YAML way, users need to bundle all the required 
  resources into a yaml file, e.g. Namespace, ClusterRole, ServiceAccount, and Deployment.

After aggregating the required resources into a file
Then, specify the deployment in the configuration file through the `deploy` property, e.g.:
```json
{
  "deploy": {
    "method": "YAML",
    "file": "data/cass-operator/bundle.yaml",
    "init": "data/cass-operator/init.yaml"
  }
}
```

### Providing the name of the CRD to be tested
Specify the name of the CRD to be tested in the configuration through the `crd_name` property. Only required if the operator defines multiple CRDs.
E.g.:
```json
{
  "crd_name": "cassandradatacenters.cassandra.datastax.com"
}
```

### Providing a seed CR for Acto to start with
Provide a sample CR which will be used by Acto as the seed. This can be any valid CR, usually operator repos contain multiple sample CRs. Specify this through the `seed_custom_resource` property in the configuration.

### Providing source code information for whitebox mode (optional)
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

## Testing
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