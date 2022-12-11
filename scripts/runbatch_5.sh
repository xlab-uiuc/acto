if [ $1 = "whitebox" ]
then
    python3 acto.py --config data/percona-xtradb-cluster-operator/config.json --num-workers 8 --num-cases 1 --workdir testrun-xtradb-whitebox --notify-crash
    python3 checker.py --config data/percona-xtradb-cluster-operator/config.json --num-workers 16 --testrun-dir testrun-xtradb-whitebox
    bash scripts/teardown.sh
elif [ $1 = "blackbox" ]
then
    python3 acto.py --config data/percona-xtradb-cluster-operator/config.json --blackbox --num-workers 8 --num-cases 1 --workdir testrun-xtradb-blackbox --notify-crash
    python3 checker.py --config data/percona-xtradb-cluster-operator/config.json --blackbox --num-workers 16 --testrun-dir testrun-xtradb-blackbox
    bash scripts/teardown.sh
else
    echo "Invalid mode"
    exit 1
fi

rm -rf testrun-*/images.tar
find testrun-* -maxdepth 0 -exec tar -czf {}.tar.gz {} \;