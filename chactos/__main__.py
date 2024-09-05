import argparse
import json
import logging
from datetime import datetime

from chactos.fault_injection_config import FaultInjectionConfig
from chactos.fault_injections import ExperimentDriver

parser = argparse.ArgumentParser(
    description="Automatic, Continuous Testing for k8s/openshift Operators"
)
parser.add_argument(
    "--workdir",
    dest="workdir_path",
    type=str,
    default=f"testrun-{datetime.now().strftime('%Y-%m-%d-%H-%M')}",
    help="Working directory",
)
parser.add_argument(
    "--config",
    "-c",
    dest="config",
    help="Operator fault injection config path",
    required=True,
)
args = parser.parse_args()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-7s, %(name)s, %(filename)-9s:%(lineno)d, %(message)s",
)
logging.getLogger("kubernetes").setLevel(logging.ERROR)
logging.getLogger("sh").setLevel(logging.ERROR)

with open(args.config, "r", encoding="utf-8") as config_file:
    config = json.load(config_file)

driver = ExperimentDriver(
    operator_config=FaultInjectionConfig.model_validate(config), worker_id=0
)
driver.run()
