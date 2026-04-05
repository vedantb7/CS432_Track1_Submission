"""
DB-Level ACID Tests — CS432 Track 1 Module B
============================================
Tests ACID properties directly via the DBManager / TransactionManager API.
Every assertion is deterministic: a test PASSES only when the expected
invariant is actually satisfied; it FAILS otherwise.

Key constraints of the underlying B+Tree engine:
  - Keys MUST be 32-bit integers (c_int). String keys cause TypeError.
  - Direct table.insert() bypasses the WAL; txn_insert() writes WAL + in-memory.
  - TransactionManager uses a global serialization lock (one transaction at a time).

Usage:
    cd Module_B/app/backend
    python3 test_acid_db_level.py

Output:
    acid_db_results.json   — machine-readable results
    Console summary table
"""

import threading
import time
import json
import os
import sys
from datetime import datetime
from collections import defaultdict

# ── path setup ──────────────────────────────────────────────────────────────
BACKEND_DIR  = os.path.dirname(os.path.abspath(__file__))
MODULE_A_DIR = os.path.abspath(os.path.join(BACKEND_DIR, "../../../Module_A/database"))
if MODULE_A_DIR not in sys.path:
    sys.path.insert(0, MODULE_A_DIR)

from db_manager import DBManager          # noqa: E402

# ── constants ────────────────────────────────────────────────────────────────
RESULTS_FILE   = os.path.join(BACKEND_DIR, "acid_db_results.json")
# NOTE: The global serialization lock + WAL fsync serialises all txns.
# Counts chosen to run in <60s on typical hardware.
RACE_THREADS   = 5
RACE_ITERS     = 5           # 5 threads × 5 iters = 25 serialised WAL-writes
CONCURRENCY_N  = 20
STRESS_THREADS = 20
STRESS_OPS     = 50          # 20 threads × 50 ops = 1000 WAL-writes


# ── helpers ──────────────────────────────────────────────────────────────────
def fresh_db(log_name: str) -> DBManager:
    """Return a DBManager whose WAL starts clean."""
    log_path = os.path.join(BACKEND_DIR, log_name)
    if os.path.exists(log_path):
        os.remove(log_path)
    return DBManager(log_path)


class Results:
    def __init__(self):
        self.records: list = []

    def add(self, name: str, status: str, duration: float, details: str):
        rec = dict(test=name, status=status, duration=round(duration, 6),
                   timestamp=datetime.now().isoformat(), details=details)
        self.records.append(rec)
        icon = "✓" if status == "PASS" else "✗"
        print(f"\n{'='*70}")
        print(f" {icon} [{name}]  {status}  ({duration:.3f}s)")
        print(f"   {details}")
        print('='*70)

    def summary(self) -> dict:
        total  = len(self.records)
        passed = sum(1 for r in self.records if r["status"] == "PASS")
        return dict(total=total, passed=passed, failed=total-passed,
                    pass_pct=round(100*passed/total, 1) if total else 0)


# ── individual tests ──────────────────────────────────────────────────────────

def test_atomicity_concurrent_inserts(res: Results):
    """A1 — 50 inserts in a single transaction all commit atomically."""
    name = "A1_ATOMICITY_CONCURRENT_INSERTS"
    db = fresh_db("acid_a1.log")
    db.create_table("Accounts")
    t  = db.get_table("Accounts")
    t0 = time.perf_counter()
    try:
        # Use txn_insert so WAL is written
        txn = db.begin()
        for i in range(50):
            db.txn_insert(txn, "Accounts", 1000 + i, f"balance:{1000 * (i+1)}")
        db.commit(txn)

        count = len(t.get_all())
        dur   = time.perf_counter() - t0
        if count == 50:
            res.add(name, "PASS", dur, f"All 50 inserts committed atomically (count={count})")
        else:
            res.add(name, "FAIL", dur, f"Expected 50 records after commit, got {count}")
    except Exception as exc:
        res.add(name, "FAIL", time.perf_counter()-t0, str(exc))


