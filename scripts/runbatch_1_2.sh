if [ $1 = "whitebox" ]
then
    python3 acto.py --config data/mongodb-community-operator/config.json --num-workers 16 --num-cases 1 --workdir testrun-mongodb-comm-whitebox --notify-crash
    python3 checker.py --config data/mongodb-community-operator/config.json --num-workers 16 --testrun-dir testrun-mongodb-comm-whitebox
    bash scripts/teardown.sh

    python3 acto.py --config data/rabbitmq-operator/config.json --num-workers 16 --num-cases 1 --workdir testrun-rabbitmq-whitebox --notify-crash
    python3 checker.py --config data/rabbitmq-operator/config.json --num-workers 16 --testrun-dir testrun-rabbitmq-whitebox
    bash scripts/teardown.sh
elif [ $1 = "blackbox" ]
then
    python3 acto.py --config data/mongodb-community-operator/config.json --blackbox --num-workers 16 --num-cases 1 --workdir testrun-mongodb-comm-blackbox --notify-crash
    python3 checker.py --config data/mongodb-community-operator/config.json --blackbox --num-workers 16 --testrun-dir testrun-mongodb-comm-blackbox
    bash scripts/teardown.sh

    python3 acto.py --config data/rabbitmq-operator/config.json --blackbox --num-workers 16 --num-cases 1 --workdir testrun-rabbitmq-blackbox --notify-crash
    python3 checker.py --config data/rabbitmq-operator/config.json --blackbox --num-workers 16 --testrun-dir testrun-rabbitmq-blackbox
    bash scripts/teardown.sh
else
    echo "Invalid mode"
    exit 1
fi

rm -rf testrun-*/images.tar
find testrun-* -maxdepth 0 -exec tar -czf {}.tar.gz {} \;