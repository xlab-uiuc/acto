echo "Running Performance Measurement workloads for ZooKeeper controller"

python3 -m plugins.performance_measurement.measure_performance --workdir testrun-anvil-zk-performance --input-dir anvil-ae-data/testrun-anvil-zk --anvil-config data/anvil-zookeeper-operator/config.json --reference-config data/zookeeper-operator/v0.2.15/config.json --project zookeeper-operator --sample
echo "ZooKeeper operator performance results are stored in testrun-anvil-zk-performance"

echo "Parsing performance data"

python3 plugins/performance_measurement/process_ts.py
