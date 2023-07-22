import types

from acto.config import actoConfig

if actoConfig.ray.enabled:
    import ray

    remote = ray.remote
    get = ray.get
else:
    class MethodTypeWithRemote:
        def __init__(self, func, bound):
            self.__bound = bound
            self.__func = func
            self.remote = self

        def __call__(self, *args, **kwargs):
            return self.__func(self.__bound, *args, **kwargs)

    def _make_remote(runner):
        old_init = runner.__init__

        def __init__(self, *arg, **kwargs):
            old_init(self, *arg, **kwargs)
            self.run = MethodTypeWithRemote(self.run.__func__, self)
            self.teardown_cluster = MethodTypeWithRemote(self.teardown_cluster.__func__, self)

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
