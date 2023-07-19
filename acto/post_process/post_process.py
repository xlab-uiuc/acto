import glob
import json
import logging
import os
import pickle
from typing import Dict, TypeVar, Generic, Type

import yaml

from acto.utils import OperatorConfig
from acto.deploy import Deploy, YamlDeploy
from runner.trial import Trial

SomeDeploy = TypeVar('SomeDeploy', bound=Deploy)


class PostProcessor(Generic[SomeDeploy]):

    def __init__(self, testrun_dir: str, config: OperatorConfig, deploy_class: Type[SomeDeploy] = YamlDeploy):
        # Set config and context
        self.diff_ignore_fields = config.diff_ignore_fields
        context_cache = os.path.join(os.path.dirname(config.seed_custom_resource), 'context.json')
        with open(context_cache, 'r') as context_fin:
            self._context = json.load(context_fin)
            self._context['preload_images'] = set(self._context['preload_images'])
        self._deploy = deploy_class(config.deploy.file, config.deploy.init)
        try:
            with open(config.seed_custom_resource, 'r') as cr_file:
                self._seed = yaml.safe_load(cr_file)
        except:
            logging.error('Failed to read seed yaml, aborting')
            quit()
        # Initialize trials
        self._trials: Dict[str, Trial] = {}
        trial_paths = glob.glob(os.path.join(testrun_dir, '**', 'trial.pkl'))
        common_prefix = os.path.commonprefix(trial_paths)
        for trial_path in trial_paths:
            self._trials[trial_path[len(common_prefix):]] = pickle.load(open(trial_path, 'rb'))

    @property
    def trials(self):
        return self._trials
