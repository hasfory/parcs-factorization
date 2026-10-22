#!/usr/bin/env python3
"""Локальна перевірка factorization.py без кластера (воркери - процеси).
    python3 local_run.py inputs/04_semiprime_1e16.txt [k]
Pyro4 не потрібен: підставляється заглушка декоратора @expose."""
import multiprocessing
import sys
import types

sys.modules["Pyro4"] = types.SimpleNamespace(expose=lambda f: f)
import factorization as fz


def _map(n, a, b):
    return fz.Solver.mymap(n, a, b)


class Future(object):
    def __init__(self, r):
        self.r = r

    @property
    def value(self):
        return self.r.get()


class Worker(object):
    def __init__(self, pool):
        self.pool = pool

    def mymap(self, n, a, b):
        return Future(self.pool.apply_async(_map, (n, a, b)))


if __name__ == "__main__":
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    pool = multiprocessing.Pool(k)
    fz.Solver([Worker(pool) for _ in range(k)], sys.argv[1], "local_output.txt").solve()
    print(open("local_output.txt").read())
