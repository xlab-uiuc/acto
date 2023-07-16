from acto.config import actoConfig

if actoConfig.ray.enabled:
    import ray

    remote = ray.remote
    get = ray.get
else:
    def _make_remote(runner):
        old_init = runner.__init__

        def __init__(self, *arg, **kwargs):
            old_init(self, *arg, **kwargs)
            setattr(self.run.__func__, 'remote', self.run)

        setattr(runner, 'remote', runner)
        runner.__init__ = __init__
        return runner


    def remote(*args, **kwargs):
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            # This is the case where the decorator is just @ray.remote.
            # "args[0]" is the class or function under the decorator.
            return _make_remote(args[0])
        return _make_remote


    def get(foo):
        return foo
