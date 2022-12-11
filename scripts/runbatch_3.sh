
if [ $1 = "whitebox" ]
then
    python3 acto.py --config data/tidb-operator/config.json --num-workers 12 --num-cases 1 --workdir testrun-tidb-whitebox --notify-crash
    python3 checker.py --config data/tidb-operator/config.json --num-workers 16 --testrun-dir testrun-tidb-whitebox
    bash scripts/teardown.sh
elif [ $1 = "blackbox" ]
then
    python3 acto.py --config data/tidb-operator/config.json --blackbox --num-workers 12 --num-cases 1 --workdir testrun-tidb-blackbox --notify-crash
    python3 checker.py --config data/tidb-operator/config.json --blackbox --num-workers 16 --testrun-dir testrun-tidb-blackbox
    bash scripts/teardown.sh
else
    echo "Invalid mode"
    exit 1
fi

rm -rf testrun-*/images.tar
find testrun-* -maxdepth 0 -exec tar -czf {}.tar.gz {} \;