helm repo add k8ssandra https://helm.k8ssandra.io/stable
helm install cass-operator k8ssandra/cass-operator -n cass-operator --create-namespace