import json
import os

from acto.config import actoConfig


def load_monkey_patch(config: str):
    with open(config, 'r') as config_file:
        config = json.load(config_file)
        monkey_patch_load_path = os.path.expanduser('~/.acto_monkey_patch.rc')
        if 'monkey_patch' in config:
            with open(monkey_patch_load_path, 'w') as f:
                f.write(config['monkey_patch'])
        else:
            open(monkey_patch_load_path, 'w').write('')
        if actoConfig.ray.enabled:
            import ansible_runner

            ansible_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts',
                                       'ansible')
            ansible_runner.run(inventory=actoConfig.ray.ansible_inventory,
                               playbook=os.path.join(ansible_dir, 'monkey_patch.yaml'))
