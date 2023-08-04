import os

from acto.config import actoConfig
from acto.lib.operator_config import OperatorConfig

def patch_process_pool():
    import sys
    import dill
    # pickle cannot serialize closures, so we use dill instead
    # https://stackoverflow.com/questions/19984152/what-can-multiprocessing-and-dill-do-together
    dill.Pickler.dumps, dill.Pickler.loads = dill.dumps, dill.loads
    from multiprocessing import reduction
    reduction.ForkingPickler = dill.Pickler
    reduction.dump = dill.dump
    assert 'multiprocessing.connection' not in sys.modules

def load_monkey_patch(config: OperatorConfig):
    monkey_patch_load_path = os.path.expanduser('~/.acto_monkey_patch.rc')
    if config.monkey_patch:
        with open(monkey_patch_load_path, 'w') as f:
            f.write(config.monkey_patch)
    else:
        open(monkey_patch_load_path, 'w').write('')

    if actoConfig.parallel.executor == 'process':
        patch_process_pool()

    if actoConfig.parallel.executor == 'ray':
        import ansible_runner

        ansible_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                   'scripts', 'ansible')
        ansible_runner.run(inventory=actoConfig.parallel.ansible_inventory,
                           playbook=os.path.join(ansible_dir, 'monkey_patch.yaml'))
    import acto.monkey_patch.monkey_patch
