python3 acto.py --config data/percona-xtradb-cluster-operator/config.json --num-workers 8 --num-cases 1 --workdir testrun-xtradb --notify-crash
python3 checker.py --config data/percona-xtradb-cluster-operator/config.json --num-workers 16 --testrun-dir testrun-xtradb
bash scripts/teardown.sh

rm -rf testrun-*/images.tar
find testrun-* -maxdepth 0 -exec tar -czf {}.tar.gz {} \;