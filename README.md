# Final Assignment — Real-Time Embedded Systems

AERO4 — 2025/2026
Eugénie Chevalier

## Files

- `multiplication.c` : task τ1 (large number multiplication)
- `measurement.py` : runs the C program 100 times and computes WCET stats
- `scheduler.py` : non-preemptive schedule search over the task set
- `Report_RealTime_Embedded_Systems_EN.pdf` : final report
- `gantt_part1.png`, `measurement_boxplot.png` : figures used in the report

## How to run

Compile the C task:

    gcc -O0 -o multiplication.exe multiplication.c

Measure WCET (100 runs):

    python measurement.py

Run the scheduler:

    python scheduler.py

Measurements were done on an AMD Ryzen 7 5800X, Windows 11.
