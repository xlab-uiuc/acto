import json
import logging

from acto.lib.operator_config import OperatorConfig
from chactos.fault_injections import ExperimentDriver

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-7s, %(name)s, %(filename)-9s:%(lineno)d, %(message)s",
)
logging.getLogger("kubernetes").setLevel(logging.ERROR)
logging.getLogger("sh").setLevel(logging.ERROR)

with open(
    "data/zookeeper-operator/v0.2.15/config.json", "r", encoding="utf-8"
) as config_file:
    config = json.load(config_file)

driver = ExperimentDriver(
    operator_config=OperatorConfig.model_validate(config), worker_id=0
)
driver.run()
