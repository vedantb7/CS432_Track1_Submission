"""
Locust headless runner — CS432 Track 1 Module B
================================================
Runs Locust in headless mode, collects CSV output, and writes a
machine-readable JSON summary with p50/p95/p99/throughput/error-rate.

Usage (called by run_all_validations.sh):
    python3 run_locust_headless.py

Output:
    locust_results_stats.csv        — per-endpoint stats (from Locust)
    locust_results_stats_history.csv
    locust_results_failures.csv
    locust_pass_report.json         — overall pass/fail judgment
    locust_summary.json             — cleaned up summary for final report
"""

import subprocess
import sys
import os
import json
import time
import csv
import shutil

BACKEND_DIR  = os.path.dirname(os.path.abspath(__file__))
LOCUST_BIN   = shutil.which("locust") or os.path.expanduser("~/.local/bin/locust")

LOCUST_HOST  = "http://127.0.0.1:5001"
USERS        = 50       # peak users
SPAWN_RATE   = 5        # users added per second
RUN_TIME     = "120s"   # total test duration
CSV_PREFIX   = os.path.join(BACKEND_DIR, "locust_results")

PASS_CRITERIA = {
    "max_error_pct": 5.0,
    "max_p95_ms":    2000,
    "min_throughput": 5.0,
}


def run_locust():
    cmd = [
        LOCUST_BIN or "locust",
        "-f", os.path.join(BACKEND_DIR, "locustfile.py"),
        "--headless",
        "--host", LOCUST_HOST,
        "--users", str(USERS),
        "--spawn-rate", str(SPAWN_RATE),
        "--run-time", RUN_TIME,
        "--csv", CSV_PREFIX,
        "--logfile", os.path.join(BACKEND_DIR, "locust.log"),
        "--loglevel", "WARNING",
    ]

    print(f"\n  Running Locust: {' '.join(cmd)}\n")
    print(f"  Users: {USERS} | Spawn rate: {SPAWN_RATE}/s | Duration: {RUN_TIME}")

    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode


def parse_csv_results() -> dict:
    stats_csv = f"{CSV_PREFIX}_stats.csv"
    if not os.path.exists(stats_csv):
        return {}

    aggregated = {}
    with open(stats_csv, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Name") == "Aggregated":
                aggregated = row
                break

    if not aggregated:
        return {}

    def safe_float(key, default=0.0):
        try:
            return float(aggregated.get(key, default))
        except (ValueError, TypeError):
            return default

    total_req = safe_float("Request Count")
    failures  = safe_float("Failure Count")
    err_pct   = 100.0 * failures / total_req if total_req > 0 else 0.0

    return {
        "total_requests":  int(total_req),
        "failures":        int(failures),
        "error_pct":       round(err_pct, 2),
        "median_ms":       round(safe_float("Median Response Time"), 2),
        "p95_ms":          round(safe_float("95%ile Response Time"), 2),
        "p99_ms":          round(safe_float("99%ile Response Time"), 2),
        "avg_ms":          round(safe_float("Average Response Time"), 2),
        "min_ms":          round(safe_float("Min Response Time"), 2),
        "max_ms":          round(safe_float("Max Response Time"), 2),
        "throughput_rps":  round(safe_float("Requests/s"), 2),
        "failures_rps":    round(safe_float("Failures/s"), 2),
    }


def evaluate_criteria(stats: dict) -> dict:
    err_pct  = stats.get("error_pct", 999.0)
    p95      = stats.get("p95_ms",    999999.0)
    tput     = stats.get("throughput_rps", 0.0)

    met = {
        "error_pct_ok":  err_pct <= PASS_CRITERIA["max_error_pct"],
        "p95_ok":        p95     <= PASS_CRITERIA["max_p95_ms"],
        "throughput_ok": tput    >= PASS_CRITERIA["min_throughput"],
    }
    return met


def main():
    print("\n" + "="*70)
    print("  LOCUST STRESS TEST — CS432 Track 1 Module B")
    print("="*70)

    rc = run_locust()

    stats = parse_csv_results()
    met   = evaluate_criteria(stats)
    overall_pass = all(met.values()) and rc == 0

    print("\n" + "="*70)
    print("  LOCUST RESULTS SUMMARY")
    print("="*70)
    for k, v in stats.items():
        print(f"  {k:<25}: {v}")
    print()
    for k, ok in met.items():
        mark = "✓" if ok else "✗"
        print(f"  {mark} {k:<25} (threshold: {PASS_CRITERIA})")
    print(f"\n  Locust exit code: {rc}")
    print(f"  Overall: {'PASS ✓' if overall_pass else 'FAIL ✗'}")
    print("="*70)

    summary = {
        "timestamp":     __import__("datetime").datetime.now().isoformat(),
        "config": {
            "users":       USERS,
            "spawn_rate":  SPAWN_RATE,
            "run_time":    RUN_TIME,
            "host":        LOCUST_HOST,
        },
        "stats":           stats,
        "pass_criteria":   PASS_CRITERIA,
        "criteria_met":    met,
        "overall_pass":    overall_pass,
        "locust_exit_code": rc,
    }

    out_path = os.path.join(BACKEND_DIR, "locust_summary.json")
    with open(out_path, "w") as fh:
        json.dump(summary, fh, indent=2)
    print(f"\n  Results written → {out_path}")

    sys.exit(0 if overall_pass else 1)


if __name__ == "__main__":
    main()
