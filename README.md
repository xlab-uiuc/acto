# Acto: Automatic, Continuous Testing for (Kubernetes/OpenShift) Operators

## Prerequisites
- Python dependencies
    - `pip3 install -r requirements.txt`
- [k8s Kind cluster](https://kind.sigs.k8s.io/)  
    - For go(1.17+)  
    `go install sigs.k8s.io/kind@v0.11.1`
    - For older version  
    `GO111MODULE="on" go get sigs.k8s.io/kind@v0.11.1`
- kubectl
    - [Installation](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/)

## Usage
To run the test:  
```
python3 acto.py --candidates [CANDIDATE_FILE] \
                --seed [SEED_CR] \
                --operator [OPERATOR_CR] \
                --duration [#HOURS]
```

Example:  
To run the test on the rabbitmq-operator:  
`python3 acto.py --candidates data/rabbitmq-operator/candidates.yaml --seed data/rabbitmq-operator/cr.yaml --operator data/rabbitmq-operator/operator.yaml --duration 1`

cass-operator (using helm)   
`python3 acto_helm.py --candidates data/cass-operator/candidates.yaml --seed data/cass-operator/cr.yaml --helm data/cass-operator/cass-operator --crd=data/cass-operator/cass-operator/crds/customresourcedefinition.yaml --init data/cass-operator/init.yaml --duration 1`

## Porting operators
Acto aims to automate the E2E testing as much as possible to minimize users' labor.

Currently, porting operators still requires some manual effort, we need:
1. The operator deployment yaml file to deploy the operator, the yaml file also needs to contain all the necessary prerequisites to deploy the operator, e.g. CRD, namespace creation, RBAC, etc.
2. A candidates file specifying possible values for some parameters. The candidates file's format is very similar to a CR, except you replace the values with another field `candidates` and specify a list of values under `candidates`. Example:
    ```yaml
    image:
        candidates:
        - "rabbitmq:3.8.21-management"
        - "rabbitmq:latest"
        - "rabbitmq:3.9-management"
        - null
    ```
    A complete example for rabbitmq-operator is [here](data/rabbitmq-operator/candidates.yaml)

    We aim to remove this requirement for a candidates file in the future.
3. A seed CR yaml serving as the initial cr input. This can be any valid CR for your application. [Example](data/rabbitmq-operator/cr.yaml)
