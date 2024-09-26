import argparse
import json
import logging
from datetime import datetime

from chactos.fault_injection_config import FaultInjectionConfig
from chactos.fault_injections import ChactosDriver

from acto.lib.operator_config import OperatorConfig

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
    help="Operator config path",
    required=True,
)
parser.add_argument(
    "--fi-config",
    "-fic",
    dest="fi_config",
    help="Operator fault injection config path",
    required=True,
)
parser.add_argument(
    "--testrun-dir",
    "-td",
    dest="testrun_dir",
    help="Testrun directory to load the inputs from",
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
    config_data = json.load(config_file)
    operator_config = OperatorConfig.model_validate(config_data)

with open(args.fi_config, "r", encoding="utf-8") as fi_config_file:
    fi_config_data = json.load(fi_config_file)
    fi_config = FaultInjectionConfig.model_validate(fi_config_data)

driver = ChactosDriver(
    testrun_dir=args.testrun_dir,
    work_dir=args.workdir_path,
    operator_config=operator_config,
    fault_injection_config=fi_config,
)
driver.run()
