# Onboarding Task - Yuxuan

### Target Operator 
[ot-container-kit/redis-operator](https://github.com/OT-CONTAINER-KIT/redis-operator)

### Run test for the redis cluster support
```shell
screen python3 acto.py -s data/redis-ot-container-kit-operator/cr_cluster.yaml -o data/redis-ot-container-kit-operator/bundle.yaml --crd-name redisclusters.redis.redis.opstreelabs.in
```

### Run test for the redis standalone support
```shell
screen python3 acto.py -s data/redis-ot-container-kit-operator/cr_standalone.yaml -o data/redis-ot-container-kit-operator/bundle.yaml --crd-name redis.redis.redis.opstreelabs.in
```


