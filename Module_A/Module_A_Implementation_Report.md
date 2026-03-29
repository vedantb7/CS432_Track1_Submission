# Module A: ACID & Crash Recovery Implementation Report

**Date:** 2026-03-30  
**Project:** FreshWash DBMS - Indexing Engine Enhancement  
**Status:** Completed & Verified

---

## 1. Executive Summary
The objective was to transform a high-performance C++ B+ Tree indexing engine into a fully ACID-compliant transactional database system. This involved implementing Write-Ahead Logging (WAL), a Transaction Manager for atomic operations, startup Crash Recovery, and Serialization for Isolation. All goals outlined in the "One-Day Completion Plan" have been met and verified via a rigorous test suite.

---

## 2. Architectural Overview

The system follows a layered architecture:
1.  **Storage Engine (C++)**: A raw B+ Tree implementation providing $O(\log N)$ search, insert, and delete operations.
2.  **Abstraction Layer (Python/ctypes)**: Wraps the C++ shared library (`libdbms.so`) into a Pythonic `Table` interface.
3.  **Transaction & Log Layer (Python)**: The newly implemented logic that manages the lifecycle of transactions and ensures persistence.

### Key Components:
- **LogManager (`log_manager.py`)**: Manages the Write-Ahead Log (WAL). Every mutation is recorded here before being applied to the in-memory tree.
- **TransactionManager (`transaction_manager.py`)**: Generates transaction IDs, tracks undo actions for rollbacks, and manages the global serialization lock.
- **DBManager (`db_manager.py`)**: The central orchestrator. It handles recovery on startup and provides the Transactional API (`txn_insert`, `txn_update`, etc.).

---

## 3. Implementation Details

### 3.1 Write-Ahead Logging (WAL)
We adopted a **JSON Lines (JSONL)** format for the WAL to ensure human readability and ease of parsing during recovery.

**Code Logic (`log_manager.py`):**
```python
def append(self, record):
    self.lsn += 1
    record['lsn'] = self.lsn
    with open(self.log_file, "a") as f:
        f.write(json.dumps(record) + "
")
        f.flush()
        os.fsync(f.fileno()) # Guarantee Durability
    return self.lsn
```
The use of `os.fsync()` is critical; it forces the OS to flush the write buffer to the physical disk, satisfying the **Durability** requirement.

### 3.2 Transaction Management & Rollback
The `TransactionManager` tracks "Undo Actions" for every mutation performed within a transaction.

**Rollback Logic:**
When `rollback()` is called, the manager iterates through the transaction's history in **reverse order**:
- `INSERT` is undone by a `delete()`.
- `UPDATE` is undone by restoring the `before` image.
- `DELETE` is undone by re-inserting the `before` image.

### 3.3 Crash Recovery
Recovery is performed automatically when `DBManager` is initialized. It uses a **Two-Pass Algorithm**:
1.  **Analysis Pass**: Read the WAL to identify all transaction IDs that have a `COMMIT` record.
2.  **Redo Pass**: Iterate through the WAL again. For every operation belonging to a *committed* transaction, apply it to the B+ Tree.

Transactions that were "in-flight" (had a `BEGIN` but no `COMMIT`) at the time of the crash are ignored, effectively achieving **Atomicity**.

### 3.4 Isolation (Serialization)
To prevent race conditions and dirty reads, we implemented a **Global Transaction Lock**.
- `begin()` acquires the lock.
- `commit()` or `rollback()` releases the lock.
This ensures that only one transaction can mutate the database at a time, providing the highest level of Isolation (Serializable).

---

## 4. Testing & Validation (The `demo_acid.py` Suite)

We implemented five critical test scenarios to validate the engine.

### Scenario 1: Atomicity & Rollback
- **Action**: Update User balance (-100), Update Product stock (-1), and Insert an Order. Then trigger a rollback.
- **Result**: All three tables reverted to their exact initial state. The order was removed, and the balance/stock were restored.

### Scenario 2: Durability
- **Action**: Commit a transaction and then immediately shut down the `DBManager`.
- **Result**: Upon restart, the data was successfully reloaded from the WAL into the B+ Trees.

### Scenario 3: Crash Recovery
- **Action**: Simulate a crash where a transaction has written logs but didn't commit.
- **Result**: On restart, the recovery engine identified the "loser" transaction and did not apply its changes.

### Scenario 4: Isolation
- **Action**: Two concurrent threads attempted to increment a balance.
- **Result**: Due to the global lock, the operations were serialized. Final balance was exactly `Initial + ThreadA + ThreadB`.

### Scenario 5: Consistency Constraints
- **Action**: Attempt to set a user's balance to `-50`.
- **Result**: The `DBManager` raised a `ValueError`. The transaction was caught and rolled back, preserving the invariant that balances cannot be negative.

---

## 5. Challenges Encountered

### 5.1 C++ Wrapper String Handling
The B+ Tree engine expects C-style strings (`char*`). We had to ensure that Python dictionaries (representing records) were consistently serialized to JSON strings using `json.dumps()` before being passed to the C++ layer.

### 5.2 WAL Newline Parsing
During initial implementation, some `
` characters were misinterpreted by the shell tool, leading to malformed JSON in the WAL. This was resolved by switching to a robust `write_file` method that preserves literal newlines, ensuring each log record sits on its own line.

---

## 6. Final State of the Codebase

### New Files Created:
1.  `Module_A/database/log_manager.py`: The WAL engine.
2.  `Module_A/database/transaction_manager.py`: Transaction state and rollback logic.
3.  `Module_A/database/demo_acid.py`: The validation test suite.
4.  `Module_A/database/MODULE_A_EVIDENCE.md`: Structured evidence for grading.

### Modified Files:
1.  `Module_A/database/db_manager.py`: Integrated with Log and Transaction managers; added recovery logic.
2.  `readme.md`: Added instructions for running the ACID demo.
3.  `MODULE_A_ONE_DAY_PLAN.md`: Updated checklist to reflect 100% completion.

---

## 7. Conclusion
Module A is now a robust, transactional storage engine. While the core indexing is handled by high-performance C++, the Python management layer ensures that the system is resilient to crashes and maintains data integrity under concurrent access.

**To run the validation suite:**
```bash
cd Module_A/database/
python3 demo_acid.py
```
