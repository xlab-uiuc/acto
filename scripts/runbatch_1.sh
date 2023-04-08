if [ $1 = "whitebox" ]
then
    python3 acto.py --config data/cass-operator/config.json --num-workers 16 --num-cases 1 --workdir testrun-cass-whitebox --notify-crash
    python3 checker.py --config data/cass-operator/config.json --num-workers 16 --testrun-dir testrun-cass-whitebox
    bash scripts/teardown.sh
elif [ $1 = "blackbox" ]
then
    python3 acto.py --config data/cass-operator/config.json --blackbox --num-workers 16 --num-cases 1 --workdir testrun-cass-blackbox --notify-crash
    python3 checker.py --config data/cass-operator/config.json --blackbox --num-workers 16 --testrun-dir testrun-cass-blackbox
    bash scripts/teardown.sh
else
    echo "Invalid mode"
    exit 1
fi

rm -rf testrun-*/images.tar
find testrun-* -maxdepth 0 -exec tar -czf {}.tar.gz {} \;