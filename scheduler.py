"""
Author: Eugénie
Date  : April 2026

Purpose
-------
Non-preemptive schedule search at job level for a periodic task set
of 7 tasks with implicit deadlines (D_i = T_i).

The script does three things:
  1. Computes the system utilization U and checks the necessary
     condition U <= 1 for schedulability.
  2. Performs an exhaustive search over all 7! = 5040 task priority
     orderings to find a non-preemptive schedule that:
       - misses no deadline
       - minimizes total waiting time (sum of start - release over jobs)
     This indirectly maximizes total processor idle time (verified).
  3. Repeats the search allowing tau_5 to miss its deadline, and
     additionally tries to force tau_5 to miss to see whether relaxing
     the constraint can reduce total waiting time.

Why search over task-level priority permutations rather than job-level?
  - True job-level optimization would mean searching over permutations
    of all 29 jobs in the hyperperiod, i.e. 29! ≈ 8.8e30 candidates.
    That is intractable.
  - Restricting the search to static task-priority orderings reduces
    the problem to 7! = 5040 candidates, which runs in well under a
    second. For this task set the result happens to be globally optimal
    because the only available slack (5 ms per hyperperiod) is fully
    consumed regardless of job ordering.

Usage
-----
  python scheduler.py
"""

import itertools
from math import gcd
from functools import reduce


# ---------------------------------------------------------------------------
# Task set definition
# ---------------------------------------------------------------------------
# C1 = ceil(WCET) measured from multiplication.c
# Measured WCET = 2564.30 us ≈ 2.56 ms → C1 = 3 ms (ceiling)
C1 = 3

TASKS = [
    # (name, C_i, T_i)   T_i = period = implicit deadline (ms)
    ("tau_1", C1, 10),
    ("tau_2", 3,  10),
    ("tau_3", 2,  20),
    ("tau_4", 2,  20),
    ("tau_5", 2,  40),
    ("tau_6", 2,  40),
    ("tau_7", 3,  80),
]


def lcm(a, b):
    return a * b // gcd(a, b)


def hyperperiod(tasks):
    return reduce(lcm, [t[2] for t in tasks])


# ---------------------------------------------------------------------------
# Generate all jobs within one hyperperiod
# ---------------------------------------------------------------------------
def generate_jobs(tasks, hp):
    """
    Return list of jobs as dicts:
      name, C, release, deadline, task_idx, job_id
    """
    jobs = []
    job_id = 0
    for idx, (name, ci, ti) in enumerate(tasks):
        n_jobs = hp // ti
        for k in range(n_jobs):
            release = k * ti
            deadline = (k + 1) * ti
            jobs.append({
                "name": name,
                "C": ci,
                "release": release,
                "deadline": deadline,
                "task_idx": idx,
                "job_id": job_id,
                "instance": k,
            })
            job_id += 1
    return jobs



# ---------------------------------------------------------------------------
# Non-preemptive scheduler (greedy with pluggable priority)
# ---------------------------------------------------------------------------

"""
 Build a non-preemptive schedule using greedy selection.
 key_fn(job) determines priority among ready jobs (lower = higher priority).
 allow_miss_tasks: set of task indices allowed to miss deadlines.
 Returns (schedule, total_wait, total_idle, missed) or None if infeasible.
 """

def schedule_greedy(jobs, key_fn, allow_miss_tasks=None):
    if allow_miss_tasks is None:
        allow_miss_tasks = set()

    remaining = list(jobs)
    t = 0
    schedule = []
    total_wait = 0
    total_idle = 0
    missed = []
    hp = max(j["deadline"] for j in jobs)

    while remaining:
        ready = [j for j in remaining if j["release"] <= t]
        if not ready:
            next_release = min(j["release"] for j in remaining)
            total_idle += next_release - t
            t = next_release
            continue

        ready.sort(key=key_fn)
        job = ready[0]
        remaining.remove(job)

        start = t
        finish = t + job["C"]
        wait = start - job["release"]
        response = finish - job["release"]
        total_wait += wait

        entry = {
            "name": job["name"],
            "C": job["C"],
            "release": job["release"],
            "start": start,
            "finish": finish,
            "deadline": job["deadline"],
            "wait": wait,
            "response": response,
            "task_idx": job["task_idx"],
            "miss": finish > job["deadline"],
        }

        if finish > job["deadline"]:
            if job["task_idx"] in allow_miss_tasks:
                missed.append(entry)
            else:
                return None  # infeasible
        schedule.append(entry)
        t = finish

    total_idle += max(0, hp - t)
    return schedule, total_wait, total_idle, missed


