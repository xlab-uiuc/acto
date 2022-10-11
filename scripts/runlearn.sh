#!/bin/bash

# TODO: implement gnu parallel

python3 acto.py --config data/cass-operator/config.json --learn --learn-analysis
python3 acto.py --config data/cockroach-operator/config.json --learn --learn-analysis
python3 acto.py --config data/mongodb-community-operator/config.json --learn --learn-analysis
python3 acto.py --config data/percona-server-mongodb-operator/config.json --learn --learn-analysis
python3 acto.py --config data/percona-xtradb-cluster-operator/config.json --learn --learn-analysis
python3 acto.py --config data/rabbitmq-operator/config.json --learn --learn-analysis
python3 acto.py --config data/redis-operator/config.json --learn --learn-analysis
python3 acto.py --config data/redis-ot-container-kit-operator/config.json --learn --learn-analysis
python3 acto.py --config data/tidb-operator/config.json --learn --learn-analysis
python3 acto.py --config data/zookeeper-operator/config.json --learn --learn-analysis