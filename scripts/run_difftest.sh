python3 -m post_process.post_diff_test --config data/cass-operator/config.json --num-workers 16 \
    --testrun-dir /home/tyler/acto-data/cass-operator/testrun-cass-whitebox \
    --workdir-path difftest-cass-whitebox \
    --checkonly


python3 -m post_process.post_diff_test --config data/cass-operator/config.json --num-workers 16 \
    --testrun-dir /home/tyler/acto-data/cass-operator/testrun-cass-blackbox \
    --workdir-path difftest-cass-blackbox \
    --checkonly

python3 -m post_process.post_diff_test --config data/cockroach-operator/config.json --num-workers 16 \
    --testrun-dir testrun-crdb-whitebox \
    --workdir-path difftest-crdb-whitebox \
    --checkonly

python3 -m post_process.post_diff_test --config data/cockroach-operator/config.json --num-workers 16 \
    --testrun-dir testrun-crdb-blackbox \
    --workdir-path difftest-crdb-blackbox \
    --checkonly

python3 -m post_process.post_diff_test --config data/knative-operator-eventing/config.json --num-workers 16 \
    --testrun-dir /users/tylergu/acto/gen5/testrun-knative-eventing-whitebox \
    --workdir-path difftest-knative-eventing-whitebox \
    --checkonly

python3 -m post_process.post_diff_test --config data/knative-operator-eventing/config.json --num-workers 16 \
    --testrun-dir testrun-knative-eventing-blackbox \
    --workdir-path difftest-knative-eventing-blackbox \
    --checkonly

python3 -m post_process.post_diff_test --config data/knative-operator-serving/config.json --num-workers 16 \
    --testrun-dir /users/tylergu/acto/gen5/testrun-knative-serving-whitebox \
    --workdir-path difftest-knative-serving-whitebox \
    --checkonly

python3 -m post_process.post_diff_test --config data/knative-operator-serving/config.json --num-workers 16 \
    --testrun-dir testrun-knative-serving-blackbox \
    --workdir-path difftest-knative-serving-blackbox \
    --checkonly

python3 -m post_process.post_diff_test --config data/mongodb-community-operator/config.json --num-workers 16 \
    --testrun-dir testrun-mongodb-comm-whitebox \
    --workdir-path difftest-mongodb-comm-whitebox \
    --checkonly

python3 -m post_process.post_diff_test --config data/mongodb-community-operator/config.json --num-workers 16 \
    --testrun-dir testrun-mongodb-comm-blackbox \
    --workdir-path difftest-mongodb-comm-blackbox \
    --checkonly

python3 -m post_process.post_diff_test --config data/percona-server-mongodb-operator/config.json --num-workers 12 \
    --testrun-dir testrun-percona-mongodb-whitebox \
    --workdir-path difftest-percona-mongodb-whitebox \
    --checkonly

python3 -m post_process.post_diff_test --config data/percona-server-mongodb-operator/config.json --num-workers 12 \
    --testrun-dir testrun-percona-mongodb-blackbox \
    --workdir-path difftest-percona-mongodb-blackbox \
    --checkonly

python3 -m post_process.post_diff_test --config data/percona-xtradb-cluster-operator/config.json --num-workers 12 \
    --testrun-dir testrun-xtradb-whitebox \
    --workdir-path difftest-xtradb-whitebox \
    --checkonly

python3 -m post_process.post_diff_test --config data/percona-xtradb-cluster-operator/config.json --num-workers 12 \
    --testrun-dir testrun-xtradb-blackbox \
    --workdir-path difftest-xtradb-blackbox \
    --checkonly

python3 -m post_process.post_diff_test --config data/rabbitmq-operator/config.json --num-workers 16 \
    --testrun-dir testrun-rabbitmq-whitebox \
    --workdir-path difftest-rabbitmq-whitebox \
    --checkonly

python3 -m post_process.post_diff_test --config data/rabbitmq-operator/config.json --num-workers 16 \
    --testrun-dir testrun-rabbitmq-blackbox \
    --workdir-path difftest-rabbitmq-blackbox \
    --checkonly

python3 -m post_process.post_diff_test --config data/redis-operator/config.json --num-workers 16 \
    --testrun-dir testrun-redis-whitebox \
    --workdir-path difftest-redis-whitebox \
    --checkonly

python3 -m post_process.post_diff_test --config data/redis-operator/config.json --num-workers 16 \
    --testrun-dir testrun-redis-blackbox \
    --workdir-path difftest-redis-blackbox \
    --checkonly

python3 -m post_process.post_diff_test --config data/redis-ot-container-kit-operator/config.json --num-workers 16 \
    --testrun-dir testrun-redis-ot-whitebox \
    --workdir-path difftest-redis-ot-whitebox \
    --checkonly

python3 -m post_process.post_diff_test --config data/redis-ot-container-kit-operator/config.json --num-workers 16 \
    --testrun-dir testrun-redis-ot-blackbox \
    --workdir-path difftest-redis-ot-blackbox \
    --checkonly

python3 -m post_process.post_diff_test --config data/tidb-operator/config.json --num-workers 12 \
    --testrun-dir testrun-tidb-whitebox \
    --workdir-path difftest-tidb-whitebox \
    --checkonly

python3 -m post_process.post_diff_test --config data/tidb-operator/config.json --num-workers 12 \
    --testrun-dir testrun-tidb-blackbox \
    --workdir-path difftest-tidb-blackbox \
    --checkonly

python3 -m post_process.post_diff_test --config data/zookeeper-operator/config.json --num-workers 16 \
    --testrun-dir testrun-zk-whitebox \
    --workdir-path difftest-zk-whitebox \
    --checkonly

python3 -m post_process.post_diff_test --config data/zookeeper-operator/config.json --num-workers 16 \
    --testrun-dir testrun-zk-blackbox \
    --workdir-path difftest-zk-blackbox \
    --checkonly