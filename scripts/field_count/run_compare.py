import os

if __name__ == '__main__':

    ACTO_DATA = '/home/tyler/acto-data'

    ops = [
        'cass-operator',
        'cockroach-operator',
        'knative-operator-eventing',
        'knative-operator-serving',
        'mongodb-community-operator',
        'percona-server-mongodb-operator',
        'percona-xtradb-cluster-operator',
        'rabbitmq-operator',
        'redis-operator',
        'redis-ot-container-kit-operator',
        'tidb-operator',
        'zookeeper-operator',
    ]

    for op in ops:
        
        os.system('go run cmd/compareFields.go/compareFields.go ')