"""
Final Evidence Report Generator — CS432 Track 1 Module B
=========================================================
Aggregates all test results (DB-level, API-level, Locust) into:
  - A human-readable Markdown report  (final_evidence_report.md)
  - A traceability matrix             (traceability_matrix.md)
  - An updated master JSON            (all_results.json)

Usage:
    python3 generate_final_report.py
"""

import json
import os
from datetime import datetime

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR    = os.path.abspath(os.path.join(BACKEND_DIR, "../../../../"))

FILES = {
    "db":     os.path.join(BACKEND_DIR, "acid_db_results.json"),
    "api":    os.path.join(BACKEND_DIR, "acid_api_results.json"),
    "locust": os.path.join(BACKEND_DIR, "locust_summary.json"),
}

TRACEABILITY = [
    # (req_id, requirement_text, test_name, how_to_run, expected, acid_layer)
    ("R1",  "Atomicity — all inserts commit or all rollback",
     "A1_ATOMICITY_CONCURRENT_INSERTS",
     "python3 test_acid_db_level.py",
     "count == 50 after commit",
     "DB"),

    ("R2",  "Atomicity — rolled-back txn leaves zero trace",
     "A2_ATOMICITY_ROLLBACK_LEAVES_NO_TRACE",
     "python3 test_acid_db_level.py",
     "count == 1 (baseline only) after rollback",
     "DB"),

    ("R3",  "Atomicity — multi-table transaction commits as one unit",
     "A3_ATOMICITY_MULTI_TABLE",
     "python3 test_acid_db_level.py",
     "Users=1, Products=1, Orders=1",
     "DB"),

    ("R4",  "Consistency — negative balance rejected, rollback restores state",
     "C1_CONSISTENCY_NEGATIVE_BALANCE_REJECTED",
     "python3 test_acid_db_level.py",
     "ValueError raised; balance stays at 100",
     "DB"),

    ("R5",  "Isolation — 20 concurrent threads update distinct keys without interference",
     "I1_ISOLATION_CONCURRENT_UPDATES",
     "python3 test_acid_db_level.py",
     "all 20 updates succeed",
     "DB"),

    ("R6",  "Isolation / Race condition — 10 threads × 10 iters on same key; 100 serialized updates",
     "I2_ISOLATION_RACE_CONDITION_SAME_KEY",
     "python3 test_acid_db_level.py",
     "update_log length == 100; final value valid",
     "DB"),

    ("R7",  "Failure simulation — mid-txn exception causes complete rollback",
     "F1_FAILURE_ROLLBACK_ON_EXCEPTION",
     "python3 test_acid_db_level.py",
     "final count == baseline count (rollback verified)",
     "DB"),

    ("R8",  "Durability / Crash recovery — committed data replayed by new DBManager from WAL",
     "F2_FAILURE_CRASH_RECOVERY",
     "python3 test_acid_db_level.py",
     "record 'rec_1' found after WAL replay",
     "DB"),

    ("R9",  "Durability — WAL contains ≥5 INSERT + COMMIT records on disk",
     "D1_DURABILITY_WAL_PERSISTED",
     "python3 test_acid_db_level.py",
     "inserts >= 5 and commits >= 5 in log file",
     "DB"),

    ("R10", "Stress — 100 concurrent threads × 100 ops, ≥90 % success rate",
     "S1_STRESS_HIGH_THROUGHPUT",
     "python3 test_acid_db_level.py",
     "≥9000/10000 ops succeed",
     "DB"),

    ("R11", "API Atomicity — concurrent checkout does not oversell (stock integrity)",
     "API_A1_CONCURRENT_CHECKOUT_ATOMICITY",
     "python3 test_acid_api_level.py",
     "remaining_stock == initial_stock - successful_orders",
     "API"),

    ("R12", "API Race condition — 15 threads race for last unit; exactly 1 wins",
     "API_I1_RACE_CONDITION_LAST_UNIT",
     "python3 test_acid_api_level.py",
     "successes==1, stock==0",
     "API"),

    ("R13", "API Failure injection — simulate_failure=true returns 400; stock & balance unchanged",
     "API_F1_FAILURE_INJECTION_ROLLBACK",
     "python3 test_acid_api_level.py",
     "HTTP 400, stock==initial, balance==initial",
     "API"),

    ("R14", "API Concurrent users — 20 virtual users (configurable) ramp-up, all succeed",
     "API_C1_CONCURRENT_USERS_CONFIGURABLE",
     "python3 test_acid_api_level.py",
     "failures==0; p95 < 2 s",
     "API"),

    ("R15", "API Durability — committed order persists in Orders table",
     "API_D1_PROCESS_RESTART_DURABILITY",
     "python3 test_acid_api_level.py",
     "order_id found in Orders B+Tree",
     "API"),

    ("R16", "Stress test — Locust 50 VU, 120 s, error rate <5 %, p95 <2 s, ≥5 RPS",
     "Locust — CheckoutUser + ReadUser",
     "python3 run_locust_headless.py",
     "all 3 pass criteria met",
     "Stress"),
]


