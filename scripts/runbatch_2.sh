python3 acto.py --config data/redis-operator/config.json --num-workers 16 --num-cases 1 --workdir testrun-redis --notify-crash
python3 checker.py --config data/redis-operator/config.json --num-workers 16 --testrun-dir testrun-redis
bash scripts/teardown.sh

python3 acto.py --config data/redis-ot-container-kit-operator/config.json --num-workers 16 --num-cases 1 --workdir testrun-redis-ot --notify-crash
python3 checker.py --config data/redis-ot-container-kit-operator/config.json --num-workers 16 --testrun-dir testrun-redis-ot
bash scripts/teardown.sh

python3 acto.py --config data/zookeeper-operator/config.json --num-workers 16 --num-cases 1 --workdir testrun-zk --notify-crash
python3 checker.py --config data/zookeeper-operator/config.json --num-workers 16 --testrun-dir testrun-zk
bash scripts/teardown.sh

rm -rf testrun-*/images.tar
find testrun-* -maxdepth 0 -exec tar -czf {}.tar.gz {} \;