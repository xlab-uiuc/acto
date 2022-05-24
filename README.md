# Acto: Automatic, Continuous Testing for (Kubernetes/OpenShift) Operators

## Prerequisites
- Golang
- Python dependencies
    - `pip3 install -r requirements.txt`
- [k8s Kind cluster](https://kind.sigs.k8s.io/)  
    `go install sigs.k8s.io/kind@v0.11.1`
- kubectl
    - [Installation](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/)
- helm
    - [Installing Helm](https://helm.sh/docs/intro/install/)

## Usage
To run the test:  
```
python3 acto.py \
    --seed SEED, -s SEED                    seed CR file
    --operator OPERATOR, -o OPERATOR        yaml file for deploying the operator with kubectl
    --helm OPERATOR_CHART                   Path of operator helm chart
    --kustomize KUSTOMIZE                   Path of folder with kustomize
    --init INIT                             Path of init yaml file (deploy before operator)
    --duration DURATION, -d DURATION        Number of hours to run
    --preload-images [PRELOAD_IMAGES [PRELOAD_IMAGES ...]]
                                            Docker images to preload into Kind cluster
    --crd-name CRD_NAME                     Name of CRD to use, required if there are multiple CRDs
    --helper-crd HELPER_CRD                 generated CRD file that helps with the input generation
    --custom-fields CUSTOM_FIELDS           Python source file containing a list of custom fields
    --context CONTEXT                       Cached context data
    --dryrun                                Only generate test cases without executing them
```

Example:   
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

## Porting operators
Acto aims to automate the E2E testing as much as possible to minimize users' labor.

Currently, porting operators still requires some manual effort, we need:
1. A way to deploy the operator, the deployment method needs to handle all the necessary prerequisites to deploy the operator, e.g. CRD, namespace creation, RBAC, etc. Current we support three deploy methods: `yaml`, `helm`, and `kustomize`. For example, rabbitmq-operator uses `yaml` for deployment, and the [example is shown here](data/rabbitmq-operator/operator.yaml)
2. A seed CR yaml serving as the initial cr input. This can be any valid CR for your application. [Example](data/rabbitmq-operator/cr.yaml)
