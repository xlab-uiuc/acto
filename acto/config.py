import os

import yaml

from acto.config_schema import Config

actoConfig: Config


def load_config(path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.yaml')):
    global actoConfig
    config = yaml.safe_load(open(path))
    actoConfig = Config.parse_obj(config)
    return actoConfig


load_config()
