if [ $1 = "whitebox" ]
then
    python3 acto.py --config data/percona-server-mongodb-operator/config.json --num-workers 12 --num-cases 1 --workdir testrun-percona-mongodb-whitebox --notify-crash
    python3 checker.py --config data/percona-server-mongodb-operator/config.json --num-workers 16 --testrun-dir testrun-percona-mongodb-whitebox
    bash scripts/teardown.sh
elif [ $1 = "blackbox" ]
then
    python3 acto.py --config data/percona-server-mongodb-operator/config.json --blackbox --num-workers 12 --num-cases 1 --workdir testrun-percona-mongodb-blackbox --notify-crash
    python3 checker.py --config data/percona-server-mongodb-operator/config.json --blackbox --num-workers 16 --testrun-dir testrun-percona-mongodb-blackbox
    bash scripts/teardown.sh
else
    echo "Invalid mode"
    exit 1
fi

rm -rf testrun-*/images.tar
find testrun-* -maxdepth 0 -exec tar -czf {}.tar.gz {} \;