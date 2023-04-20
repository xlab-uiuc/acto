# python3 checker.py --config data/cass-operator/config.json --blackbox --num-workers 16 --testrun-dir /home/tyler/acto-data/gen6/blackbox/testrun-cass-blackbox
# python3 scripts/feature_results_to_csv.py --testrun-dir /home/tyler/acto-data/gen6/blackbox/testrun-cass-blackbox

python3 checker.py --config data/cockroach-operator/config.json --blackbox --num-workers 16 --testrun-dir /home/tyler/acto-data/gen6/blackbox/testrun-crdb-blackbox
python3 scripts/feature_results_to_csv.py --testrun-dir /home/tyler/acto-data/gen6/blackbox/testrun-crdb-blackbox

python3 checker.py --config data/knative-operator-serving/config.json --blackbox --num-workers 16 --testrun-dir /home/tyler/acto-data/gen6/blackbox/testrun-knative-serving-blackbox
python3 scripts/feature_results_to_csv.py --testrun-dir /home/tyler/acto-data/gen6/blackbox/testrun-knative-serving-blackbox

python3 checker.py --config data/knative-operator-eventing/config.json --blackbox --num-workers 16 --testrun-dir /home/tyler/acto-data/gen6/blackbox/testrun-knative-eventing-blackbox
python3 scripts/feature_results_to_csv.py --testrun-dir /home/tyler/acto-data/gen6/blackbox/testrun-knative-eventing-blackbox

python3 checker.py --config data/mongodb-community-operator/config.json --blackbox --num-workers 16 --testrun-dir /home/tyler/acto-data/gen6/blackbox/testrun-mongodb-comm-blackbox
python3 scripts/feature_results_to_csv.py --testrun-dir /home/tyler/acto-data/gen6/blackbox/testrun-mongodb-comm-blackbox

# python3 checker.py --config data/percona-server-mongodb-operator/config.json --blackbox --num-workers 16 --testrun-dir /home/tyler/acto-data/gen6/blackbox/testrun-percona-mongodb-blackbox
# python3 scripts/feature_results_to_csv.py --testrun-dir /home/tyler/acto-data/gen6/blackbox/testrun-percona-mongodb-blackbox

python3 checker.py --config data/rabbitmq-operator/config.json --blackbox --num-workers 16 --testrun-dir /home/tyler/acto-data/gen6/blackbox/testrun-rabbitmq-blackbox
python3 scripts/feature_results_to_csv.py --testrun-dir /home/tyler/acto-data/gen6/blackbox/testrun-rabbitmq-blackbox

python3 checker.py --config data/redis-ot-container-kit-operator/config.json --blackbox --num-workers 16 --testrun-dir /home/tyler/acto-data/gen6/blackbox/testrun-redis-ot-blackbox
python3 scripts/feature_results_to_csv.py --testrun-dir /home/tyler/acto-data/gen6/blackbox/testrun-redis-ot-blackbox

python3 checker.py --config data/redis-operator/config.json --blackbox --num-workers 16 --testrun-dir /home/tyler/acto-data/gen6/blackbox/testrun-redis-blackbox
python3 scripts/feature_results_to_csv.py --testrun-dir /home/tyler/acto-data/gen6/blackbox/testrun-redis-blackbox

python3 checker.py --config data/zookeeper-operator/config.json --blackbox --num-workers 16 --testrun-dir /home/tyler/acto-data/gen6/blackbox/testrun-zk-blackbox
python3 scripts/feature_results_to_csv.py --testrun-dir /home/tyler/acto-data/gen6/blackbox/testrun-zk-blackbox