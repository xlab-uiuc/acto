# How to run MongoDB operator?
```
# Step1: Install operator
helm install community-operator community-operator/

# Step2: Create a custom resource
kubectl apply -f cr.yaml

# Step3: Check CR status 
kubectl get mdbc

# Step4: Check secrets (You should see the secret "example-mongodb-admin-my-user".)
kubectl get secrets

# Step5: Deploy Application
helm install mongo-app sample-app

# Step6: Check application
export POD_NAME=$(kubectl get pods --namespace default -l "app.kubernetes.io/name=sample-app,app.kubernetes.io/instance=mongo-app" -o jsonpath="{.items[0].metadata.name}")
export CONTAINER_PORT=$(kubectl get pod --namespace default $POD_NAME -o jsonpath="{.spec.containers[0].ports[0].containerPort}")
echo "Visit http://127.0.0.1:8080 to use your application"
kubectl --namespace default port-forward $POD_NAME 8080:$CONTAINER_PORT
```

# Resources
* https://github.com/mongodb/helm-charts
* https://github.com/mongodb/mongodb-kubernetes-operator
