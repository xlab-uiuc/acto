if [ $1 = "whitebox" ]
then
    python3 acto.py --config data/knative-operator-serving/config.json --num-workers 16 --num-cases 1 --workdir testrun-knative-serving-whitebox --notify-crash
    python3 checker.py --config data/knative-operator-serving/config.json --num-workers 16 --testrun-dir testrun-knative-serving-whitebox
    bash scripts/teardown.sh

    python3 acto.py --config data/knative-operator-eventing/config.json --num-workers 16 --num-cases 1 --workdir testrun-knative-eventing-whitebox --notify-crash
    python3 checker.py --config data/knative-operator-eventing/config.json --num-workers 16 --testrun-dir testrun-knative-eventing-whitebox
    bash scripts/teardown.sh
elif [ $1 = "blackbox" ]
then
    python3 acto.py --config data/knative-operator-serving/config.json --blackbox --num-workers 16 --num-cases 1 --workdir testrun-knative-serving-blackbox --notify-crash
    python3 checker.py --config data/knative-operator-serving/config.json --blackbox --num-workers 16 --testrun-dir testrun-knative-serving-blackbox
    bash scripts/teardown.sh

    python3 acto.py --config data/knative-operator-eventing/config.json --blackbox --num-workers 16 --num-cases 1 --workdir testrun-knative-eventing-blackbox --notify-crash
    python3 checker.py --config data/knative-operator-eventing/config.json --blackbox --num-workers 16 --testrun-dir testrun-knative-eventing-blackbox
    bash scripts/teardown.sh
else
    echo "Invalid mode"
    exit 1
fi


rm -rf testrun-*/images.tar
find testrun-* -maxdepth 0 -exec tar -czf {}.tar.gz {} \;