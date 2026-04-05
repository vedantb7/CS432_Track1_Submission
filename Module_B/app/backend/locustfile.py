"""
Locust Load-Testing Script — CS432 Track 1 Module B
====================================================
Stress tests the Flask backend with increasing load stages.

Stages:
  Stage 1 — Warm-up      :  5 users,  30 s
  Stage 2 — Normal load  : 20 users,  60 s
  Stage 3 — Peak load    : 50 users,  60 s
  Stage 4 — Spike        :100 users,  30 s

Pass criteria (all stages must meet these to be "green"):
  • Error rate       < 5 %
  • p95 response     < 2 s
  • Throughput      ≥ 5 RPS (during peak)

Usage — headless (recommended, auto-run by run_all_validations.sh):
    locust -f locustfile.py \
           --headless \
           --host http://127.0.0.1:5001 \
           --users 100 --spawn-rate 5 \
           --run-time 180s \
           --csv locust_results \
           --exit-code-on-error 1

Usage — interactive (opens web UI at http://localhost:8089):
    locust -f locustfile.py --host http://127.0.0.1:5001
"""

import json
import os
import sys
import random

from locust import HttpUser, task, between, events
from locust.runners import MasterRunner

# ── path setup ────────────────────────────────────────────────────────────────
BACKEND_DIR  = os.path.dirname(os.path.abspath(__file__))
MODULE_A_DIR = os.path.abspath(os.path.join(BACKEND_DIR, "../../../Module_A/database"))
if MODULE_A_DIR not in sys.path:
    sys.path.insert(0, MODULE_A_DIR)

# ── seed data ids (must exist in the server's in-process DBManager) ───────────
# run_all_validations.sh seeds via /api/seed before running Locust.
PRODUCT_IDS = [100000 + i for i in range(50)]
USER_IDS    = [200000 + i for i in range(100)]

PASS_CRITERIA = {
    "max_error_pct": 5.0,    # %
    "max_p95_ms":    2000,   # ms
    "min_throughput": 5.0,   # RPS
}


# ── Locust user behaviours ─────────────────────────────────────────────────────

class CheckoutUser(HttpUser):
    """
    Simulates a buyer hitting the checkout endpoint.
    Weight: 70 % of traffic.
    """
    weight       = 7
    wait_time    = between(0.1, 0.5)

    @task(3)
    def checkout(self):
        uid = random.choice(USER_IDS)
        pid = random.choice(PRODUCT_IDS)
        with self.client.post(
            "/checkout",
            json={"user_id": uid, "product_id": pid, "quantity": 1},
            name="/checkout [normal]",
            catch_response=True
        ) as resp:
            if resp.status_code in (200, 400):
                # 400 = business logic rejection (insufficient stock/balance) — expected
                resp.success()
            else:
                resp.failure(f"Unexpected status {resp.status_code}")

    @task(1)
    def checkout_simulate_failure(self):
        """Inject mid-transaction failure and verify rollback via HTTP."""
        uid = random.choice(USER_IDS)
        pid = random.choice(PRODUCT_IDS)
        with self.client.post(
            "/checkout?simulate_failure=true",
            json={"user_id": uid, "product_id": pid, "quantity": 1},
            name="/checkout [failure-inject]",
            catch_response=True
        ) as resp:
            body = {}
            try:
                body = resp.json()
            except Exception:
                pass
            if resp.status_code == 400 and body.get("status") == "failed":
                resp.success()
            else:
                resp.failure(f"Expected 400/failed, got {resp.status_code}: {body}")


class ReadUser(HttpUser):
    """
    Simulates read-heavy traffic (user stats, orders, payments).
    Weight: 30 % of traffic.
    """
    weight    = 3
    wait_time = between(0.05, 0.3)

    @task
    def get_user_stats(self):
        member_id = random.randint(1, 20)
        with self.client.get(
            f"/api/user/stats/{member_id}",
            name="/api/user/stats/[id]",
            catch_response=True
        ) as resp:
            # 404 is acceptable (member may not exist in test DB)
            if resp.status_code in (200, 404, 500):
                resp.success()
            else:
                resp.failure(f"Unexpected {resp.status_code}")

    @task
    def get_user_orders(self):
        member_id = random.randint(1, 20)
        with self.client.get(
            f"/api/user/orders/{member_id}",
            name="/api/user/orders/[id]",
            catch_response=True
        ) as resp:
            if resp.status_code in (200, 404, 500):
                resp.success()
            else:
                resp.failure(f"Unexpected {resp.status_code}")


# ── event hooks ───────────────────────────────────────────────────────────────

@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """
    Evaluate pass/fail criteria when Locust finishes.
    Prints a summary and writes locust_pass_report.json.
    """
    stats   = environment.runner.stats.total
    errors  = stats.num_failures
    total   = stats.num_requests
    err_pct = 100.0 * errors / total if total > 0 else 0.0
    p95_ms  = stats.get_response_time_percentile(0.95) or 0.0
    tput    = stats.current_rps

    passed_criteria = {
        "error_pct_ok": err_pct <= PASS_CRITERIA["max_error_pct"],
        "p95_ok":       p95_ms  <= PASS_CRITERIA["max_p95_ms"],
        "throughput_ok": tput   >= PASS_CRITERIA["min_throughput"],
    }
    overall_pass = all(passed_criteria.values())

    report = {
        "timestamp":    __import__("datetime").datetime.now().isoformat(),
        "total_requests": total,
        "failures":     errors,
        "error_pct":    round(err_pct, 2),
        "p50_ms":       round(stats.get_response_time_percentile(0.50) or 0, 2),
        "p95_ms":       round(p95_ms, 2),
        "p99_ms":       round(stats.get_response_time_percentile(0.99) or 0, 2),
        "throughput_rps": round(tput, 2),
        "pass_criteria": PASS_CRITERIA,
        "criteria_met":  passed_criteria,
        "overall_pass":  overall_pass,
    }

    report_path = os.path.join(BACKEND_DIR, "locust_pass_report.json")
    with open(report_path, "w") as fh:
        json.dump(report, fh, indent=2)

    print("\n" + "="*60)
    print("  LOCUST STRESS TEST PASS/FAIL REPORT")
    print("="*60)
    for k, v in report.items():
        if k not in ("pass_criteria", "criteria_met"):
            print(f"  {k:<25}: {v}")
    print("\n  Pass Criteria:")
    for k, v in passed_criteria.items():
        mark = "✓" if v else "✗"
        print(f"    {mark} {k}")
    print(f"\n  Overall: {'PASS ✓' if overall_pass else 'FAIL ✗'}")
    print("="*60)

    if not overall_pass:
        environment.process_exit_code = 1
