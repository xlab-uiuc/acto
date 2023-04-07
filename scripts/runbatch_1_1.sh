if [ $1 = "whitebox" ]
then 
    python3 acto.py --config data/cockroach-operator/config.json --num-workers 16 --num-cases 1 --workdir testrun-crdb-whitebox --notify-crash
    python3 checker.py --config data/cockroach-operator/config.json --num-workers 16 --testrun-dir testrun-crdb-whitebox
    bash scripts/teardown.sh
elif [ $1 = "blackbox" ]
then
    python3 acto.py --config data/cockroach-operator/config.json --blackbox --num-workers 16 --num-cases 1 --workdir testrun-crdb-blackbox --notify-crash
    python3 checker.py --config data/cockroach-operator/config.json --blackbox --num-workers 16 --testrun-dir testrun-crdb-blackbox
    bash scripts/teardown.sh
else
    echo "Invalid mode"
    exit 1
fi

rm -rf testrun-*/images.tar
find testrun-* -maxdepth 0 -exec tar -czf {}.tar.gz {} \;