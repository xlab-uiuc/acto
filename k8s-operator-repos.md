I looked at Populatiry and activeness of the operator repository when I look for k8s operator repositories.

I list some operators, divided by their CAPABILITY LEVEL according to OperatorHub.
However, using OperatorHub is not necessarily the best way to find operators, since a **lot** of operators are not on it. 
So I included some operators with many "stars" from github but not present on the OperatorHub at the end.

# Auto Pilot
- [Argo CD](https://github.com/argoproj-labs/argocd-operator)
- [Crunchy Postgres for Kubernetes](https://github.com/CrunchyData/postgres-operator)

# Deep Insights
- [Apache Spark Operator](https://github.com/radanalyticsio/spark-operator)
- [Azure Service Operator](https://github.com/Azure/azure-service-operator)
- [Community Jaeger Operator](https://github.com/jaegertracing/jaeger-operator)
- [Kiali Operator](https://github.com/kiali/kiali)
- [Spark Operator by GCP](https://github.com/GoogleCloudPlatform/spark-on-k8s-operator)
- [Strimzi](https://github.com/strimzi/strimzi-kafka-operator)
- [TiDB Operator](https://github.com/pingcap/tidb-operator)
- [Percona Distribution for MongoDB Operator](https://jira.percona.com/projects/K8SPSMDB/issues/K8SPSMDB-511?filter=allopenissues) @jira (jira database has priority tags on the issues, thus should be easier to analyze)
- [Percona XtraDB Cluster Operator](https://jira.percona.com/projects/K8SPXC/issues/K8SPXC-860?filter=allopenissues) @jira

# Other operators for some popular services
- [postgres-operator](https://github.com/zalando/postgres-operator)
- [pravega-operator](https://github.com/pravega/pravega-operator) This one has a priority label for its bugs
- [RabbitMQ](https://github.com/rabbitmq/cluster-operator)
- [TensorFlow](https://github.com/kubeflow/tf-operator)
- [flux](https://github.com/fluxcd/flux)
- [prometheus-operator](https://github.com/prometheus-operator/prometheus-operator)