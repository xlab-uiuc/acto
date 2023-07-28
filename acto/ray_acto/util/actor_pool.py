from acto.config import actoConfig
from acto.lib.fp import unreachable

if actoConfig.parallel.executor == 'ray':
    from ray.util import ActorPool
elif actoConfig.parallel.executor == 'process':
    from .process_acto_pool import ActorPool
elif actoConfig.parallel.executor == 'thread':
    from .thread_acto_pool import ActorPool
else:
    unreachable()
