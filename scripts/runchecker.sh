python3 checker.py --config data/cass-operator/config.json --num-workers 16 --testrun-dir /home/tyler/acto-data/gen6/testrun-cass-whitebox
python3 scripts/feature_results_to_csv.py --testrun-dir /home/tyler/acto-data/gen6/testrun-cass-whitebox

python3 checker.py --config data/cockroachdb-operator/config.json --num-workers 16 --testrun-dir /home/tyler/acto-data/gen6/testrun-crdb-whitebox
python3 scripts/feature_results_to_csv.py --testrun-dir /home/tyler/acto-data/gen6/testrun-crdb-whitebox

python3 checker.py --config data/knative-operator-serving/config.json --num-workers 16 --testrun-dir /home/tyler/acto-data/gen6/testrun-knative-serving-whitebox
python3 scripts/feature_results_to_csv.py --testrun-dir /home/tyler/acto-data/gen6/testrun-knative-serving-whitebox

python3 checker.py --config data/knative-operator-eventing/config.json --num-workers 16 --testrun-dir /home/tyler/acto-data/gen6/testrun-knative-eventing-whitebox
python3 scripts/feature_results_to_csv.py --testrun-dir /home/tyler/acto-data/gen6/testrun-knative-eventing-whitebox

python3 checker.py --config data/mongodb-community-operator/config.json --num-workers 16 --testrun-dir /home/tyler/acto-data/gen6/testrun-mongodb-comm-whitebox
python3 scripts/feature_results_to_csv.py --testrun-dir /home/tyler/acto-data/gen6/testrun-mongodb-comm-whitebox

python3 checker.py --config data/percona-server-mongodb-operator/config.json --num-workers 16 --testrun-dir /home/tyler/acto-data/gen6/testrun-percona-mongodb-whitebox
python3 scripts/feature_results_to_csv.py --testrun-dir /home/tyler/acto-data/gen6/testrun-percona-mongodb-whitebox

python3 checker.py --config data/rabbitmq-operator/config.json --num-workers 16 --testrun-dir /home/tyler/acto-data/gen6/testrun-rabbitmq-whitebox
python3 scripts/feature_results_to_csv.py --testrun-dir /home/tyler/acto-data/gen6/testrun-rabbitmq-whitebox

python3 checker.py --config data/redis-ot-container-kit-operator/config.json --num-workers 16 --testrun-dir /home/tyler/acto-data/gen6/testrun-redis-ot-whitebox
python3 scripts/feature_results_to_csv.py --testrun-dir /home/tyler/acto-data/gen6/testrun-redis-ot-whitebox

python3 checker.py --config data/redis-operator/config.json --num-workers 16 --testrun-dir /home/tyler/acto-data/gen6/testrun-redis-whitebox
python3 scripts/feature_results_to_csv.py --testrun-dir /home/tyler/acto-data/gen6/testrun-redis-whitebox

# python3 checker.py --config data/zookeeper-operator/config.json --num-workers 16 --testrun-dir testrun-zk-whitebox