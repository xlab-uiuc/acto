import os

from acto.config_schema import Config

actoConfig: Config


def load_config(path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.yaml')):
    global actoConfig
    actoConfig: Config = Config.parse_file(path)


load_config()
