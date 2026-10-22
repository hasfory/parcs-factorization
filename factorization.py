# -*- coding: utf-8 -*-
"""
Факторизація числа методом пробних дільників на PARCS-Python.
Послідовний алгоритм: Solver.factorize_sequential
Паралельний алгоритм: Solver.factorize_parallel (map: mymap, reduce: myreduce)

Вхідний файл: 1-й рядок - n, 2-й (необов'язковий) - режим: both | seq | par.
"""
from __future__ import division
import time
from Pyro4 import expose

try:
    range = xrange      # Python 2
except NameError:
    pass


def isqrt(n):
    """Цілий квадратний корінь (метод Ньютона)."""
    x = 1 << ((n.bit_length() + 1) // 2)
    while True:
        y = (x + n // x) // 2
        if y >= x:
            return x
        x = y


def next_divisor(n, start, stop):
    """Найменший непарний d з [start, stop), що ділить n, або None.
    Цей цикл спільний для обох алгоритмів - порівняння часу чесне."""
    for d in range(start, stop, 2):
        if n % d == 0:
            return d
    return None


def show(factors):
    return " * ".join(str(f) for f in factors)


class Solver:
    def __init__(self, workers=None, input_file_name=None, output_file_name=None):
        self.workers = workers
        self.input_file_name = input_file_name
        self.output_file_name = output_file_name

    def solve(self):
        with open(self.input_file_name) as f:
            lines = f.read().split()
        n = int(lines[0])
        mode = lines[1] if len(lines) > 1 else "both"
        k = len(self.workers)
        out = ["n = %d" % n, "workers = %d" % k, ""]
        t_seq = t_par = None

        if mode in ("both", "seq"):
            t = time.time()
            seq = Solver.factorize_sequential(n)
            t_seq = time.time() - t
            out += ["[sequential] factors: " + show(seq), "[sequential] time:    %.3f s" % t_seq]

        if mode in ("both", "par"):
            t = time.time()
            par = self.factorize_parallel(n)
            t_par = time.time() - t
            out += ["[parallel]   factors: " + show(par), "[parallel]   time:    %.3f s" % t_par]

        if t_seq is not None and t_par is not None:
            s = t_seq / t_par
            out += ["", "results match: " + ("YES" if seq == par else "NO"),
                    "speedup S = %.3f, efficiency E = %.3f" % (s, s / k)]

        with open(self.output_file_name, "w") as f:
            f.write("\n".join(out) + "\n")

    # ---------------- послідовний алгоритм ----------------
    @staticmethod
    def factorize_sequential(n):
        factors = []
        m = n
        while m % 2 == 0:
            factors.append(2)
            m //= 2
        d = 3
        while True:
            d = next_divisor(m, d, isqrt(m) + 1)    # межа зменшується разом з m
            if d is None:
                break
            while m % d == 0:
                factors.append(d)
                m //= d
        if m > 1:
            factors.append(m)
        return factors

    # ---------------- паралельний алгоритм ----------------
    def factorize_parallel(self, n):
        k = len(self.workers)
        lo, hi = 2, isqrt(n) + 1                    # шукаємо дільники в [lo, hi)
        step = max(1, (hi - lo) // k)

        # MAP: кожен воркер перевіряє свою частину відрізка (виклики асинхронні)
        mapped = []
        for i in range(k):
            a = lo + i * step
            b = hi if i == k - 1 else min(hi, a + step)
            if a < b:
                mapped.append(self.workers[i].mymap(str(n), str(a), str(b)))

        # REDUCE + побудова розкладу з усіх знайдених дільників
        factors = []
        m = n
        for d in Solver.myreduce(mapped):
            while m % d == 0:
                factors.append(d)
                m //= d
        if m > 1:
            factors.append(m)
        return factors

    @staticmethod
    @expose
    def mymap(n, a, b):
        """Воркер: усі дільники n у відрізку [a, b). Числа передаються рядками."""
        n, a, b = int(n), int(a), int(b)
        found = [2] if a <= 2 < b and n % 2 == 0 else []
        d = next_divisor(n, max(3, a | 1), b)       # a | 1 - найближче непарне >= a
        while d is not None:
            found.append(d)
            d = next_divisor(n, d + 2, b)
        return [str(d) for d in found]

    @staticmethod
    @expose
    def myreduce(mapped):
        """Збирає результати воркерів (.value чекає на завершення) і сортує."""
        return sorted(int(d) for chunk in mapped for d in chunk.value)
