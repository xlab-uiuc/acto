python3 acto.py --config data/percona-server-mongodb-operator/config.json --num-workers 12 --num-cases 1 --workdir testrun-percona-mongodb --notify-crash
python3 checker.py --config data/percona-server-mongodb-operator/config.json --num-workers 16 --testrun-dir testrun-percona-mongodb
bash scripts/teardown.sh

rm -rf testrun-*/images.tar
find testrun-* -maxdepth 0 -exec tar -czf {}.tar.gz {} \;