def load(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def status_emoji(s):
    return "✅ PASS" if s == "PASS" else "❌ FAIL"


def generate():
    db_data     = load(FILES["db"])
    api_data    = load(FILES["api"])
    locust_data = load(FILES["locust"])

    def lookup_test(layer_data, test_name):
        if not layer_data:
            return None
        for t in layer_data.get("tests", []):
            if t["test"] == test_name:
                return t
        return None

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── TRACEABILITY MATRIX ──────────────────────────────────────────────────
    matrix_lines = [
        "# Traceability Matrix — CS432 Track 1 Module B",
        f"\n_Generated: {now}_\n",
        "| Req ID | Requirement | Test Name | How to Run | Expected Result | Layer | Actual Result |",
        "|--------|-------------|-----------|------------|-----------------|-------|---------------|",
    ]

    for (rid, req, tname, how, expected, layer) in TRACEABILITY:
        if layer == "DB":
            rec = lookup_test(db_data, tname)
        elif layer == "API":
            rec = lookup_test(api_data, tname)
        else:  # Locust
            rec = None

        if rec:
            actual = f"{status_emoji(rec['status'])}: {rec['details'][:60]}"
        elif layer == "Stress" and locust_data:
            if locust_data.get("overall_pass"):
                s = locust_data.get("stats", {})
                actual = (f"✅ PASS: p95={s.get('p95_ms')}ms, "
                          f"err={s.get('error_pct')}%, "
                          f"tput={s.get('throughput_rps')} RPS")
            else:
                actual = "❌ FAIL: see locust_summary.json"
        else:
            actual = "⚠️ Not run yet"

        matrix_lines.append(
            f"| {rid} | {req[:55]} | `{tname[:35]}` | `{how}` | {expected[:45]} | {layer} | {actual[:70]} |"
        )

    matrix_path = os.path.join(BACKEND_DIR, "traceability_matrix.md")
    with open(matrix_path, "w") as f:
        f.write("\n".join(matrix_lines))
    print(f"  ✓ Traceability matrix      → {matrix_path}")

    # ── HUMAN-READABLE EVIDENCE REPORT ───────────────────────────────────────
    db_sum     = db_data["summary"]     if db_data     else {}
    api_sum    = api_data["summary"]    if api_data    else {}
    loc_stats  = locust_data["stats"]   if locust_data else {}
    loc_met    = locust_data.get("criteria_met", {}) if locust_data else {}
    loc_pass   = locust_data.get("overall_pass", False) if locust_data else False

    overall_tests = (db_sum.get("total", 0) + api_sum.get("total", 0)
                     + (1 if locust_data else 0))
    overall_pass  = (db_sum.get("failed", 1) == 0
                     and api_sum.get("failed", 1) == 0
                     and loc_pass)

    md = f"""# Final Evidence Report — CS432 Track 1 Module B

_Generated: {now}_

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Report Date | {now} |
| Overall Result | {"**✅ ALL TESTS PASSED**" if overall_pass else "**❌ SOME TESTS FAILED**"} |
| DB-Level Tests | {db_sum.get('passed',0)}/{db_sum.get('total',0)} passed |
| API-Level Tests | {api_sum.get('passed',0)}/{api_sum.get('total',0)} passed |
| Stress Test (Locust) | {"PASS ✅" if loc_pass else "FAIL ❌" if locust_data else "Not run ⚠️"} |

---

## 1. DB-Level ACID Tests

"""
    if db_data:
        for r in db_data["tests"]:
            md += f"### {r['test']}\n"
            md += f"- **Status**: {status_emoji(r['status'])}\n"
            md += f"- **Duration**: {r['duration']:.3f}s\n"
            md += f"- **Details**: {r['details']}\n\n"
    else:
        md += "_No results found. Run `python3 test_acid_db_level.py` first._\n\n"

    md += "---\n\n## 2. API-Level ACID Tests\n\n"
    if api_data:
        for r in api_data["tests"]:
            md += f"### {r['test']}\n"
            md += f"- **Status**: {status_emoji(r['status'])}\n"
            md += f"- **Duration**: {r['duration']:.3f}s\n"
            md += f"- **Details**: {r['details']}\n"
            m = r.get("metrics", {})
            if m:
                md += "- **Metrics**:\n"
                for k, v in m.items():
                    md += f"  - `{k}`: {v}\n"
            md += "\n"
    else:
        md += "_No results found. Start Flask server and run `python3 test_acid_api_level.py` first._\n\n"

    md += "---\n\n## 3. Stress Test (Locust)\n\n"
    if locust_data:
        cfg = locust_data.get("config", {})
        md += f"- **Tool**: Locust\n"
        md += f"- **Virtual Users**: {cfg.get('users')}\n"
        md += f"- **Spawn Rate**: {cfg.get('spawn_rate')} VU/s\n"
        md += f"- **Duration**: {cfg.get('run_time')}\n\n"
        md += "| Metric | Value | Pass Threshold | Met |\n"
        md += "|--------|-------|---------------|-----|\n"
        md += f"| Total Requests | {loc_stats.get('total_requests')} | — | — |\n"
        md += f"| Failures | {loc_stats.get('failures')} | — | — |\n"
        md += f"| Error Rate | {loc_stats.get('error_pct')}% | <5% | {'✅' if loc_met.get('error_pct_ok') else '❌'} |\n"
        md += f"| p50 Response | {loc_stats.get('median_ms')}ms | — | — |\n"
        md += f"| p95 Response | {loc_stats.get('p95_ms')}ms | <2000ms | {'✅' if loc_met.get('p95_ok') else '❌'} |\n"
        md += f"| p99 Response | {loc_stats.get('p99_ms')}ms | — | — |\n"
        md += f"| Throughput | {loc_stats.get('throughput_rps')} RPS | ≥5 RPS | {'✅' if loc_met.get('throughput_ok') else '❌'} |\n"
        md += f"\n**Overall Locust result**: {'✅ PASS' if loc_pass else '❌ FAIL'}\n\n"
    else:
        md += "_No results found. Run `python3 run_locust_headless.py` first._\n\n"

    md += """---

## 4. ACID Property Coverage

| Property | DB Test | API Test | Stress Test |
|----------|---------|----------|-------------|
| **Atomicity** | A1, A2, A3 | API_A1 | Implicit (CheckoutUser) |
| **Consistency** | C1 | API_F1 (rollback) | Implicit |
| **Isolation** | I1, I2 | API_I1 (race) | Concurrent checkouts |
| **Durability** | F2, D1 | API_D1 | Implicit |

---

## 5. How to Reproduce All Results

```bash
# From CS432_Track1_Submission/Module_B/
bash VERIFY_COMPLETE.sh
```

Or step-by-step:
```bash
cd Module_B/app/backend/

# Step 1 — DB-level tests (no server needed)
python3 test_acid_db_level.py

# Step 2 — Start Flask server
python3 main.py &
sleep 3

# Step 3 — Seed data for API + Locust tests
curl -s -X POST http://127.0.0.1:5001/api/seed

# Step 4 — API-level ACID tests
python3 test_acid_api_level.py

# Step 5 — Locust stress test
python3 run_locust_headless.py

# Step 6 — Aggregate report
python3 generate_final_report.py
```

---

## 6. Remaining Risks & Limitations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Global serialization lock in TransactionManager | Limits true parallelism of DB-layer ops | Acceptable for educational DBMS; real systems use MVCC |
| In-process state reset between test runs | Tests must clean per-test tables | Use `fresh_db()` helper; each DB test uses isolated WAL |
| Locust RPS depends on machine speed | Threshold might not hold on slow CI | Threshold set conservatively (5 RPS); adjust via PASS_CRITERIA |
| PostgreSQL not required | API tests use B+Tree backend only | Consistent with assignment scope; PostgreSQL tested separately |

---
_Assignment: CS 432 – Database Assignment 3, Module B_
"""

    report_path = os.path.join(BACKEND_DIR, "final_evidence_report.md")
    with open(report_path, "w") as f:
        f.write(md)
    print(f"  ✓ Final evidence report    → {report_path}")

    # ── MASTER JSON ───────────────────────────────────────────────────────────
    master = {
        "timestamp": now,
        "overall_pass": overall_pass,
        "db_level":     db_data,
        "api_level":    api_data,
        "stress_test":  locust_data,
    }
    master_path = os.path.join(BACKEND_DIR, "all_results.json")
    with open(master_path, "w") as f:
        json.dump(master, f, indent=2)
    print(f"  ✓ Master results JSON      → {master_path}")


if __name__ == "__main__":
    print("\n  Generating final evidence report …\n")
    generate()
    print("\n  Done.\n")
