if [ $1 = "whitebox" ]
then 
    python3 acto.py --config data/redis-operator/config.json --num-workers 16 --num-cases 1 --workdir testrun-redis-whitebox --notify-crash
    python3 checker.py --config data/redis-operator/config.json --num-workers 16 --testrun-dir testrun-redis-whitebox
    bash scripts/teardown.sh

    python3 acto.py --config data/zookeeper-operator/config.json --num-workers 16 --num-cases 1 --workdir testrun-zk-whitebox --notify-crash
    python3 checker.py --config data/zookeeper-operator/config.json --num-workers 16 --testrun-dir testrun-zk-whitebox
    bash scripts/teardown.sh
elif [ $1 = "blackbox" ]
then
    python3 acto.py --config data/redis-operator/config.json --blackbox --num-workers 16 --num-cases 1 --workdir testrun-redis-blackbox --notify-crash
    python3 checker.py --config data/redis-operator/config.json --num-workers 16 --testrun-dir testrun-redis-blackbox
    bash scripts/teardown.sh

    python3 acto.py --config data/zookeeper-operator/config.json --blackbox --num-workers 16 --num-cases 1 --workdir testrun-zk-blackbox --notify-crash
    python3 checker.py --config data/zookeeper-operator/config.json --blackbox --num-workers 16 --testrun-dir testrun-zk-blackbox
    bash scripts/teardown.sh
else
    echo "Invalid mode"
    exit 1
fi

rm -rf testrun-*/images.tar
find testrun-* -maxdepth 0 -exec tar -czf {}.tar.gz {} \;