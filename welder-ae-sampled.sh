echo "Running Performance Measurement workloads"

python3 -m plugins.performance_measurement.measure_performance \
    --project vdeployment-controller \
    --anvil-config data/vdeployment-controller/v0/config.json \
    --reference-config data/deployment-controller/v0/config.json \
    --input-dir welder-ae-data/testrun-vdeployment \
    --workdir testrun-vdeployment-performance \
    --modes single-operation \
    --sample $1
echo "VDeployment controller performance results are stored in testrun-vdeployment-performance"

python3 -m plugins.performance_measurement.measure_performance \
    --project rabbitmq-operator \
    --anvil-config data/anvil-rabbitmq-controller/config.json \
    --reference-config data/rabbitmq-operator/v2.5.0/config.json \
    --input-dir welder-ae-data/testrun-rabbitmq \
    --workdir testrun-rabbitmq-performance \
    --modes single-operation \
    --sample $1
echo "RabbitMQ controller performance results are stored in testrun-rabbitmq-performance"

echo "Parsing performance data"

python3 plugins/performance_measurement/process_ts.py
