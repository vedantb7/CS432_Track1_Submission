# Module A — One-Day Completion Plan
**Repository:** `vedantb7/CS432_Track1_Submission`  
**Date:** 2026-03-30  
**Target:** Complete **Module A (ACID Validation + Crash Recovery)** in one day with demonstrable evidence.

---

## 0) What must be true by end of day (Definition of Done)

- [x] At least **3 relations** exist, each stored in its own **B+ Tree**
- [x] Primary key is B+ Tree key, full record is value
- [x] No shadow/copy DB outside B+ Tree as primary storage
- [x] `BEGIN`, `COMMIT`, `ROLLBACK` work
- [x] One transaction updates **3 tables** atomically
- [x] WAL logging exists (begin/update/insert/delete/commit/rollback)
- [x] Crash recovery restores correctness:
  - [x] Undo incomplete txns
  - [x] Keep committed txns
- [x] Isolation mechanism exists (basic locking or serial execution)
- [x] Durability shown (committed state persists after restart)
- [x] Evidence file + runnable tests/script ready

---

## 1) Fast architecture (minimal, acceptable for grading)

Implement only what is needed to satisfy Module A reliably.

## 1.1 Components to add (minimum)
1. `TransactionManager` (Added)
2. `LogManager` (WAL append + flush) (Added)
3. `RecoveryManager` (startup undo/redo policy) (Added)
4. `LockManager` (coarse lock acceptable today) (Added)
5. Transactional wrappers around B+ Tree operations (Added)

---

## 2) Time-boxed schedule (single-day sprint)

## Block A (0.5h): Repo prep
- [x] Create branch: `module-a-final`
- [x] Add files:
  - [x] `MODULE_A_ONE_DAY_PLAN.md` (this file)
  - [x] `MODULE_A_EVIDENCE.md`
  - [x] `tests/module_a/` or `scripts/module_a_demo.*`
- [x] Identify existing files where B+ Tree insert/update/delete are implemented

## Block B (1.5h): Transaction + WAL skeleton
- [x] Add txn states: `ACTIVE`, `COMMITTED`, `ABORTED`
- [x] Implement:
  - [x] `begin() -> txn_id`
  - [x] `commit(txn_id)`
  - [x] `rollback(txn_id)`
- [x] Add WAL file (e.g., `wal.log`)
- [x] Log record formats (JSON lines strongly recommended)

**Required log record types:**
- `BEGIN`
- `UPDATE` (with `before` and `after`)
- `INSERT` (with `after`)
- `DELETE` (with `before`)
- `COMMIT`
- `ROLLBACK`

## Block C (2h): Wrap all writes in transaction layer
- [x] Replace direct B+ Tree writes with transactional methods:
  - [x] `txn_insert(txn_id, table, key, value)`
  - [x] `txn_update(txn_id, table, key, new_value)`
  - [x] `txn_delete(txn_id, table, key)`
- [x] Enforce WAL rule:
  - [x] Log record must be written/flushed before data page/tree mutation
- [x] Track per-txn operations for rollback replay

## Block D (1.5h): Rollback + Recovery
- [x] `rollback(txn_id)`:
  - [x] Replay txn’s log records in reverse
  - [x] For `UPDATE`, restore `before`
  - [x] For `INSERT`, delete key
  - [x] For `DELETE`, restore `before`
  - [x] Write `ROLLBACK`
- [x] `recover()` on startup:
  - [x] Parse WAL
  - [x] Build committed txn set
  - [x] For txns without COMMIT, undo in reverse order
  - [x] Ensure committed data remains

## Block E (1h): Isolation (minimal acceptable)
Pick one quick option:
- [x] Option 1: Global DB lock per transaction (serialized txns)
- [ ] Option 2: Table-level lock map

For same-key conflicts, ensure second txn waits/fails cleanly (either acceptable if deterministic and documented).

## Block F (1.5h): Mandatory demonstration scenario + tests
Implement one end-to-end transaction touching 3 tables:

**Example transaction**
1. Update `Users.balance -= amount`
2. Update `Products.stock -= qty`
3. Insert into `Orders`

- [x] Success case: all 3 persist after COMMIT + restart
- [x] Failure case: inject failure after step 2, verify rollback of all
- [x] Concurrent case: two txns attempt same user/product update; no corruption
- [x] Recovery case: crash before commit, restart => partial changes undone

## Block G (1h): Evidence and submission materials
- [x] Fill `MODULE_A_EVIDENCE.md`
- [x] Add command list in README:
  - [x] run app
  - [x] run module A tests/demo
  - [x] simulate crash/restart
- [x] Record short demo video clips (later for full submission)

---

## 3) Exact implementation checklist (copy/paste task tracker)

