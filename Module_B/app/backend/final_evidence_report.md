# Final Evidence Report — CS432 Track 1 Module B

_Generated: 2026-04-05 17:00:20_

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Report Date | 2026-04-05 17:00:20 |
| Overall Result | **✅ ALL TESTS PASSED** |
| DB-Level Tests | 10/10 passed |
| API-Level Tests | 5/5 passed |
| Stress Test (Locust) | PASS ✅ |

---

## 1. DB-Level ACID Tests

### A1_ATOMICITY_CONCURRENT_INSERTS
- **Status**: ✅ PASS
- **Duration**: 0.109s
- **Details**: All 50 inserts committed atomically (count=50)

### A2_ATOMICITY_ROLLBACK_LEAVES_NO_TRACE
- **Status**: ✅ PASS
- **Duration**: 0.012s
- **Details**: Rollback removed all dirty writes; only baseline survives (count=1)

### A3_ATOMICITY_MULTI_TABLE
- **Status**: ✅ PASS
- **Duration**: 0.011s
- **Details**: All 3 tables updated: Users=1, Products=1, Orders=1

### C1_CONSISTENCY_NEGATIVE_BALANCE_REJECTED
- **Status**: ✅ PASS
- **Duration**: 0.010s
- **Details**: Negative balance rejected by txn_update; rollback restored state

### I1_ISOLATION_CONCURRENT_UPDATES
- **Status**: ✅ PASS
- **Duration**: 0.190s
- **Details**: All 20 concurrent updates completed without interference

### I2_ISOLATION_RACE_CONDITION_SAME_KEY
- **Status**: ✅ PASS
- **Duration**: 0.166s
- **Details**: All 25 serialized updates completed; final={"v": "T2_it4"}

### F1_FAILURE_ROLLBACK_ON_EXCEPTION
- **Status**: ✅ PASS
- **Duration**: 0.014s
- **Details**: Rollback succeeded: baseline=1, dirty_mid=2, final=1

### F2_FAILURE_CRASH_RECOVERY
- **Status**: ✅ PASS
- **Duration**: 0.007s
- **Details**: Crash-recovery via WAL replay: record={'value': 'survived'}

### D1_DURABILITY_WAL_PERSISTED
- **Status**: ✅ PASS
- **Duration**: 0.032s
- **Details**: WAL contains 5 INSERT + 5 COMMIT records — durability proven

### S1_STRESS_HIGH_THROUGHPUT
- **Status**: ✅ PASS
- **Duration**: 7.267s
- **Details**: 1000 ops in 7.27s → 138 ops/s | success=1000/1000 (100.0%)

---

## 2. API-Level ACID Tests

### API_A1_CONCURRENT_CHECKOUT_ATOMICITY
- **Status**: ✅ PASS
- **Duration**: 2.025s
- **Details**: Stock integrity preserved: 0 remaining (20 orders, 0 rejected)
- **Metrics**:
  - `virtual_users`: 20
  - `successful_orders`: 20
  - `failed_orders`: 0
  - `remaining_stock`: 0
  - `expected_stock`: 0
  - `p50_latency_s`: 1.0295
  - `p95_latency_s`: 1.9276
  - `p99_latency_s`: 1.9276

### API_I1_RACE_CONDITION_LAST_UNIT
- **Status**: ✅ PASS
- **Duration**: 0.299s
- **Details**: Race condition handled: exactly 1 buyer won, stock=0
- **Metrics**:
  - `race_buyers`: 15
  - `successes`: 1
  - `rejections`: 14
  - `final_stock`: 0

### API_F1_FAILURE_INJECTION_ROLLBACK
- **Status**: ✅ PASS
- **Duration**: 0.052s
- **Details**: Simulated failure returned 400; stock & balance rolled back correctly
- **Metrics**:
  - `http_status`: 400
  - `response`: {'error': 'Simulated Failure', 'status': 'failed'}
  - `stock_before`: 50
  - `stock_after`: 50
  - `balance_before`: 500.0
  - `balance_after`: 500.0

### API_C1_CONCURRENT_USERS_CONFIGURABLE
- **Status**: ✅ PASS
- **Duration**: 2.049s
- **Details**: All 20 virtual users completed successfully | p95=0.040s | 9.8 tx/s
- **Metrics**:
  - `virtual_users`: 20
  - `ramp_up_sec`: 2
  - `successes`: 20
  - `failures`: 0
  - `p50_latency_s`: 0.0284
  - `p95_latency_s`: 0.0396
  - `p99_latency_s`: 0.0396
  - `throughput_rps`: 9.76

### API_D1_PROCESS_RESTART_DURABILITY
- **Status**: ✅ PASS
- **Duration**: 0.038s
- **Details**: Order 537167 committed and persisted in Orders table

---

## 3. Stress Test (Locust)

- **Tool**: Locust
- **Virtual Users**: 50
- **Spawn Rate**: 5 VU/s
- **Duration**: 120s

| Metric | Value | Pass Threshold | Met |
|--------|-------|---------------|-----|
| Total Requests | 15329 | — | — |
| Failures | 0 | — | — |
| Error Rate | 0.0% | <5% | ✅ |
| p50 Response | 110.0ms | — | — |
| p95 Response | 0.0ms | <2000ms | ✅ |
| p99 Response | 0.0ms | — | — |
| Throughput | 128.47 RPS | ≥5 RPS | ✅ |

**Overall Locust result**: ✅ PASS

---

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
