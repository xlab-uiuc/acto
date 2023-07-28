import threading
from multiprocessing import Pool


class ActorPool:
    def __init__(self, actors: list):
        self._idle_actors = actors
        self._total_actors = len(actors)
        self._pending_submits = []
        self._result = []
        self._pool = Pool(len(actors))
        self._result_count: threading.Semaphore = threading.Semaphore(value=0)

    @property
    def pool(self):
        return self._pool

    def has_free(self) -> bool:
        return len(self._idle_actors) > 0

    def has_next(self) -> bool:
        return len(self._idle_actors) != self._total_actors or len(self._result) != 0

    def submit(self, fn, value):
        assert self._pool is not None, "The pool has been closed."
        if self._idle_actors:
            actor = self._idle_actors.pop()
            self._pool.apply_async(fn, (actor, value),
                                   callback=self.__make_callback_fn(actor),
                                   error_callback=self.__make_error_callback_fn(actor))
        else:
            self._pending_submits.append((fn, value))

    def __make_callback_fn(self, runner):
        def cycle_runner(result):
            self._result.append(result)
            self._result_count.release()
            self._idle_actors.append(runner)
            if self._pending_submits:
                (fn, value) = self._pending_submits.pop(0)
                self.submit(fn, value)

        return cycle_runner

    def __make_error_callback_fn(self, runner):
        def error_callback(error):
            print(error, flush=True)
            self._idle_actors.append(runner)
            if self._pending_submits:
                (fn, value) = self._pending_submits.pop(0)
                self.submit(fn, value)
        return error_callback

    def get_next_unordered(self):
        self._result_count.acquire()
        return self._result.pop()

    def pop_idle(self):
        """Removes an idle actor from the pool.

        Returns:
            An idle actor if one is available.
            None if no actor was free to be removed.
        """
        if self.has_free():
            self._total_actors -= 1
            if self._total_actors == 0:
                self._pool.close()
                self._pool = None
            return self._idle_actors.pop()
        return None

    def push(self, actor):
        """Pushes a new actor into the current list of idle actors.
        """
        self._idle_actors.append(actor)
        self._total_actors += 1
