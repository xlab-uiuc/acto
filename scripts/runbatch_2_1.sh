if [ $1 = "whitebox" ]
then 
    python3 acto.py --config data/redis-ot-container-kit-operator/config.json --num-workers 16 --num-cases 1 --workdir testrun-redis-ot-whitebox --notify-crash
    python3 checker.py --config data/redis-ot-container-kit-operator/config.json --num-workers 16 --testrun-dir testrun-redis-ot-whitebox
    bash scripts/teardown.sh
elif [ $1 = "blackbox" ]
then
    python3 acto.py --config data/redis-ot-container-kit-operator/config.json --blackbox  --num-workers 16 --num-cases 1 --workdir testrun-redis-ot-blackbox --notify-crash
    python3 checker.py --config data/redis-ot-container-kit-operator/config.json --blackbox  --num-workers 16 --testrun-dir testrun-redis-ot-blackbox
    bash scripts/teardown.sh
else
    echo "Invalid mode"
    exit 1
fi

rm -rf testrun-*/images.tar
find testrun-* -maxdepth 0 -exec tar -czf {}.tar.gz {} \;