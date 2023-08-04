import os
import time

from .ray import remote, get
from acto.config import actoConfig


def start_service():
    if actoConfig.parallel.executor == 'ray':
        import ansible_runner
        import ray

        ansible_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                   'scripts', 'ansible')
        ansible_runner.run(inventory=actoConfig.parallel.ansible_inventory,
                           playbook=os.path.join(ansible_dir, 'acto_ray.yaml'))
        head_result = ansible_runner.run(inventory=actoConfig.parallel.ansible_inventory,
                                         playbook=os.path.join(ansible_dir, 'ray_head.yaml'))
        ansible_runner.run(inventory=actoConfig.parallel.ansible_inventory,
                           playbook=os.path.join(ansible_dir, 'ray_worker.yaml'))
        if head_result.stats['changed'] != {}:
            time.sleep(5)
        ray.init(address='auto')
