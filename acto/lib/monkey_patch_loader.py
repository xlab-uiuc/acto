import os

from acto.config import actoConfig
from acto.lib.operator_config import OperatorConfig


def load_monkey_patch(config: OperatorConfig):
    monkey_patch_load_path = os.path.expanduser('~/.acto_monkey_patch.rc')
    if config.monkey_patch:
        with open(monkey_patch_load_path, 'w') as f:
            f.write(config.monkey_patch)
    else:
        open(monkey_patch_load_path, 'w').write('')

    if actoConfig.parallel.executor == 'ray':
        import ansible_runner

        ansible_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                   'scripts', 'ansible')
        ansible_runner.run(inventory=actoConfig.parallel.ansible_inventory,
                           playbook=os.path.join(ansible_dir, 'monkey_patch.yaml'))
    import acto.monkey_patch.monkey_patch
