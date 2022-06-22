# Kafka Operator
* [Link](https://banzaicloud.com/docs/supertubes/kafka-operator/install-kafka-operator/)

# Step-by-step
```bash
# Step1: Install cert-manager
kubectl create -f https://github.com/jetstack/cert-manager/releases/download/v1.6.2/cert-manager.yaml

# Step2: Install Zookeeper
helm repo add pravega https://charts.pravega.io
helm repo update
helm install zookeeper-operator --namespace=zookeeper --create-namespace pravega/zookeeper-operator

# Step3: Create a Zookeeper cluster
kubectl create --namespace zookeeper -f - <<EOF
apiVersion: zookeeper.pravega.io/v1beta1
kind: ZookeeperCluster
metadata:
    name: zookeeper
    namespace: zookeeper
spec:
    replicas: 1
EOF

# Step4: Install Prometheus-operator 
kubectl create -n default -f https://raw.githubusercontent.com/coreos/prometheus-operator/master/bundle.yaml

# Step5: Install CRD
kubectl create --validate=false -f https://github.com/banzaicloud/koperator/releases/download/v0.21.2/kafka-operator.crds.yaml

# Step6: Install kafka operator
helm install kafka-operator --namespace=kafka --create-namespace charts/kafka-operator/

# Step7: Create a Kafka cluster
kubectl create -n kafka -f simplekafkacluster.yaml
```
