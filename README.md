# Acto: Automatic, Continuous Testing for (Kubernetes/OpenShift) Operators

## Prerequisites
- kubernetes  
    `pip3 install kubernetes`
- DeepDiff  
    `pip3 install deepdiff`
- [k8s Kind cluster](https://kind.sigs.k8s.io/)  
    - For go(1.17+)  
    `go install sigs.k8s.io/kind@v0.11.1`
    - For older version  
    `GO111MODULE="on" go get sigs.k8s.io/kind@v0.11.1`

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