### Target Operator
[percona/percona-xtradb-cluster-operator](https://github.com/percona/percona-xtradb-cluster-operator)

### Running Experiments
We use the version [v1.11.0](https://github.com/percona/percona-xtradb-cluster-operator/commit/e797d016cfbf847ff0a45ce1b1a1d10ad70a2fd3) as the version being tested.

To run the experiments, execute the below command
```bash
python3 acto.py --seed data/percona-xtradb-cluster-operator/cr.yaml \
                --operator data/percona-xtradb-cluster-operator/cw-bundle.yaml \
                --crd-name perconaxtradbclusters.pxc.percona.com \
                --custom-fields data.percona-xtradb-cluster-operator.prune
```
Note that the operator is deployed in "[Cluster-Wide](https://www.percona.com/doc/kubernetes-operator-for-pxc/cluster-wide.html#install-clusterwide)" mode for [enabling the input validation webhook](https://www.percona.com/doc/kubernetes-operator-for-pxc/cluster-wide.html#install-clusterwide). The clusterRolebinding resource's namespace has been set to `acto-namespace` so that Acto can deploy the operator.

To reproduce an experiment, either 
- use `reproduce.py`  
  - usage:
    ```shell
    python3 acto.py --config <CONFIG PATH> --num-workers 1 --is_reproduce --reproduce_dir <PATH TO THE FOLDER OF CR FILES>
    ```
- or deploy the operator using

    ```
    kubectl create namespace acto-namespace
    kubectl apply -f data/percona-xtradb-cluster-operator/cw-bundle.yaml
    ```
- or if the input validation webhook is not needed (the operator will still validate input after submission, but the error message will only be printed to operator log), simply

    ```
    kubectl apply -f data/percona-xtradb-cluster-operator/bundle.yaml
    ```