## 3.1 Transaction manager
- [x] Generate unique `txn_id`
- [x] Store in-memory txn map: `{txn_id: state}`
- [x] `begin()` writes `BEGIN` log
- [x] `commit()` flushes all pending logs, writes `COMMIT`
- [x] `rollback()` executes undo and writes `ROLLBACK`

## 3.2 Log manager (WAL)
- [x] JSONL log writer
- [x] `append(record)`
- [x] `flush()` (fsync if possible)
- [x] Timestamps + sequence number

**Suggested JSON log examples**
```json
{"lsn":1,"type":"BEGIN","txn":"T1","ts":"2026-03-29T10:00:00Z"}
{"lsn":2,"type":"UPDATE","txn":"T1","table":"Users","key":"U1","before":{"balance":1000},"after":{"balance":900}}
{"lsn":3,"type":"COMMIT","txn":"T1","ts":"2026-03-29T10:00:01Z"}
```

## 3.3 Transactional data operations
- [x] Read current record from B+ Tree before update/delete
- [x] Validate constraints before applying:
  - [x] no negative balance
  - [x] no negative stock
  - [x] valid foreign refs (e.g., Orders.user_id exists)
- [x] Log before mutation
- [x] Apply mutation

## 3.4 Recovery
- [x] Parse WAL start→end
- [x] Collect txns with COMMIT
- [x] Identify loser txns (begun but not committed)
- [x] Undo loser txn actions in reverse LSN order
- [x] Save corrected state

## 3.5 Isolation
- [x] Acquire lock at txn begin (or per table/key)
- [x] Hold locks until commit/rollback (strict 2PL style)
- [x] Release locks after txn completion

---

## 4) ACID validation matrix (what you must prove today)

| ACID Property | What to implement | What to show as evidence |
|---|---|---|
| Atomicity | rollback all-or-nothing for multi-table txn | crash/failure after step 2; all 3 tables unchanged |
| Consistency | enforce constraints each txn | balances/stocks never negative; refs valid |
| Isolation | lock/serialize conflicting txns | concurrent update test gives correct final value |
| Durability | commit persisted to disk | restart after commit retains changes |

---

## 5) Mandatory test cases (minimum set)

- [x] `test_begin_commit_three_table_transaction`
- [x] `test_rollback_three_table_transaction_on_failure`
- [x] `test_crash_recovery_undo_uncommitted`
- [x] `test_durability_after_restart`
- [x] `test_isolation_conflicting_transactions`
- [x] `test_consistency_constraints_enforced`

If no formal test framework exists, implement as scripts and print PASS/FAIL clearly.

---

## 6) Crash injection plan (quick and deterministic)

Use one deterministic fault flag:

- `INJECT_FAIL_AFTER_STEP=2`

In transaction flow:
1. update user
2. update product
3. if flag triggered -> throw exception / simulate crash
4. order insert never happens
5. on restart recovery should undo steps 1 and 2

- [x] Add this flag
- [x] Document usage in README
- [x] Capture before/after table snapshots

---

## 7) Evidence template to fill (create MODULE_A_EVIDENCE.md)

Use this exact structure:

1. **Atomicity**
   - Scenario:
   - Steps:
   - Expected:
   - Observed:
   - Verdict: PASS/FAIL

2. **Consistency**
   - Constraints checked:
   - Evidence:
   - Verdict:

3. **Isolation**
   - Concurrent scenario:
   - Locking behavior:
   - Final state:
   - Verdict:

4. **Durability**
   - Commit performed:
   - Restart method:
   - Post-restart state:
   - Verdict:

5. **Recovery**
   - Crash point:
   - Uncommitted txn IDs:
   - Undo actions applied:
   - Final state:
   - Verdict:

---

## 8) Final pre-submit checklist (tonight)

- [x] All module A scripts/tests passing
- [x] No direct writes bypassing txn layer
- [x] WAL file generated and readable
- [x] Recovery runs automatically on startup
- [x] README updated with run commands
- [x] Evidence markdown complete
- [x] Commit with clear messages:
  - [x] `feat: add WAL and transaction manager`
  - [x] `feat: add crash recovery and rollback`
  - [x] `test: add module A ACID validation scenarios`
  - [x] `docs: add module A evidence and run guide`

---

## 9) If time is running out (priority order)

Do these in this exact order:
1. **Atomicity + Rollback (3-table txn)**
2. **Durability (commit persists after restart)**
3. **Recovery undo uncommitted**
4. **Basic isolation via global lock**
5. **Consistency constraints**
6. Nice-to-have cleanup/refactor

---

## 10) Deliverables to keep ready for report/video later

- [x] WAL excerpt showing BEGIN/UPDATE/COMMIT
- [x] WAL excerpt showing BEGIN/UPDATE/CRASH/UNDO
- [x] Before/after snapshots of 3 tables
- [x] Short terminal run demonstrating restart recovery
- [x] List of assumptions/limitations
