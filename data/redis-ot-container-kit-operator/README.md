### Target Operator 
[ot-container-kit/redis-operator](https://github.com/OT-CONTAINER-KIT/redis-operator)

We use the commit [f1c547](https://github.com/OT-CONTAINER-KIT/redis-operator/commit/f1c547e26ece015c0c5cd8a8549ff277e8e7c2ab) as the version being tested.
To reproduce experiment against this version, follow the below instructions.
First, copy the following repo. This repo is forked from the original one and has been modified based on commit f1c547. We added a few logs inside the codebase for debugging purposes and also modified the docker image tag so that we can use the custom-built image and the official images simutaneously.
```shell
git clone git@github.com:Essoz/redis-operator-hack.git
cd redis-operator-hack
make docker-build
```
Go back to the acto folder:
```shell
python3 acto.py -s data/redis-ot-container-kit-operator/cr_cluster.yaml \
            -o data/redis-ot-container-kit-operator/bundle.yaml \
            --crd-name redisclusters.redis.redis.opstreelabs.in  \               
            --custom-fields data.redis-ot-container-kit-operator.prune \
            --preload-images f1c547e/redis-operator
```



### Run test for the redis cluster support
```shell
python3 acto.py -s data/redis-ot-container-kit-operator/cr_cluster.yaml -o data/redis-ot-container-kit-operator/bundle.yaml --crd-name redisclusters.redis.redis.opstreelabs.in
```

### Run test for the redis standalone support
```shell
python3 acto.py -s data/redis-ot-container-kit-operator/cr_standalone.yaml -o data/redis-ot-container-kit-operator/bundle.yaml --crd-name redis.redis.redis.opstreelabs.in
```

### Necessary Modifications to Acto:
1. Acto currently uses a naive pruning methodology. If you find out that no test plan is generated, please modify [this line](https://github.com/xlab-uiuc/acto/blob/b757555edb9792344995f63f7eb4eb2ddbd19510/schema.py#L356) to 600 or 100 in order to avoid the pruning the entire `cr.spec` field.

2. The operator does not return status info about the CR. If you run into a `<class: 'KeyError'>: 'status'`, please modify [this line](https://github.com/xlab-uiuc/acto/blob/main/check_result.py#L72) to 
   ```python
   if 'status' in current_cr['test-cluster']:
       current_cr_status = current_cr['test-cluster']['status']
   else: 
       current_cr_status = None
   ```

