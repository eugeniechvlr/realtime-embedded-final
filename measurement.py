"""
Author: Eugénie
Date  : April 2026

Purpose
-------
Runs the C multiplication program (task tau_1) a fixed number of times
and computes basic statistics on its execution time:
  Min, Q1, Q2 (median), Q3, Max
The maximum observed value is used as an empirical estimate of the WCET (C1).

Usage
-----
  1. Compile the C task once:
       gcc -O0 -o multiplication.exe multiplication.c
  2. Run this script:
       python measurement.py

"""

import subprocess
import statistics
import sys
import os

EXECUTABLE = os.path.join(os.path.dirname(__file__), "multiplication.exe")
NUM_RUNS = 100 
# 100 runs is a reasonable trade-off: enough samples to see a stable
# distribution, but fast enough to finish in a few seconds.


def collect_times(exe_path, num_runs):
    times = []
    for i in range(num_runs):
        result = subprocess.run(
            exe_path, capture_output=True, text=True, check=True
        )
        # The C program prints its own measured execution time in microseconds
        t = float(result.stdout.strip())
        times.append(t)
        if (i + 1) % 10 == 0:
            print(f"  Run {i + 1}/{num_runs} done ({t:.2f} us)")
    return sorted(times)


def quartiles(data):
    n = len(data)
    q1 = statistics.median(data[: n // 2])
    q2 = statistics.median(data)
    q3 = statistics.median(data[(n + 1) // 2 :])
    return q1, q2, q3


if __name__ == "__main__":
    if not os.path.isfile(EXECUTABLE):
        print(f"Error: {EXECUTABLE} not found. Compile first:")
        print("  gcc -O0 -o multiplication multiplication.c")
        sys.exit(1)

    print(f"Collecting {NUM_RUNS} execution times...\n")
    times = collect_times(EXECUTABLE, NUM_RUNS)

    q1, q2, q3 = quartiles(times)
    wcet = max(times)

    print(f"\n--- Results (microseconds) ---")
    print(f"  Min : {min(times):.2f}")
    print(f"  Q1  : {q1:.2f}")
    print(f"  Q2  : {q2:.2f} (median)")
    print(f"  Q3  : {q3:.2f}")
    print(f"  Max : {max(times):.2f}")
    print(f"  WCET (C1) = {wcet:.2f} us")
    print(f"  Mean: {statistics.mean(times):.2f}")
    print(f"  Stdev: {statistics.stdev(times):.2f}")
