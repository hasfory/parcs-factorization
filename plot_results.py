#!/usr/bin/env python3
"""
Будує графіки для звіту з results.csv (його створює bench.py):
  time.png     - час паралельного алгоритму від кількості воркерів (+ час послідовного)
  speedup.png  - прискорення S(k) у порівнянні з ідеальним S = k

    pip3 install --user matplotlib   # якщо ще не встановлено
    python3 plot_results.py results.csv
"""
import csv
import sys
from collections import OrderedDict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

path = sys.argv[1] if len(sys.argv) > 1 else "results.csv"
data = OrderedDict()
for row in csv.DictReader(open(path)):
    d = data.setdefault(row["input"], {"k": [], "par": [], "S": [], "seq": float(row["T_seq_s"])})
    d["k"].append(int(row["workers"]))
    d["par"].append(float(row["T_par_s"]))
    d["S"].append(float(row["speedup"]))

fig, ax = plt.subplots(figsize=(7, 4.5))
for i, (name, d) in enumerate(data.items()):
    line, = ax.plot(d["k"], d["par"], "o-", label=name)
    ax.axhline(d["seq"], color=line.get_color(), ls=":", lw=1)
ax.set_xlabel("Кількість воркерів k")
ax.set_ylabel("Час, с")
ax.set_yscale("log")
ax.set_title("Час паралельного алгоритму (пунктир - послідовний)")
ax.grid(True, alpha=0.3)
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig("time.png", dpi=150)

fig, ax = plt.subplots(figsize=(7, 4.5))
kmax = max(max(d["k"]) for d in data.values())
ax.plot([1, kmax], [1, kmax], "k--", lw=1, label="ідеальне S = k")
for name, d in data.items():
    ax.plot(d["k"], d["S"], "o-", label=name)
ax.set_xlabel("Кількість воркерів k")
ax.set_ylabel("Прискорення S = T_seq / T_par")
ax.set_title("Прискорення паралельного алгоритму")
ax.grid(True, alpha=0.3)
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig("speedup.png", dpi=150)
print("Збережено time.png і speedup.png")
