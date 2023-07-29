# Running test campaigns for each operator

We provide the scripts to run the test campaigns for each operator below.

If you are going to run multiple test campaigns serially on one machine, you will have to do the following for a cleanup:

```sh
bash scripts/teardown.sh
```

## [Cassop](https://github.com/k8ssandra/cass-operator)
This script runs the test campaign for the [Cassop](https://github.com/k8ssandra/cass-operator).
This test campaign takes ~10 hours, and the results will be stored at `testrun-cass` directory.
```sh
python3 -m acto \
        --config data/cass-operator/config.json \
        --num-workers 16 \
        --workdir testrun-cass
```

## [CockroachOp](https://github.com/cockroachdb/cockroach-operator)
This script runs the test campaign for the [CockroachOp](https://github.com/cockroachdb/cockroach-operator).
This test campaign takes ~6 hours, and the results will be stored at `testrun-crdb` directory.
```sh
python3 -m acto \
        --config data/cockroach-operator/config.json \
        --num-workers 16 \
        --workdir testrun-crdb
```

## [KnativeOp](https://github.com/knative/operator)
This script runs the test campaigns for the two operators in the [KnativeOp](https://github.com/knative/operator).
The two test campaigns take ~6 hours in total, and the results will be stored separately at `testrun-knative-serving`
    and `testrun-knative-eventing` directories.
```sh
python3 -m acto \
        --config data/knative-operator-serving/config.json \
        --num-workers 16 \
        --workdir testrun-knative-serving
python3 -m acto \
        --config data/knative-operator-eventing/config.json \
        --num-workers 16 \
        --workdir testrun-knative-eventing
```

## [OCK/RedisOp](https://github.com/OT-CONTAINER-KIT/redis-operator)
This script runs the test campaign for the [OCK/RedisOp](https://github.com/OT-CONTAINER-KIT/redis-operator).
This test campaign takes ~6 hours, and the results will be stored at `testrun-redis-ot` directory.
```sh
python3 -m acto \
        --config data/redis-ot-container-kit-operator/config.json \
        --num-workers 16 \
        --workdir testrun-redis-ot
```

## [OFC/MongoOp](https://github.com/mongodb/mongodb-kubernetes-operator)
This script runs the test campaign for the [OFC/MongoOp](https://github.com/mongodb/mongodb-kubernetes-operator).
This test campaign takes ~6 hours, and the results will be stored at `testrun-mongodb-comm` directory.
```sh
python3 -m acto \
        --config data/mongodb-community-operator/config.json \
        --num-workers 16 \
        --workdir testrun-mongodb-comm
```

## [PCN/MongoOp](https://github.com/percona/percona-server-mongodb-operator)
This script runs the test campaign for the [PCN/MongoOp](https://github.com/percona/percona-server-mongodb-operator).
This test campaign takes ~27 hours, and the results will be stored at `testrun-percona-mongodb` directory.
```sh
python3 -m acto \
        --config data/percona-server-mongodb-operator/config.json \
        --num-workers 12 \
        --workdir testrun-percona-mongodb
```

## [RabbitMQOp](https://github.com/rabbitmq/cluster-operator)
This script runs the test campaign for the [RabbitMQOp](https://github.com/rabbitmq/cluster-operator).
This test campaign takes ~5 hours, and the results will be stored at `testrun-rabbitmq` directory.
```sh
python3 -m acto \
        --config data/rabbitmq-operator/config.json \
        --num-workers 16 \
        --workdir testrun-rabbitmq
```

## [SAH/RedisOp](https://github.com/spotahome/redis-operator)
This script runs the test campaign for the [SAH/RedisOp](https://github.com/spotahome/redis-operator).
This test campaign takes ~8 hours, and the results will be stored at `testrun-redis` directory.
```sh
python3 -m acto \
        --config data/redis-operator/config.json \
        --num-workers 16 \
        --workdir testrun-redis
```

## [TiDBOp](https://github.com/pingcap/tidb-operator)
This script runs the test campaign for the [TiDBOp](https://github.com/pingcap/tidb-operator).
This test campaign takes ~16 hours, and the results will be stored at `testrun-tidb` directory.
```sh
python3 -m acto \
        --config data/tidb-operator/config.json \
        --num-workers 12 \
        --workdir testrun-tidb
```

## [XtraDBOp](https://github.com/percona/percona-xtradb-cluster-operator)
This script runs the test campaign for the [XtraDBOp](https://github.com/percona/percona-xtradb-cluster-operator).
This test campaign takes ~58 hours, and the results will be stored at `testrun-xtradb` directory.
```sh
python3 -m acto \
        --config data/percona-xtradb-cluster-operator/config.json \
        --num-workers 8 \
        --workdir testrun-xtradb
```

## [ZooKeeperOp](https://github.com/pravega/zookeeper-operator)
This script runs the test campaign for the [ZooKeeperOp](https://github.com/pravega/zookeeper-operator).
This test campaign takes ~9 hours, and the results will be stored at `testrun-zk` directory.
```sh
python3 -m acto \
        --config data/zookeeper-operator/config.json \
        --num-workers 16 \
        --workdir testrun-zk
```