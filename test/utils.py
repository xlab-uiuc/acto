import json

import yaml

from acto.snapshot import Snapshot


def construct_snapshot(trial_dir: str, generation: int):
    mutated_path = f'{trial_dir}/mutated-{generation}.yaml'
    operator_log_path = f'{trial_dir}/operator-{generation}.log'
    system_state_path = "%s/system-state-%03d.json" % (trial_dir, generation)
    cli_output_path = f'{trial_dir}/cli-output-{generation}.log'

    with open(mutated_path, 'r') as mutated_file, \
            open(operator_log_path, 'r') as operator_log_file, \
            open(system_state_path, 'r') as system_state_file, \
            open(cli_output_path, 'r') as cli_output_file:

        mutated = yaml.load(mutated_file, Loader=yaml.FullLoader)
        operator_log = operator_log_file.read().splitlines()
        system_state = json.load(system_state_file)
        cli_output = json.load(cli_output_file)

        return Snapshot(mutated, cli_output, system_state, operator_log)