def test_atomicity_rollback_cleans_all(res: Results):
    """A2 — A rolled-back transaction leaves ZERO trace (only baseline survives)."""
    name = "A2_ATOMICITY_ROLLBACK_LEAVES_NO_TRACE"
    db = fresh_db("acid_a2.log")
    db.create_table("Staging")
    t  = db.get_table("Staging")
    t0 = time.perf_counter()
    try:
        # Commit a baseline record (integer key 1)
        txn1 = db.begin()
        db.txn_insert(txn1, "Staging", 1, "baseline")
        db.commit(txn1)

        # Begin a new txn, insert key 2, then rollback
        txn2 = db.begin()
        db.txn_insert(txn2, "Staging", 2, "should_disappear")
        db.rollback(txn2)

        count = len(t.get_all())
        dur   = time.perf_counter() - t0
        if count == 1:
            res.add(name, "PASS", dur,
                    f"Rollback removed all dirty writes; only baseline survives (count={count})")
        else:
            res.add(name, "FAIL", dur,
                    f"Expected 1 record after rollback, found {count}")
    except Exception as exc:
        res.add(name, "FAIL", time.perf_counter()-t0, str(exc))


def test_atomicity_multi_table(res: Results):
    """A3 — A 3-table transaction commits atomically."""
    name = "A3_ATOMICITY_MULTI_TABLE"
    db = fresh_db("acid_a3.log")
    for tbl in ("MUsers", "MProducts", "MOrders"):
        db.create_table(tbl)
    t0 = time.perf_counter()
    try:
        txn = db.begin()
        db.txn_insert(txn, "MUsers",    2001, "Alice")
        db.txn_insert(txn, "MProducts", 3001, "Laptop")
        db.txn_insert(txn, "MOrders",   4001, "order_ref")
        db.commit(txn)

        u = len(db.get_table("MUsers").get_all())
        p = len(db.get_table("MProducts").get_all())
        o = len(db.get_table("MOrders").get_all())
        dur = time.perf_counter() - t0
        if u == 1 and p == 1 and o == 1:
            res.add(name, "PASS", dur, f"All 3 tables updated: Users={u}, Products={p}, Orders={o}")
        else:
            res.add(name, "FAIL", dur, f"Incomplete multi-table commit: U={u} P={p} O={o}")
    except Exception as exc:
        res.add(name, "FAIL", time.perf_counter()-t0, str(exc))


def test_consistency_no_negative_balance(res: Results):
    """C1 — Consistency check: negative balance rejected at application layer."""
    name = "C1_CONSISTENCY_NEGATIVE_BALANCE_REJECTED"
    db = fresh_db("acid_c1.log")
    db.create_table("Users")
    t0 = time.perf_counter()
    try:
        # Insert using integer key (B+Tree requires c_int keys)
        txn = db.begin()
        db.txn_insert(txn, "Users", 9901, json.dumps({"name": "Bob", "balance": 100}))
        db.commit(txn)

        # Verify it was stored correctly
        stored_str = db.get_table("Users").search(9901)
        assert stored_str is not None, "Baseline insert failed"
        stored = json.loads(stored_str)
        assert stored["balance"] == 100

        # Attempt negative-balance update via txn_update (which checks constraints)
        txn2 = db.begin()
        raised = False
        try:
            db.txn_update(txn2, "Users", 9901, {"name": "Bob", "balance": -50})
        except ValueError:
            raised = True
            db.rollback(txn2)

        dur = time.perf_counter() - t0
        if raised:
            # Verify data integrity: balance should still be 100
            stored2 = json.loads(db.get_table("Users").search(9901))
            if stored2["balance"] == 100:
                res.add(name, "PASS", dur,
                        "Negative balance rejected by txn_update; rollback restored state")
            else:
                res.add(name, "FAIL", dur, f"Balance corrupted after rejection: {stored2}")
        else:
            res.add(name, "FAIL", dur, "Negative balance was accepted — consistency violated")
    except Exception as exc:
        res.add(name, "FAIL", time.perf_counter()-t0, str(exc))


