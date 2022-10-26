go run cmd/compareFields.go/compareFields.go -test-plan /home/tyler/acto-data/rabbitmq-operator/testrun-2022-10-16-11-26/test_plan.json -project-path ~/rabbitmq-operator/ -seed-type RabbitmqCluster -seed-pkg github.com/rabbitmq/cluster-operator/api/v1beta1

go run cmd/compareFields.go/compareFields.go -test-plan /home/tyler/acto-data/zookeeper-operator/testrun-2022-10-12-05-56/test_plan.json -project-path ~/zookeeper-operator/ -seed-type ZookeeperCluster -seed-pkg github.com/pravega/zookeeper-operator/api/v1beta1

go run cmd/compareFields.go/compareFields.go -test-plan /home/tyler/acto-data/cass-operator/testrun-2022-10-12-00-19/test_plan.json -project-path ~/cass-operator -seed-type CassandraDatacenter -seed-pkg github.com/k8ssandra/cass-operator/apis/cassandra/v1beta1 -yaml-dir ~/cass-operator/tests/testdata/

go run cmd/compareFields.go/compareFields.go -test-plan /home/tyler/acto/testrun-2022-08-11-16-39-redis/test_plan.json -project-path ~/redis-operator -seed-type RedisFailover -seed-pkg github.com/spotahome/redis-operator/api/redisfailover/v1

go run cmd/compareFields.go/compareFields.go -test-plan /home/tyler/acto/testrun-2022-08-11-16-39-redis/test_plan.json -project-path ~/redis-operator -seed-type RedisCluster -seed-pkg redis-operator/api/v1beta1 -yaml-dir ~/redis-operator/tests/testdata/

go run cmd/compareFields.go/compareFields.go -test-plan /home/tyler/acto/testrun-2022-09-13-14-35-pmongo/test_plan.json -project-path ~/percona-server-mongodb-operator/ -seed-type PerconaServerMongoDB -seed-pkg github.com/percona/percona-server-mongodb-operator/pkg/apis/psmdb/v1 -yaml-dir ~/percona-server-mongodb-operator/e2e-tests/

go run cmd/compareFields.go/compareFields.go -test-plan /home/tyler/acto/testrun-crdb/test_plan.json -project-path ~/acto-ops/cockroach-operator/ -seed-type CrdbCluster -seed-pkg github.com/cockroachdb/cockroach-operator/apis/v1alpha1

go run cmd/compareFields.go/compareFields.go -test-plan /home/tyler/acto-data/tidb-operator/testrun-2022-10-16-15-04/test_plan.json -project-path ~/acto-ops/tidb-operator -seed-type TidbCluster -seed-pkg github.com/pingcap/tidb-operator/pkg/apis/pingcap/v1alpha1 -test-dir github.com/pingcap/tidb-operator/tests