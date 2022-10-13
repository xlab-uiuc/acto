go run cmd/compareFields.go/compareFields.go -test-plan /home/tyler/acto-data/rabbitmq-operator/testrun-2022-10-08-01-09/test_plan.json -project-path ~/rabbitmq-operator/ -seed-type RabbitmqCluster -seed-pkg github.com/rabbitmq/cluster-operator/api/v1beta1

go run cmd/compareFields.go/compareFields.go -test-plan /home/tyler/acto-data/zookeeper-operator/testrun-2022-10-12-05-56/test_plan.json -project-path ~/zookeeper-operator/ -seed-type ZookeeperCluster -seed-pkg github.com/pravega/zookeeper-operator/api/v1beta1

go run cmd/compareFields.go/compareFields.go -test-plan /home/tyler/acto-data/cass-operator/testrun-2022-10-12-00-19/test_plan.json -project-path ~/cass-operator -seed-type CassandraDatacenter -seed-pkg github.com/k8ssandra/cass-operator/apis/cassandra/v1beta1 -yaml-dir ~/cass-operator/tests/testdata/

go run cmd/compareFields.go/compareFields.go -test-plan /home/tyler/acto/testrun-2022-08-11-16-39-redis/test_plan.json -project-path ~/redis-operator -seed-type RedisFailover -seed-pkg github.com/spotahome/redis-operator/api/redisfailover/v1

go run cmd/compareFields.go/compareFields.go -test-plan /home/tyler/acto/testrun-2022-09-13-14-35-pmongo/test_plan.json -project-path ~/percona-server-mongodb-operator/ -seed-type PerconaServerMongoDB -seed-pkg github.com/percona/percona-server-mongodb-operator/pkg/apis/psmdb/v1 -yaml-dir ~/percona-server-mongodb-operator/e2e-tests/