echo "Running Performance Measurement workloads for Welder Deployment Controller"

python3 -m plugins.performance_measurement.measure_performance\
    --project vdeployment-controller\
    --anvil-config data/vdeployment-controller/v0/config.json\
    --reference-config data/deployment-controller/v0/config.json\
    --input-dir welder-ae-data/testrun-vdeployment\
    --workdir testrun-vdeployment-performance\
    --modes single-operation\
    --sample $1

echo "Welder Deployment Controller performance results are stored in testrun-vdeployment-performance"

echo "Parsing performance data"

python3 plugins/performance_measurement/process_ts.py
