# Functionality tests
python3 -m acto --config data/percona-server-mongodb-operator/v1-16-0/func-only.json --workdir testrun-mongodb-func --num-workers 4

python3 -m acto --config data/cass-operator/v1-22/func-only.json --workdir testrun-cass-func --num-workers 4

python3 -m acto --config data/tidb-operator/v1-6-0/func-only.json --workdir testrun-tidb-func --num-workers 4

python3 -m acto --config data/mariadb-operator/v0-30-0/func-only.json --workdir testrun-mariadb-func --num-workers 6


# Config tests
python3 -m acto --config data/percona-server-mongodb-operator/v1-16-0/config-only.json --workdir testrun-mongodb-conf --num-workers 4

python3 -m acto --config data/cass-operator/v1-22/config-only.json --workdir testrun-cass-conf --num-workers 4

python3 -m acto --config data/tidb-operator/v1-6-0/config-only.json --workdir testrun-tidb-conf --num-workers 4

python3 -m acto --config data/mariadb-operator/v0-30-0/config-only.json --workdir testrun-mariadb-conf --num-workers 6

# Functionality fault injection run
python3 -m chactos --config data/percona-server-mongodb-operator/v1-16-0/func-only.json \
    --workdir testrun-mongodb-func-fi \
    --fi-config chactos/percona-mongodb-operator.json \
    --testrun-dir testrun-mongodb-func \
    --num-workers 4

python3 -m chactos --config data/cass-operator/v1-22/func-only.json \
    --workdir testrun-cass-func-fi \
    --fi-config chactos/cass-operator.json \
    --testrun-dir testrun-cass-func \
    --num-workers 4

python3 -m chactos --config data/tidb-operator/v1-6-0/func-only.json \
    --workdir testrun-tidb-func-fi \
    --fi-config chactos/tidb-operator.json \
    --testrun-dir testrun-tidb-func \
    --num-workers 4

python3 -m chactos --config data/mariadb-operator/v0-30-0/func-only.json \
    --workdir testrun-mariadb-func-fi \
    --fi-config chactos/mariadb-operator.json \
    --testrun-dir testrun-mariadb-func \
    --num-workers 6

# Config fault injection run

python3 -m chactos --config data/percona-server-mongodb-operator/v1-16-0/config-only.json \
    --workdir testrun-mongodb-conf-fi \
    --fi-config chactos/percona-mongodb-operator.json \
    --testrun-dir testrun-mongodb-conf \
    --num-workers 4

python3 -m chactos --config data/cass-operator/v1-22/config-only.json \
    --workdir testrun-cass-conf-fi \
    --fi-config chactos/cass-operator.json \
    --testrun-dir testrun-cass-conf \
    --num-workers 4

python3 -m chactos --config data/tidb-operator/v1-6-0/config-only.json \
    --workdir testrun-tidb-conf-fi \
    --fi-config chactos/tidb-operator.json \
    --testrun-dir testrun-tidb-conf \
    --num-workers 4

python3 -m chactos --config data/mariadb-operator/v0-30-0/config-only.json \
    --workdir testrun-mariadb-conf-fi \
    --fi-config chactos/mariadb-operator.json \
    --testrun-dir testrun-mariadb-conf \
    --num-workers 6