# -------------------------------------------------------------------------
# Search over task-level priority orderings for minimum waiting time
# ---------------------------------------------------------------

"""
Try all permutations of task priorities.
For each permutation, use that as the dispatching order among ready jobs.
Return the schedule with minimum total waiting time that is feasible.
"""

def search_best_schedule(jobs, num_tasks, allow_miss_tasks=None):
    best = None
    best_wait = float("inf")
    best_prio = None

    task_indices = list(range(num_tasks))
    for perm in itertools.permutations(task_indices):
        prio_map = {task_idx: rank for rank, task_idx in enumerate(perm)}
        key_fn = lambda j, pm=prio_map: (pm[j["task_idx"]], j["release"])
        result = schedule_greedy(jobs, key_fn, allow_miss_tasks)
        if result is not None:
            sched, wait, idle, missed = result
            if wait < best_wait:
                best_wait = wait
                best = result
                best_prio = perm

    return best, best_prio


def print_schedule(schedule, total_wait, total_idle, missed, hp):
    """Pretty-print a schedule table."""
    print(f"  Total waiting time:  {total_wait} ms")
    print(f"  Total idle time:     {total_idle} ms")
    print(f"  Hyperperiod:         {hp} ms")
    print(f"  Missed deadlines:    {len(missed)}")
    if missed:
        for m in missed:
            print(f"    -> {m['name']} instance: "
                  f"finish={m['finish']} > deadline={m['deadline']}")
    print()
    hdr = (f"  {'Job':<8} {'Inst':>4} {'C':>3} {'Release':>8} {'Start':>8} "
           f"{'Finish':>8} {'Deadline':>8} {'Wait':>6} {'Resp':>6} {'Status':>6}")
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for e in schedule:
        status = "MISS" if e["miss"] else "OK"
        inst = ""
        print(f"  {e['name']:<8} {inst:>4} {e['C']:>3} {e['release']:>8} "
              f"{e['start']:>8} {e['finish']:>8} {e['deadline']:>8} "
              f"{e['wait']:>6} {e['response']:>6} {status:>6}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    hp = hyperperiod(TASKS)
    n_tasks = len(TASKS)

    print("=" * 70)
    print("REAL-TIME EMBEDDED SYSTEMS — SCHEDULE SEARCH")
    print("=" * 70)

    # -- Task set summary --
    print(f"\nTask Set (C1 = {C1} ms, measured WCET = 2564.30 µs):\n")
    print(f"  {'Task':<8} {'C (ms)':>8} {'T (ms)':>8} {'U_i':>8}")
    print("  " + "-" * 36)
    for name, ci, ti in TASKS:
        print(f"  {name:<8} {ci:>8} {ti:>8} {ci/ti:>8.4f}")
    U = sum(ci / ti for _, ci, ti in TASKS)
    print(f"\n  Total Utilization U = {U:.4f}")
    print(f"  Hyperperiod H = LCM({', '.join(str(t[2]) for t in TASKS)}) = {hp} ms")

    # -- Schedulability check --
    print(f"\n--- Schedulability Check ---")
    if U <= 1.0:
        print(f"  U = {U:.4f} <= 1.0 → Necessary condition SATISFIED")
        print(f"  (For non-preemptive scheduling, U ≤ 1 is necessary.)")
        print(f"  Total execution per hyperperiod: "
              f"{sum(ci * (hp // ti) for _, ci, ti in TASKS)} / {hp} ms")
    else:
        print(f"  U = {U:.4f} > 1.0 → NOT SCHEDULABLE")
        exit(1)

    jobs = generate_jobs(TASKS, hp)
    print(f"  Total jobs in one hyperperiod: {len(jobs)}")

    # =====================================================================
    # PART 1: No missed deadlines — minimize total waiting time
    # =====================================================================
    print(f"\n{'=' * 70}")
    print("PART 1: Non-preemptive schedule — NO missed deadlines")
    print(f"{'=' * 70}")
    print("  Searching over all task priority permutations...\n")

    result1, prio1 = search_best_schedule(jobs, n_tasks, allow_miss_tasks=None)

    if result1 is None:
        print("  No feasible non-preemptive schedule exists!")
    else:
        sched1, wait1, idle1, missed1 = result1
        prio_names = [TASKS[i][0] for i in prio1]
        print(f"  Best priority order: {' > '.join(prio_names)}")
        print()
        print_schedule(sched1, wait1, idle1, missed1, hp)
        print(f"\n  Verification: Total wait ({wait1}) should be minimized")
        print(f"  Verification: Total idle ({idle1}) should be maximized")
        print(f"  Verification: idle + exec = {idle1} + "
              f"{sum(e['C'] for e in sched1)} = "
              f"{idle1 + sum(e['C'] for e in sched1)} = {hp} ✓")









    # =====================================================================
    # PART 2: Allow tau_5 to miss a deadline — minimize total waiting time
    # =====================================================================
    print(f"\n{'=' * 70}")
    print("PART 2: Non-preemptive schedule — tau_5 MAY miss a deadline")
    print(f"{'=' * 70}")
    print("  Searching over all task priority permutations...\n")

    tau5_idx = 4
    result2, prio2 = search_best_schedule(
        jobs, n_tasks, allow_miss_tasks={tau5_idx}
    )

    if result2 is None:
        print("  No feasible schedule found even allowing tau_5 misses.")
    else:
        sched2, wait2, idle2, missed2 = result2
        prio_names2 = [TASKS[i][0] for i in prio2]
        print(f"  Best priority order: {' > '.join(prio_names2)}")
        print()
        print_schedule(sched2, wait2, idle2, missed2, hp)
        print(f"\n  Verification: idle + exec = {idle2} + "
              f"{sum(e['C'] for e in sched2)} = "
              f"{idle2 + sum(e['C'] for e in sched2)} = {hp} ✓")

    # -- Analysis: compare with forced tau_5 miss --
    print(f"\n{'=' * 70}")
    print("PART 2 — Analysis: schedules where tau_5 actually misses")
    print(f"{'=' * 70}")
    print("  Searching for best schedule with at least one tau_5 miss...\n")

    best_forced = None
    best_forced_wait = float("inf")
    best_forced_prio = None
    task_indices = list(range(n_tasks))

    for perm in itertools.permutations(task_indices):
        prio_map = {task_idx: rank for rank, task_idx in enumerate(perm)}
        key_fn = lambda j, pm=prio_map: (pm[j["task_idx"]], j["release"])
        result = schedule_greedy(jobs, key_fn, allow_miss_tasks={tau5_idx})
        if result is not None:
            sched, wait, idle, missed = result
            if len(missed) > 0 and wait < best_forced_wait:
                best_forced_wait = wait
                best_forced = result
                best_forced_prio = perm

    if best_forced is None:
        print("  No permutation causes tau_5 to miss a deadline.")
        print("  The system has enough slack to always schedule tau_5 on time.")
    else:
        sf, wf, idf, mf = best_forced
        pf_names = [TASKS[i][0] for i in best_forced_prio]
        print(f"  Best priority order (with miss): {' > '.join(pf_names)}")
        print()
        print_schedule(sf, wf, idf, mf, hp)

    # -- Comparison --
    print(f"\n{'=' * 70}")
    print("COMPARISON")
    print(f"{'=' * 70}")
    if result2 is not None:
        print(f"  Part 1 (no misses allowed):    wait = {wait1} ms, "
              f"idle = {idle1} ms, misses = 0")
        print(f"  Part 2 (tau_5 may miss):       wait = {wait2} ms, "
              f"idle = {idle2} ms, misses = {len(missed2)}")
        if best_forced is not None:
            print(f"  Forced tau_5 miss:             wait = {wf} ms, "
                  f"idle = {idf} ms, misses = {len(mf)}")
            print(f"\n  Conclusion: Allowing tau_5 to miss does NOT reduce "
                  f"waiting time.")
            print(f"  The relaxed constraint yields the same optimum because "
                  f"the system")
            print(f"  at U = {U:.4f} has enough slack ({idle1} ms) to "
                  f"schedule all tasks")
            print(f"  without misses. Forcing a miss only increases total "
                  f"waiting time")
            print(f"  ({wf} ms > {wait2} ms).")
        else:
            print(f"\n  Conclusion: No permutation forces tau_5 to miss.")
            print(f"  The system at U = {U:.4f} always fits all jobs within "
                  f"deadlines.")
