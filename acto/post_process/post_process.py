from abc import abstractmethod
import glob
import hashlib
import json
import os
import sys
from typing import Dict, List
import yaml

sys.path.append('.')
sys.path.append('..')

from acto.common import RunResult, oracle_result_from_dict
from acto.utils import OperatorConfig

class Step:
    '''A step in a trial
    
    Attributes:
        input (Dict): input to the operator
        operator_log (str): operator log
        system_state (Dict): system state
        cli_output (str): cli output
        runtime_result (Dict): runtime result
    '''

    def __init__(self, trial_dir: str, gen: int, input: Dict, operator_log: str, system_state: Dict,
                 cli_output: str, runtime_result: Dict):
        self._trial_dir = trial_dir
        self._gen = gen
        self._input = input
        self._input_digest = hashlib.md5(json.dumps(input,
                                                    sort_keys=True).encode("utf-8")).hexdigest()
        self._operator_log = operator_log
        self._system_state = system_state
        self._cli_output = cli_output
        self._runtime_result = RunResult.from_dict(runtime_result)

    @property
    def trial_dir(self) -> str:
        return self._trial_dir

    @property
    def gen(self) -> int:
        return self._gen

    @property
    def input(self) -> Dict:
        return self._input

    @property
    def input_digest(self) -> str:
        return self._input_digest

    @property
    def operator_log(self) -> str:
        return self._operator_log

    @property
    def system_state(self) -> Dict:
        return self._system_state

    @property
    def cli_output(self) -> str:
        return self._cli_output

    @property
    def runtime_result(self) -> RunResult:
        return self._runtime_result


def read_trial_dir(trial_dir: str) -> List[Step]:
    '''Read a trial directory and return a list of steps'''

    steps: List[Step] = []
    for generation in range(0, 20):
        if not os.path.exists('%s/mutated-%d.yaml' % (trial_dir, generation)):
            break

        step = construct_step(trial_dir, generation)
        if step is None:
            continue
        else:
            steps.append(step)

    return steps


def construct_step(trial_dir, generation) -> Step:
    events_log_path = "%s/events.log" % (trial_dir)
    mutated_filename = '%s/mutated-%d.yaml' % (trial_dir, generation)
    operator_log_path = "%s/operator-%d.log" % (trial_dir, generation)
    system_state_path = "%s/system-state-%03d.json" % (trial_dir, generation)
    cli_output_path = "%s/cli-output-%d.log" % (trial_dir, generation)
    runtime_result_path = "%s/generation-%d-runtime.json" % (trial_dir, generation)

    if not os.path.exists(operator_log_path):
        return None

    if not os.path.exists(runtime_result_path):
        return None

    with open(mutated_filename, 'r') as input_file, \
            open(operator_log_path, 'r') as operator_log_file, \
            open(system_state_path, 'r') as system_state_file, \
            open(events_log_path, 'r') as events_log, \
            open(cli_output_path, 'r') as cli_output, \
            open(runtime_result_path, 'r') as runtime_result_file:

        input = yaml.load(input_file, Loader=yaml.FullLoader)
        operator_log = operator_log_file.read().splitlines()
        system_state = json.load(system_state_file)
        cli_result = json.load(cli_output)
        runtime_result = json.load(runtime_result_file)

        return Step(trial_dir, generation, input, operator_log, system_state, cli_result,
                    runtime_result)


class PostProcessor(object):

    def __init__(self, testrun_dir: str, config: OperatorConfig):
        # Set config and context
        self.config = config
        context_cache = os.path.join(os.path.dirname(config.seed_custom_resource), 'context.json')
        with open(context_cache, 'r') as context_fin:
            self._context = json.load(context_fin)
            self._context['preload_images'] = set(self._context['preload_images'])

        # Initliaze trial dirs
        self._trials: List[str] = []
        self._trial_to_steps: Dict[str,
                                   List[Step]] = {}  # trial_dir -> steps, key by trial_dir string
        trial_dirs = glob.glob(testrun_dir + '/*')
        for trial_dir in trial_dirs:
            if not os.path.isdir(trial_dir):
                continue
            else:
                self._trials.append(trial_dir)
                self._trial_to_steps[os.path.basename(trial_dir)] = read_trial_dir(trial_dir)

    @property
    def trials(self) -> List[str]:
        return self._trials

    @trials.setter
    def trials(self, value):
        self._trials = value

    @property
    def trial_to_steps(self) -> Dict[str, List[Step]]:
        return self._trial_to_steps

    @property
    def context(self) -> Dict:
        return self._context

    @abstractmethod
    def post_process(self):
        raise NotImplementedError