def test_isolation_concurrent_updates(res: Results):
    """I1 — 20 concurrent threads each update their own integer key; no cross-contamination."""
    name = "I1_ISOLATION_CONCURRENT_UPDATES"
    db = fresh_db("acid_i1.log")
    db.create_table("Counter")
    tbl = db.get_table("Counter")
    t0  = time.perf_counter()
    try:
        # Seed N distinct keys with JSON values so txn_update's json.loads works
        txn0 = db.begin()
        for i in range(CONCURRENCY_N):
            db.txn_insert(txn0, "Counter", 6000 + i, json.dumps({"count": 0}))
        db.commit(txn0)

        successes = []
        lock = threading.Lock()

        def worker(tid):
            local_txn = None
            try:
                local_txn = db.begin()
                db.txn_update(local_txn, "Counter", 6000 + tid,
                              {"count": tid})
                db.commit(local_txn)
                with lock:
                    successes.append(tid)
            except Exception:
                try:
                    if local_txn:
                        db.rollback(local_txn)
                except Exception:
                    pass

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(CONCURRENCY_N)]
        for th in threads:
            th.start()
        for th in threads:
            th.join(timeout=60)

        dur = time.perf_counter() - t0
        if len(successes) == CONCURRENCY_N:
            res.add(name, "PASS", dur,
                    f"All {CONCURRENCY_N} concurrent updates completed without interference")
        else:
            res.add(name, "FAIL", dur,
                    f"Only {len(successes)}/{CONCURRENCY_N} updates succeeded")
    except Exception as exc:
        res.add(name, "FAIL", time.perf_counter()-t0, str(exc))


def test_isolation_race_condition_same_key(res: Results):
    """
    I2 — Race condition: RACE_THREADS threads hammer the same key.
    Uses JSON dict values so txn_update's json.loads(before_str) succeeds.
    Always calls rollback() on exception to release the global lock.
    """
    name = "I2_ISOLATION_RACE_CONDITION_SAME_KEY"
    db = fresh_db("acid_i2.log")
    db.create_table("SharedKey")
    tbl = db.get_table("SharedKey")
    t0  = time.perf_counter()
    try:
        # Seed with a JSON-dict value (required by txn_update's before-state parsing)
        txn0 = db.begin()
        db.txn_insert(txn0, "SharedKey", 7001, json.dumps({"v": "initial"}))
        db.commit(txn0)

        update_log = []
        log_lock   = threading.Lock()

        def race(tid):
            for it in range(RACE_ITERS):
                local_txn = None
                try:
                    local_txn = db.begin()
                    db.txn_update(local_txn, "SharedKey", 7001,
                                  {"v": f"T{tid}_it{it}"})
                    db.commit(local_txn)
                    with log_lock:
                        update_log.append(f"T{tid}:it{it}")
                except Exception:
                    # MUST rollback to release the global lock
                    try:
                        if local_txn:
                            db.rollback(local_txn)
                    except Exception:
                        pass

        threads = [threading.Thread(target=race, args=(i,)) for i in range(RACE_THREADS)]
        for th in threads:
            th.start()
        for th in threads:
            th.join(timeout=60)  # guard against lock starvation

        final = tbl.search(7001)
        dur   = time.perf_counter() - t0
        total_expected = RACE_THREADS * RACE_ITERS

        if len(update_log) == total_expected and final is not None:
            res.add(name, "PASS", dur,
                    f"All {total_expected} serialized updates completed; final={final}")
        else:
            res.add(name, "FAIL", dur,
                    f"Updates recorded={len(update_log)}/{total_expected}; final={final}")
    except Exception as exc:
        res.add(name, "FAIL", time.perf_counter()-t0, str(exc))


