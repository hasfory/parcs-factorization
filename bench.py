#!/usr/bin/env python3
"""
Автоматичне тестування на кластері PARCS-Python через його REST API.

Для кожного вхідного файлу:
  1) один раз запускає послідовний алгоритм (mode=seq) на майстрі;
  2) для кожної кількості воркерів k вмикає перші k воркерів (решту вимикає)
     і запускає паралельний алгоритм (mode=par).
Результати друкуються таблицею і зберігаються у results.csv.

Запуск (з Cloud Shell або з ПК, IP якого дозволена в брандмауері):
    export MASTER=http://<EXTERNAL_IP_майстра>:8080
    python3 bench.py inputs/04_semiprime_1e16.txt inputs/06_semiprime_1e18.txt --workers 1 2 3 4 5 6
"""
import argparse
import csv
import os
import re
import sys
import tempfile
import time

try:
    import requests
except ImportError:
    sys.exit("Потрібна бібліотека requests:  pip3 install --user requests")

HERE = os.path.dirname(os.path.abspath(__file__))
SOLUTION = os.path.join(HERE, "factorization.py")


def workers(master):
    r = requests.get(master + "/api/worker", timeout=10)
    r.raise_for_status()
    return sorted(w["id"] for w in r.json()["workers"])


def set_enabled(master, ids, k):
    for i, wid in enumerate(ids):
        state = "enable" if i < k else "disable"
        requests.post("%s/api/worker/%d/%s" % (master, wid, state), timeout=10).raise_for_status()


def last_job_id(master):
    html = requests.get(master + "/jobs", timeout=10).text
    ids = [int(x) for x in re.findall(r'data-job-id="(\d+)"', html)]
    return max(ids) if ids else None


def run_job(master, name, n, mode, timeout=3600):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("%d\n%s\n" % (n, mode))
        input_path = f.name
    try:
        with open(SOLUTION, "rb") as sol, open(input_path, "rb") as inp:
            requests.post(master + "/api/job", data={"job_name": name},
                          files={"solution_file": sol, "input_file": inp}, timeout=30).raise_for_status()
    finally:
        os.unlink(input_path)
    job_id = last_job_id(master)
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = requests.get("%s/api/job/%d/output" % (master, job_id), timeout=30)
        if r.status_code == 200:
            return r.text
        if r.status_code == 404:
            raise RuntimeError("Job #%d завершився з помилкою - дивіться вкладку Jobs" % job_id)
        time.sleep(2)
    raise RuntimeError("Job #%d: перевищено час очікування" % job_id)


def parse(text, tag):
    m = re.search(r"\[%s\]\s+time:\s+([\d.]+)" % tag, text)
    f = re.search(r"\[%s\]\s+factors:\s+(.+)" % tag, text)
    return float(m.group(1)), f.group(1).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+", help="вхідні файли (перший рядок - n)")
    ap.add_argument("--workers", nargs="+", type=int, default=None,
                    help="кількості воркерів для тестів (за замовчуванням 1..усі)")
    ap.add_argument("--master", default=os.environ.get("MASTER"), help="http://IP:8080")
    ap.add_argument("--out", default="results.csv")
    args = ap.parse_args()
    if not args.master:
        sys.exit("Задайте адресу майстра: export MASTER=http://<IP>:8080")
    master = args.master.rstrip("/")

    ids = workers(master)
    if not ids:
        sys.exit("До майстра не підключено жодного воркера")
    ks = args.workers or list(range(1, len(ids) + 1))
    ks = [k for k in ks if 1 <= k <= len(ids)]
    print("Воркерів у кластері: %d; тести для k = %s" % (len(ids), ks))

    rows = []
    try:
        for path in args.inputs:
            n = int(open(path).readline())
            name = os.path.splitext(os.path.basename(path))[0]
            set_enabled(master, ids, 1)
            print("\n%s: n = %d" % (name, n))
            t_seq, factors = parse(run_job(master, name + "-seq", n, "seq"), "sequential")
            print("  seq        : %9.3f s  %s" % (t_seq, factors))
            for k in ks:
                set_enabled(master, ids, k)
                t_par, factors_p = parse(run_job(master, "%s-par-%d" % (name, k), n, "par"), "parallel")
                s = t_seq / t_par if t_par > 0 else float("nan")
                print("  par k=%-3d  : %9.3f s  S=%5.2f  E=%4.2f  %s" % (
                    k, t_par, s, s / k, "OK" if factors_p == factors else "MISMATCH"))
                rows.append([name, n, factors, k, "%.3f" % t_seq, "%.3f" % t_par, "%.3f" % s, "%.3f" % (s / k)])
    finally:
        set_enabled(master, ids, len(ids))  # повертаємо всіх воркерів

    with open(args.out, "w") as f:
        w = csv.writer(f)
        w.writerow(["input", "n", "factors", "workers", "T_seq_s", "T_par_s", "speedup", "efficiency"])
        w.writerows(rows)
    print("\nЗбережено: %s" % args.out)


if __name__ == "__main__":
    main()
