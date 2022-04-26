# Acto: Automatic, Continuous Testing for (Kubernetes/OpenShift) Operators

## Prerequisites
- Python dependencies
    - `pip3 install -r requirements.txt`
- [k8s Kind cluster](https://kind.sigs.k8s.io/)  
    - For go(1.17+)  
    `go install sigs.k8s.io/kind@v0.11.1`
    - For older version  
    `GO111MODULE="on" go get sigs.k8s.io/kind@v0.11.1`
- kubectl
    - [Installation](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/)

## Usage
To run the test:  
```
python3 acto.py \
    --candidates CANDIDATES, -c CANDIDATES      yaml file to specify candidates for parameters
    --seed SEED, -s SEED                        seed CR file
    --operator OPERATOR, -o OPERATOR            yaml file for deploying the operator
    --helm OPERATOR_CHART                       Path of operator helm chart
    --init INIT                                 Path of init yaml file (deploy before operator)
    --duration DURATION, -d DURATION            Number of hours to run
    --preload-images [PRELOAD_IMAGES [PRELOAD_IMAGES ...]]
                                                Docker images to preload into Kind cluster
    --crd-name CRD_NAME                         Name of CRD to use, required if there are multiple CRDs
    --custom-fields CUSTOM_FIELDS               Python source file containing a list of custom fields
    --context CONTEXT                           Cached context data
    --dryrun DRYRUN                             Only generate test cases without executing them
```

Example:   
**rabbitmq-operator**:  
```console
python3 acto.py --candidates data/rabbitmq-operator/candidates.yaml \
                --seed data/rabbitmq-operator/cr.yaml \
                --operator data/rabbitmq-operator/operator.yaml \
                --custom-fields data.rabbitmq-operator.prune \
                --preload-images rabbitmqoperator/cluster-operator:1.10.0 rabbitmq:3.8.21-management \
                --context data/rabbitmq-operator/context.json \
                --duration 1
```

**cass-operator** (using kustomize)   
```console
python3 acto.py --candidates data/cass-operator/candidates.yaml \
                --seed data/cass-operator/cr.yaml \
                --kustomize "github.com/k8ssandra/cass-operator/config/deployments/cluster?ref=v1.10.3" \
                --init data/cass-operator/init.yaml \
                --custom-fields data.cass-operator.prune \
                --preload-images k8ssandra/cass-operator:v1.10.3 k8ssandra/cass-management-api:3.11.7 k8ssandra/system-logger:v1.10.3 datastax/cass-config-builder:1.0.4-ubi7 quay.io/jetstack/cert-manager-cainjector:v1.7.1 quay.io/jetstack/cert-manager-controller:v1.7.1 quay.io/jetstack/cert-manager-webhook:v1.7.1 docker.io/rancher/local-path-provisioner:v0.0.14 docker.io/kindest/kindnetd:v20211122-a2c10462 \
                --context data/cass-operator/context.json \
                --crd-name cassandradatacenters.cassandra.datastax.com \
                --duration 1
```

zookeeper-operator (using helm)  
`python3 acto.py --candidates data/zookeeper-operator/candidates.yaml --seed data/zookeeper-operator/cr.yaml --helm data/zookeeper-operator/zookeeper-operator --duration 1 --crd-name=zookeeperclusters.zookeeper.pravega.io`

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


## Porting operators
Acto aims to automate the E2E testing as much as possible to minimize users' labor.

Currently, porting operators still requires some manual effort, we need:
1. A way to deploy the operator, the deployment method needs to handle all the necessary prerequisites to deploy the operator, e.g. CRD, namespace creation, RBAC, etc. Current we support three deploy methods: `yaml`, `helm`, and `kustomize`. For example, rabbitmq-operator uses `yaml` for deployment, and the [example is shown here](data/rabbitmq-operator/operator.yaml)
2. A seed CR yaml serving as the initial cr input. This can be any valid CR for your application. [Example](data/rabbitmq-operator/cr.yaml)
3. (Optional) (Not yet supported)A candidates file specifying possible values for some parameters. The candidates file's format is very similar to a CR, except you replace the values with another field `candidates` and specify a list of values under `candidates`. Example:
    ```yaml
    image:
        candidates:
        - "rabbitmq:3.8.21-management"
        - "rabbitmq:latest"
        - "rabbitmq:3.9-management"
        - null
    ```
    A complete example for rabbitmq-operator is [here](data/rabbitmq-operator/candidates.yaml)