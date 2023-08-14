import glob
import json
import os

import pytest

from acto.lib.operator_config import OperatorConfig

data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")


@pytest.mark.parametrize("path", glob.glob(os.path.join(data_dir, '**', 'config.json')))
def test_operator_config(path):
    """Check if all teh operator configs can be loaded"""
    OperatorConfig(**json.load(open(path)))
