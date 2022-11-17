#!/bin/bash

# TODO: implement gnu parallel

python3 acto.py --config data/cass-operator/config.json --num-workers 16 --num-cases 1 --workdir testrun-cass --notify-crash
python3 checker.py --config data/cass-operator/config.json --num-workers 16 --testrun-dir testrun-cass
bash scripts/teardown.sh

python3 acto.py --config data/cockroach-operator/config.json --num-workers 16 --num-cases 1 --workdir testrun-crdb --notify-crash
python3 checker.py --config data/cockroach-operator/config.json --num-workers 16 --testrun-dir testrun-crdb
bash scripts/teardown.sh

python3 acto.py --config data/knative-operator-serving/config.json --enable-analysis --num-workers 16 --num-cases 1 --workdir testrun-knative-serving --notify-crash
python3 checker.py --config data/knative-operator-serving/config.json --num-workers 16 --testrun-dir testrun-crdb
bash scripts/teardown.sh

python3 acto.py --config data/knative-operator-eventing/config.json --enable-analysis --num-workers 16 --num-cases 1 --workdir testrun-knative-eventing --notify-crash
python3 checker.py --config data/knative-operator-eventing/config.json --num-workers 16 --testrun-dir testrun-crdb
bash scripts/teardown.sh

python3 acto.py --config data/mongodb-community-operator/config.json --num-workers 16 --num-cases 1 --workdir testrun-mongodb-comm --notify-crash
python3 checker.py --config data/mongodb-community-operator/config.json --num-workers 16 --testrun-dir testrun-mongodb-comm
bash scripts/teardown.sh

python3 acto.py --config data/percona-server-mongodb-operator/config.json --num-workers 12 --num-cases 1 --workdir testrun-percona-mongodb --notify-crash
python3 checker.py --config data/percona-server-mongodb-operator/config.json --num-workers 16 --testrun-dir testrun-percona-mongodb
bash scripts/teardown.sh

python3 acto.py --config data/percona-xtradb-cluster-operator/config.json --num-workers 8 --num-cases 1 --workdir testrun-xtradb --notify-crash
python3 checker.py --config data/percona-xtradb-cluster-operator/config.json --num-workers 16 --testrun-dir testrun-xtradb
bash scripts/teardown.sh

python3 acto.py --config data/rabbitmq-operator/config.json --num-workers 16 --num-cases 1 --workdir testrun-rabbitmq --notify-crash
python3 checker.py --config data/rabbitmq-operator/config.json --num-workers 16 --testrun-dir testrun-rabbitmq
bash scripts/teardown.sh

python3 acto.py --config data/redis-operator/config.json --num-workers 16 --num-cases 1 --workdir testrun-redis --notify-crash
python3 checker.py --config data/redis-operator/config.json --num-workers 16 --testrun-dir testrun-redis
bash scripts/teardown.sh

python3 acto.py --config data/redis-ot-container-kit-operator/config.json --num-workers 16 --num-cases 1 --workdir testrun-redis-ot --notify-crash
python3 checker.py --config data/redis-ot-container-kit-operator/config.json --num-workers 16 --testrun-dir testrun-redis-ot
bash scripts/teardown.sh

python3 acto.py --config data/tidb-operator/config.json --num-workers 12 --num-cases 1 --workdir testrun-tidb --notify-crash
python3 checker.py --config data/tidb-operator/config.json --num-workers 16 --testrun-dir testrun-tidb
bash scripts/teardown.sh

python3 acto.py --config data/zookeeper-operator/config.json --num-workers 16 --num-cases 1 --workdir testrun-zk --notify-crash
python3 checker.py --config data/zookeeper-operator/config.json --num-workers 16 --testrun-dir testrun-zk
bash scripts/teardown.sh

rm -rf testrun-*/images.tar
find testrun-* -maxdepth 0 -exec tar -czf {}.tar.gz {} \;