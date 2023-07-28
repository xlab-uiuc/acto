from acto.config import actoConfig

if actoConfig.parallel.executor == 'ray':
    from ray import remote, get
else:
    from .ray_mock import remote, get
