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
        "method": "YAML",  // Three deploy methods [YAML HELM KUSTOMIZE]
        "file": "data/rabbitmq-operator/operator.yaml",  // the deployment file
        "init": null  // any yaml to deploy for deploying the operator itself
    },
    "crd_name": null,  // name of the CRD to test, optional if there is only one CRD
    "custom_fields": "data.rabbitmq-operator.prune",  // to guide the pruning
    "seed_custom_resource": "data/rabbitmq-operator/cr.yaml",  // the seed CR file
    "analysis": {
        "github_link": "https://github.com/rabbitmq/cluster-operator.git",  // github link for the operator repo
        "commit": "f2ab5cecca7fa4bbba62ba084bfa4ae1b25d15ff",  // specific commit hash of the repo
        "type": "RabbitmqCluster",  // the root type of the CR
        "package": "github.com/rabbitmq/cluster-operator/api/v1beta1"  // package of the root type
    }
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
python3 acto.py --seed data/rabbitmq-operator/cr.yaml \
                --operator data/rabbitmq-operator/operator.yaml \
                --custom-fields data.rabbitmq-operator.prune \
                --context data/rabbitmq-operator/context.json
```

**cass-operator** (using kustomize)   
```console
python3 acto.py --seed data/cass-operator/cr.yaml \
                --kustomize "github.com/k8ssandra/cass-operator/config/deployments/cluster?ref=v1.10.3" \
                --init data/cass-operator/init.yaml \
                --custom-fields data.cass-operator.prune \
                --context data/cass-operator/context.json \
                --crd-name cassandradatacenters.cassandra.datastax.com
```

zookeeper-operator (using helm)  
```console
python3 acto.py --seed data/zookeeper-operator/cr.yaml \
                --helm data/zookeeper-operator/zookeeper-operator \
                --crd-name=zookeeperclusters.zookeeper.pravega.io
```

**mongodb-operator** (using kubectl)
```console
python3 acto.py --seed data/percona-server-mongodb-operator/cr.yaml \
                --operator data/percona-server-mongodb-operator/bundle.yaml \
                --context data/percona-server-mongodb-operator/context.json \
                --crd-name perconaservermongodbs.psmdb.percona.com \
                --custom-fields data.percona-server-mongodb-operator.prune
```

casskop-operator (using helm)
`python3 acto.py --candidates data/casskop-operator/candidates.yaml --seed data/casskop-operator/cr.yaml --helm data/casskop-operator/cassandra-operator --init data/casskop-operator/init.yaml --duration 1 --crd-name=cassandraclusters.db.orange.com`

nifikop-operator (using helm)
`python3 acto.py --candidates data/nifikop-operator/candidates.yaml --seed data/nifikop-operator/cr.yaml --helm data/nifikop-operator/nifikop-operator  --duration 1 --crd-name=nificlusters.nifi.orange.com`

xtradb-operator (using helm)
`python3 acto.py --candidates data/xtradb-operator/candidates.yaml --seed data/xtradb-operator/cr.yaml --helm data/xtradb-operator/xtradb-operator  --duration 1 --crd-name=perconaxtradbclusters.pxc.percona.com`

**redis-operator**
```console
python3 acto.py --seed data/redis-operator/cr.yaml \
                --operator data/redis-operator/all-redis-operator-resources.yaml \
                --init data/redis-operator/databases.spotahome.com_redisfailovers.yaml \
                --preload-images quay.io/spotahome/redis-operator:v1.1.0 redis:6.2.6-alpine \
                --context data/redis-operator/context.json \
                --custom-fields data.redis-operator.prune \
                --duration 1
```

**tidb-operator**
```
python3 acto.py --seed data/tidb-operator/cr.yaml \
                --helm data/tidb-operator/tidb-operator \
                --init data/tidb-operator/crd.yaml \
                --context data/tidb-operator/context.json \
                --custom-fields data.tidb-operator.prune \
                --crd-name tidbclusters.pingcap.com \
                --duration 1
```

**spark-operator**
```
python3 acto.py --seed data/spark-operator/cr.yaml \
                --helm data/spark-operator/spark-operator-chart --crd-name=sparkapplications.sparkoperator.k8s.io
```

**ot-container-kit/redis-operator**
```
python3 acto.py --seed data/redis-ot-container-kit-operator/cr_cluster.yaml \
                --operator data/redis-ot-container-kit-operator/bundle.yaml \
                --crd-name redisclusters.redis.redis.opstreelabs.in  \               
                --custom-fields data.redis-ot-container-kit-operator.prune \
```

**percona-xtradb-cluster-operator**
```
python3 acto.py --seed data/percona-xtradb-cluster-operator/cr.yaml \
                --operator data/percona-xtradb-cluster-operator/cw-bundle.yaml \
                --crd-name perconaxtradbclusters.pxc.percona.com \
                --custom-fields data.percona-xtradb-cluster-operator.prune
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
