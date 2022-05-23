# How to run spark-operator
```sh
helm install acto ./spark-operator-chart
kubectl apply -f cr.yaml
```

* Notice: The field `spec.driver.serviceAccount` must be the same as the name of service account. For example, the name of the helm chart release is `acto`, and the helm chart will create a service account with the name "acto-spark". Hence, in `cr.yaml`, the field `spec.driver.serviceAccount` is "acto-spark". 