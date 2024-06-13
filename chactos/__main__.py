import json

from chactos.fault_injections import ExperimentDriver

with open(
    "data/zookeeper-operator/v0.2.15/config.json", "r", encoding="utf-8"
) as config_file:
    config = json.load(config_file)

driver = ExperimentDriver(config, 0)
driver.run()
