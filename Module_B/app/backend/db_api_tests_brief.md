# DB and API Test Brief

This file gives a short summary of all tests in:
- `test_acid_db_level.py`
- `test_acid_api_level.py`

## 1) DB-Level Tests (`test_acid_db_level.py`)

### A1_ATOMICITY_CONCURRENT_INSERTS
- Runs 50 inserts in one transaction.
- Verifies commit is all-or-nothing by checking final count is exactly 50.

### A2_ATOMICITY_ROLLBACK_LEAVES_NO_TRACE
- Inserts a baseline record, then inserts another record in a new transaction and rolls back.
- Verifies rollback removed uncommitted data and baseline remains.

### A3_ATOMICITY_MULTI_TABLE
- Writes to 3 tables (`MUsers`, `MProducts`, `MOrders`) inside one transaction.
- Verifies all 3 table updates appear after commit.

### C1_CONSISTENCY_NEGATIVE_BALANCE_REJECTED
- Inserts a valid user balance, then tries to update to a negative balance.
- Expects rejection and rollback, with original balance preserved.

### I1_ISOLATION_CONCURRENT_UPDATES
- Starts 20 concurrent threads updating different keys.
- Verifies all updates complete without cross-interference.

### I2_ISOLATION_RACE_CONDITION_SAME_KEY
- Multiple threads repeatedly update the same key.
- Verifies serialized updates and valid final value (no lost-write anomalies).

### F1_FAILURE_ROLLBACK_ON_EXCEPTION
- Injects exception mid-transaction after a dirty write.
- Verifies rollback restores committed baseline state.

### F2_FAILURE_CRASH_RECOVERY
- Commits data, discards in-memory state, recreates DBManager from WAL.
- Verifies committed record is recovered from WAL replay.

### D1_DURABILITY_WAL_PERSISTED
- Executes committed transactional inserts.
- Verifies WAL contains INSERT and COMMIT records on disk.

### S1_STRESS_HIGH_THROUGHPUT
- Runs concurrent stress workload (`STRESS_THREADS * STRESS_OPS`).
- Reports throughput and pass condition based on success ratio.

## 2) API-Level Tests (`test_acid_api_level.py`)

### API_A1_CONCURRENT_CHECKOUT_ATOMICITY
- Simulates many users checking out same product concurrently via HTTP.
- Verifies stock decrement equals number of successful orders.

### API_I1_RACE_CONDITION_LAST_UNIT
- Many buyers race to buy the last unit through `/checkout`.
- Verifies exactly one success and final stock becomes zero.

### API_F1_FAILURE_INJECTION_ROLLBACK
- Calls `/checkout?simulate_failure=true` to inject a mid-transaction failure.
- Verifies API failure response and rollback (stock and balance unchanged).

### API_C1_CONCURRENT_USERS_CONFIGURABLE
- Runs configurable virtual users with ramp-up against checkout API.
- Tracks latency percentiles and verifies all users complete successfully.

### API_D1_PROCESS_RESTART_DURABILITY
- Places order through API and verifies persisted order data via test query endpoint.
- Confirms committed data is present after operation.

## What these two suites together verify
- Atomicity: commit/rollback behavior at DB and API transaction flow levels.
- Consistency: invalid state (negative balance) is blocked.
- Isolation: concurrent operations and race scenarios are controlled.
- Durability: WAL persistence and recovery behavior are validated.
- Concurrency and stress: thread-heavy DB tests plus API-level concurrent user behavior.
