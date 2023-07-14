from acto.config import actoConfig

if actoConfig.ray.enabled:
    import ray

    remote = ray.remote
    get = ray.get
else:
    def remote(runner):
        old_init = runner.__init__

        def __init__(self, *arg, **kwargs):
            old_init(self, *arg, **kwargs)
            setattr(self.run.__func__, 'remote', self.run)

        setattr(runner, 'remote', runner)
        runner.__init__ = __init__
        return runner


    def get(foo):
        return foo
