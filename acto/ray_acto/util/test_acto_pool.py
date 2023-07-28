import time
from typing import Protocol, Type

import pytest

import acto.ray_acto.ray_mock
from acto.ray_acto.util import process_acto_pool, thread_acto_pool


class ActorPool(Protocol):
    def __init__(self, actors: list):
        pass

    def has_free(self) -> bool:
        pass

    def has_next(self) -> bool:
        pass

    def submit(self, fn, value):
        pass

    def get_next_unordered(self):
        pass

    def pop_idle(self):
        pass

    def push(self, actor):
        pass


@acto.ray_acto.ray_mock.remote
class Foo:
    def __init__(self, base: int):
        self.base = base

    def add(self, x, y):
        return self.base + x + y

    def slow_add(self, x, y):
        time.sleep(1)
        return self.add(x, y)


def execute_slow_add(actor: Foo, data):
    x, y = data
    return actor.slow_add(x, y)


@pytest.mark.timeout(10)
@pytest.mark.parametrize("cls", [thread_acto_pool.ActorPool, process_acto_pool.ActorPool])
def test_has_free(cls: Type[ActorPool]):
    actors = [Foo(1)]
    pool = cls(actors)
    assert pool.has_free()
    pool.submit(execute_slow_add, (2, 3))
    assert not pool.has_free()
    assert pool.get_next_unordered() == 6
    assert pool.has_free()
    assert pool.pop_idle()
    assert not pool.has_free()


@pytest.mark.timeout(10)
@pytest.mark.parametrize("cls", [process_acto_pool.ActorPool, thread_acto_pool.ActorPool])
def test_has_next(cls: Type[ActorPool]):
    actors = [Foo(1) for _ in range(10)]
    pool = cls(actors)
    pool.submit(execute_slow_add, (2, 3))
    assert pool.has_next()
    assert pool.get_next_unordered() == 6
    assert not pool.has_next()


@pytest.mark.timeout(10)
@pytest.mark.parametrize("cls", [process_acto_pool.ActorPool, thread_acto_pool.ActorPool])
def test_submit(cls: Type[ActorPool]):
    actors = [Foo(1), Foo(1)]
    pool = cls(actors)
    pool.submit(execute_slow_add, (2, 3))
    pool.submit(execute_slow_add, (2, 3))
    pool.submit(execute_slow_add, (2, 3))
    assert pool.get_next_unordered() == 6
    assert pool.get_next_unordered() == 6
    assert pool.get_next_unordered() == 6