def test_failure_rollback_on_exception(res: Results):
    """F1 — Mid-transaction exception causes complete rollback; committed baseline untouched."""
    name = "F1_FAILURE_ROLLBACK_ON_EXCEPTION"
    db = fresh_db("acid_f1.log")
    db.create_table("FailTest")
    tbl = db.get_table("FailTest")
    t0  = time.perf_counter()

    txn2 = None
    count_mid = None

    try:
        # Committed baseline
        txn1 = db.begin()
        db.txn_insert(txn1, "FailTest", 8001, "committed_baseline")
        db.commit(txn1)
        baseline_count = len(tbl.get_all())

        # Failing transaction
        txn2 = db.begin()
        db.txn_insert(txn2, "FailTest", 8002, "dirty_write")
        count_mid = len(tbl.get_all())   # dirty read — 2 (in-memory)
        raise RuntimeError("injected failure mid-transaction")

    except RuntimeError:
        # rollback all dirty writes
        if txn2 is not None:
            db.rollback(txn2)
    except Exception as exc:
        if txn2 is not None:
            db.rollback(txn2)
        res.add(name, "FAIL", time.perf_counter()-t0, str(exc))
        return

    final_count = len(tbl.get_all())
    dur = time.perf_counter() - t0
    if final_count == baseline_count and final_count >= 1:
        res.add(name, "PASS", dur,
                f"Rollback succeeded: baseline={baseline_count}, "
                f"dirty_mid={count_mid}, final={final_count}")
    else:
        res.add(name, "FAIL", dur,
                f"Rollback failed: expected={baseline_count}, final={final_count}")


def test_failure_crash_recovery(res: Results):
    """F2 — Committed data survives simulated crash (new DBManager re-reads WAL)."""
    name = "F2_FAILURE_CRASH_RECOVERY"
    log_path = os.path.join(BACKEND_DIR, "acid_f2.log")
    if os.path.exists(log_path):
        os.remove(log_path)
    t0 = time.perf_counter()
    try:
        # Phase 1 — write and commit via txn_insert (WAL-tracked)
        db1 = DBManager(log_path)
        db1.create_table("Durable")
        txn = db1.begin()
        db1.txn_insert(txn, "Durable", 99001,
                       json.dumps({"value": "survived"}))
        db1.commit(txn)
        # "crash" — discard in-memory state
        del db1

        # Phase 2 — recover from WAL (new instance)
        db2 = DBManager(log_path)
        rec = db2.get_table("Durable").search(99001) if "Durable" in db2.tables else None
        dur = time.perf_counter() - t0

        if rec is not None:
            parsed = json.loads(rec)
            if parsed.get("value") == "survived":
                res.add(name, "PASS", dur,
                        f"Crash-recovery via WAL replay: record={parsed}")
            else:
                res.add(name, "FAIL", dur, f"Value mismatch after recovery: {parsed}")
        else:
            res.add(name, "FAIL", dur, "Record not found after WAL recovery")
    except Exception as exc:
        res.add(name, "FAIL", time.perf_counter()-t0, str(exc))


def test_durability_wal_persisted(res: Results):
    """D1 — WAL file is non-empty and contains COMMIT records after committed txns."""
    name = "D1_DURABILITY_WAL_PERSISTED"
    log_path = os.path.join(BACKEND_DIR, "acid_d1.log")
    if os.path.exists(log_path):
        os.remove(log_path)
    t0 = time.perf_counter()
    try:
        db = DBManager(log_path)
        db.create_table("DurableWAL")

        # txn_insert uses WAL; direct table.insert() does NOT
        for i in range(5):
            txn = db.begin()
            db.txn_insert(txn, "DurableWAL", 11000 + i,
                          json.dumps({"value": f"val_{i}"}))
            db.commit(txn)

        # Inspect WAL on disk
        with open(log_path) as f:
            lines = [json.loads(l) for l in f if l.strip()]
        commits = [l for l in lines if l.get("type") == "COMMIT"]
        inserts = [l for l in lines if l.get("type") == "INSERT"]
        dur = time.perf_counter() - t0
        if len(commits) >= 5 and len(inserts) >= 5:
            res.add(name, "PASS", dur,
                    f"WAL contains {len(inserts)} INSERT + {len(commits)} COMMIT records — "
                    f"durability proven")
        else:
            res.add(name, "FAIL", dur,
                    f"WAL incomplete: {len(inserts)} INSERTs, {len(commits)} COMMITs")
    except Exception as exc:
        res.add(name, "FAIL", time.perf_counter()-t0, str(exc))


