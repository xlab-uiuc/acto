python3 acto.py --config data/cass-operator/config.json --delta-from acto-data/cass-operator/testrun-cass-blackbox/ --num-workers 16 --num-cases 1 --workdir testrun-cass-whitebox --notify-crash
cp -r acto-data/cass-operator/testrun-cass-blackbox/trial-* testrun-cass-whitebox/
bash scripts/teardown.sh
python3 checker.py --config data/cass-operator/config.json --num-workers 64 --testrun-dir testrun-cass-whitebox

python3 acto.py --config data/cockroach-operator/config.json --delta-from acto-data/cockroach-operator/testrun-crdb-blackbox/ --num-workers 16 --num-cases 1 --workdir testrun-crdb-whitebox --notify-crash
cp -r acto-data/cockroach-operator/testrun-crdb-blackbox/trial-* testrun-crdb-whitebox/
bash scripts/teardown.sh
python3 checker.py --config data/cockroach-operator/config.json --num-workers 64 --testrun-dir testrun-crdb-whitebox

python3 acto.py --config data/knative-operator-eventing/config.json --delta-from acto-data/knative-operator-eventing/testrun-knative-eventing-blackbox/ --num-workers 16 --num-cases 1 --workdir testrun-knative-eventing-whitebox --notify-crash
cp -r acto-data/knative-operator-eventing/testrun-knative-eventing-blackbox/trial-* testrun-knative-eventing-whitebox/
bash scripts/teardown.sh
python3 checker.py --config data/knative-operator-eventing/config.json --num-workers 64 --testrun-dir testrun-knative-eventing-whitebox

python3 acto.py --config data/knative-operator-serving/config.json --delta-from acto-data/knative-operator-serving/testrun-knative-serving-blackbox/ --num-workers 16 --num-cases 1 --workdir testrun-knative-serving-whitebox --notify-crash
cp -r acto-data/knative-operator-serving/testrun-knative-serving-blackbox/trial-* testrun-knative-serving-whitebox/
bash scripts/teardown.sh
python3 checker.py --config data/knative-operator-serving/config.json --num-workers 64 --testrun-dir testrun-knative-serving-whitebox

python3 acto.py --config data/percona-server-mongodb-operator/config.json --delta-from acto-data/percona-server-mongodb-operator/testrun-percona-mongodb-blackbox/ --num-workers 16 --num-cases 1 --workdir testrun-percona-mongodb-whitebox --notify-crash
cp -r acto-data/percona-server-mongodb-operator/testrun-percona-mongodb-blackbox/trial-* testrun-percona-mongodb-whitebox/
bash scripts/teardown.sh
python3 checker.py --config data/percona-server-mongodb-operator/config.json --num-workers 64 --testrun-dir testrun-percona-mongodb-whitebox

python3 acto.py --config data/percona-xtradb-cluster-operator/config.json --delta-from acto-data/percona-xtradb-cluster-operator/testrun-xtradb-blackbox/ --num-workers 16 --num-cases 1 --workdir testrun-xtradb-whitebox --notify-crash
cp -r acto-data/percona-xtradb-cluster-operator/testrun-xtradb-blackbox/trial-* testrun-xtradb-whitebox/
bash scripts/teardown.sh
python3 checker.py --config data/percona-xtradb-cluster-operator/config.json --num-workers 64 --testrun-dir testrun-xtradb-whitebox

python3 acto.py --config data/rabbitmq-operator/config.json --delta-from acto-data/rabbitmq-operator/testrun-rabbitmq-blackbox/ --num-workers 16 --num-cases 1 --workdir testrun-rabbitmq-whitebox --notify-crash
cp -r acto-data/rabbitmq-operator/testrun-rabbitmq-blackbox/trial-* testrun-rabbitmq-whitebox/
bash scripts/teardown.sh
python3 checker.py --config data/rabbitmq-operator/config.json --num-workers 64 --testrun-dir testrun-rabbitmq-whitebox

python3 acto.py --config data/redis-operator/config.json --delta-from acto-data/redis-operator/testrun-redis-blackbox/ --num-workers 16 --num-cases 1 --workdir testrun-redis-whitebox --notify-crash
cp -r acto-data/redis-operator/testrun-redis-blackbox/trial-* testrun-redis-whitebox/
bash scripts/teardown.sh
python3 checker.py --config data/redis-operator/config.json --num-workers 64 --testrun-dir testrun-redis-whitebox

python3 acto.py --config data/redis-ot-container-kit-operator/config.json --delta-from acto-data/redis-ot-container-kit-operator/testrun-redis-ot-blackbox/ --num-workers 16 --num-cases 1 --workdir testrun-redis-ot-whitebox --notify-crash
cp -r acto-data/redis-ot-container-kit-operator/testrun-redis-ot-blackbox/trial-* testrun-redis-ot-whitebox/
bash scripts/teardown.sh
python3 checker.py --config data/redis-ot-container-kit-operator/config.json --num-workers 64 --testrun-dir testrun-redis-ot-whitebox

python3 acto.py --config data/tidb-operator/config.json --delta-from acto-data/tidb-operator/testrun-tidb-blackbox/ --num-workers 16 --num-cases 1 --workdir testrun-tidb-whitebox --notify-crash
cp -r acto-data/tidb-operator/testrun-tidb-blackbox/trial-* testrun-tidb-whitebox/
bash scripts/teardown.sh
python3 checker.py --config data/tidb-operator/config.json --num-workers 64 --testrun-dir testrun-tidb-whitebox

python3 acto.py --config data/zookeeper-operator/config.json --delta-from acto-data/zookeeper-operator/testrun-zk-blackbox/ --num-workers 16 --num-cases 1 --workdir testrun-zk-whitebox --notify-crash
cp -r acto-data/zookeeper-operator/testrun-zk-blackbox/trial-* testrun-zk-whitebox/
bash scripts/teardown.sh
python3 checker.py --config data/zookeeper-operator/config.json --num-workers 64 --testrun-dir testrun-zk-whitebox

rm -rf testrun-*/images.tar
find testrun-* -maxdepth 0 -exec tar -czf {}.tar.gz {} \;