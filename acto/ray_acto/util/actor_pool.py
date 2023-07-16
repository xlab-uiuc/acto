import threading

from acto.config import actoConfig

if actoConfig.ray.enabled:
    import ray

    ActorPool = ray.util.ActorPool
else:
    from concurrent.futures import ThreadPoolExecutor


    class ActorPool:
        def __init__(self, actors: list):
            self._idle_actors = actors
            self._pending_submits = []
            self._result = []
            self._pool = ThreadPoolExecutor(max_workers=len(actors))
            self._result_count: threading.Semaphore = threading.Semaphore(value=0)

        def has_free(self) -> bool:
            return len(self._idle_actors) > 0

        def submit(self, fn, value):
            if self._idle_actors:
                actor = self._idle_actors.pop()
                future = self._pool.submit(fn, actor, value)
                future.add_done_callback(self.__make_callback_fn(actor))
            else:
                self._pending_submits.append((fn, value))

        def __make_callback_fn(self, runner):
            def cycle_runner(future):
                self._result.append(future.result())
                self._result_count.release()
                self._idle_actors.append(runner)
                if self._pending_submits:
                    (fn, value) = self._pending_submits.pop(0)
                    self.submit(fn, value)

            return cycle_runner

        def get_next_unordered(self):
            self._result_count.acquire()
            return self._result.pop()
