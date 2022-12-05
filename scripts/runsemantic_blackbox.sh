#!/bin/bash

# TODO: implement gnu parallel

python3 acto.py --config data/cass-operator/config.json --blackbox --num-workers 16 --num-cases 1 --workdir testrun-cass-semantic --notify-crash
python3 checker.py --config data/cass-operator/config.json --blackbox --num-workers 16 --testrun-dir testrun-cass-semantic
bash scripts/teardown.sh

python3 acto.py --config data/cockroach-operator/config.json --blackbox --num-workers 16 --num-cases 1 --workdir testrun-crdb-semantic --notify-crash
python3 checker.py --config data/cockroach-operator/config.json --blackbox --num-workers 16 --testrun-dir testrun-crdb-semantic
bash scripts/teardown.sh

python3 acto.py --config data/knative-operator-serving/config.json --blackbox --num-workers 16 --num-cases 1 --workdir testrun-knative-serving-semantic --notify-crash
python3 checker.py --config data/knative-operator-serving/config.json --blackbox --num-workers 16 --testrun-dir testrun-knative-serving-semantic
bash scripts/teardown.sh

python3 acto.py --config data/knative-operator-eventing/config.json --blackbox --num-workers 16 --num-cases 1 --workdir testrun-knative-eventing-semantic --notify-crash
python3 checker.py --config data/knative-operator-eventing/config.json --blackbox --num-workers 16 --testrun-dir testrun-knative-eventing-semantic
bash scripts/teardown.sh

python3 acto.py --config data/mongodb-community-operator/config.json --blackbox --num-workers 16 --num-cases 1 --workdir testrun-mongodb-comm-semantic --notify-crash
python3 checker.py --config data/mongodb-community-operator/config.json --blackbox --num-workers 16 --testrun-dir testrun-mongodb-comm-semantic
bash scripts/teardown.sh

python3 acto.py --config data/percona-server-mongodb-operator/config.json --blackbox --num-workers 12 --num-cases 1 --workdir testrun-percona-mongodb-semantic --notify-crash
python3 checker.py --config data/percona-server-mongodb-operator/config.json --blackbox --num-workers 16 --testrun-dir testrun-percona-mongodb-semantic
bash scripts/teardown.sh

python3 acto.py --config data/percona-xtradb-cluster-operator/config.json --blackbox --num-workers 8 --num-cases 1 --workdir testrun-xtradb-semantic --notify-crash
python3 checker.py --config data/percona-xtradb-cluster-operator/config.json --blackbox --num-workers 16 --testrun-dir testrun-xtradb-semantic
bash scripts/teardown.sh

python3 acto.py --config data/rabbitmq-operator/config.json --blackbox --num-workers 16 --num-cases 1 --workdir testrun-rabbitmq-semantic --notify-crash
python3 checker.py --config data/rabbitmq-operator/config.json --blackbox --num-workers 16 --testrun-dir testrun-rabbitmq-semantic
bash scripts/teardown.sh

python3 acto.py --config data/redis-operator/config.json --blackbox --num-workers 16 --num-cases 1 --workdir testrun-redis-semantic --notify-crash
python3 checker.py --config data/redis-operator/config.json --blackbox --num-workers 16 --testrun-dir testrun-redis-semantic
bash scripts/teardown.sh

python3 acto.py --config data/redis-ot-container-kit-operator/config.json --blackbox --num-workers 16 --num-cases 1 --workdir testrun-redis-ot-semantic --notify-crash
python3 checker.py --config data/redis-ot-container-kit-operator/config.json --blackbox --num-workers 16 --testrun-dir testrun-redis-ot-semantic
bash scripts/teardown.sh

python3 acto.py --config data/tidb-operator/config.json --blackbox --num-workers 12 --num-cases 1 --workdir testrun-tidb-semantic --notify-crash
python3 checker.py --config data/tidb-operator/config.json --blackbox --num-workers 16 --testrun-dir testrun-tidb-semantic
bash scripts/teardown.sh

python3 acto.py --config data/zookeeper-operator/config.json --blackbox --num-workers 16 --num-cases 1 --workdir testrun-zk-semantic --notify-crash
python3 checker.py --config data/zookeeper-operator/config.json --blackbox --num-workers 16 --testrun-dir testrun-zk-semantic
bash scripts/teardown.sh

rm -rf testrun-*/images.tar
find testrun-* -maxdepth 0 -exec tar -czf {}.tar.gz {} \;