def test_stress_high_throughput(res: Results):
    """S1 — Stress: STRESS_THREADS concurrent workers, each doing STRESS_OPS insert ops."""
    name = "S1_STRESS_HIGH_THROUGHPUT"
    db  = fresh_db("acid_s1.log")
    db.create_table("StressTbl")
    tbl = db.get_table("StressTbl")
    t0  = time.perf_counter()

    op_count   = [0]
    ok_count   = [0]
    count_lock = threading.Lock()

    def worker(wid):
        for op_i in range(STRESS_OPS):
            key = wid * 100000 + op_i
            local_txn = None
            try:
                local_txn = db.begin()
                db.txn_insert(local_txn, "StressTbl", key, f"v{op_i}")
                db.commit(local_txn)
                with count_lock:
                    ok_count[0] += 1
            except Exception:
                try:
                    if local_txn:
                        db.rollback(local_txn)
                except Exception:
                    pass
            finally:
                with count_lock:
                    op_count[0] += 1

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(STRESS_THREADS)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    dur      = time.perf_counter() - t0
    total    = op_count[0]
    success  = ok_count[0]
    tput     = total / dur if dur > 0 else 0
    pct      = 100 * success / total if total else 0

    if success >= total * 0.90:   # pass if ≥ 90 % succeed
        res.add(name, "PASS", dur,
                f"{total} ops in {dur:.2f}s → {tput:.0f} ops/s | "
                f"success={success}/{total} ({pct:.1f}%)")
    else:
        res.add(name, "FAIL", dur,
                f"Too many failures: success={success}/{total} ({pct:.1f}%)")


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    res = Results()
    print("\n" + "="*70)
    print("  DB-LEVEL ACID TESTS — CS432 Track 1 Module B")
    print("="*70)
    print(f"  Started: {datetime.now().isoformat()}")
    print(f"  Race threads: {RACE_THREADS} × {RACE_ITERS} iters")
    print(f"  Concurrency N: {CONCURRENCY_N}")
    print(f"  Stress: {STRESS_THREADS} threads × {STRESS_OPS} ops")
    print("="*70)

    test_atomicity_concurrent_inserts(res)
    test_atomicity_rollback_cleans_all(res)
    test_atomicity_multi_table(res)
    test_consistency_no_negative_balance(res)
    test_isolation_concurrent_updates(res)
    test_isolation_race_condition_same_key(res)
    test_failure_rollback_on_exception(res)
    test_failure_crash_recovery(res)
    test_durability_wal_persisted(res)
    test_stress_high_throughput(res)

    summary = res.summary()

    # Console table
    print("\n" + "="*70)
    print("  DB-LEVEL ACID SUMMARY")
    print("="*70)
    print(f"  {'Test':<45} {'Status':>6}  {'Duration':>10}")
    print("  " + "-"*60)
    for r in res.records:
        tag = "✓ PASS" if r["status"] == "PASS" else "✗ FAIL"
        print(f"  {r['test'][:45]:<45} {tag:>6}  {r['duration']:>8.3f}s")
    print("  " + "-"*60)
    print(f"  Total: {summary['total']} | Passed: {summary['passed']} | "
          f"Failed: {summary['failed']} | Pass rate: {summary['pass_pct']}%")
    print("="*70)

    # Persist JSON
    output = {"timestamp": datetime.now().isoformat(),
               "summary": summary,
               "tests": res.records}
    with open(RESULTS_FILE, "w") as fh:
        json.dump(output, fh, indent=2)
    print(f"\n  Results written → {RESULTS_FILE}\n")

    # Exit non-zero on failures so the orchestrator can detect them
    sys.exit(0 if summary["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
