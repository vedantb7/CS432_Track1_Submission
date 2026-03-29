# Module A ACID Evidence

This document provides evidence of the ACID compliance and crash recovery mechanisms implemented for the Module A indexing engine.

## 1. Atomicity
- **Scenario**: A multi-table transaction (T2) updates `Users` balance, `Products` stock, and inserts an `Order`. The transaction is then rolled back.
- **Steps**:
  1. Initialize `Users` and `Products`.
  2. Start `txn2`.
  3. Perform updates/inserts across 3 tables.
  4. Call `db.rollback(txn2)`.
- **Expected**: All changes in `txn2` are undone; state returns to pre-transaction values.
- **Observed**:
  ```
  Initial State:
    Users[1] = {"name": "Alice", "balance": 1000}
    Products[101] = {"name": "Laptop", "stock": 10}

  Starting Transaction T2...
  Intermediate State:
    Users[1] = {"name": "Alice", "balance": 900}
    Products[101] = {"name": "Laptop", "stock": 9}
    Orders[5001] = {"user_id": 1, "product_id": 101}

  Post-Rollback State:
    Users[1] = {"name": "Alice", "balance": 1000}
    Products[101] = {"name": "Laptop", "stock": 10}
    Orders[5001] = None
  ```
- **Verdict**: PASS

## 2. Consistency
- **Constraints checked**: Negative balance in `Users` and negative stock in `Products`.
- **Evidence**:
  ```
  Caught Expected Exception: Consistency Error: User 1 balance cannot be negative.
  Final Balance after failed invalid update: {"name": "Alice", "balance": 100}
  ```
- **Verdict**: PASS

## 3. Isolation
- **Concurrent scenario**: Two threads attempt to update the same account balance simultaneously.
- **Locking behavior**: Global serialization lock holds for the entire transaction lifetime.
- **Final state**:
  ```
  Final Account Balance: {"balance": 250}
  Order of completion: ['A committed', 'B committed']
  ```
- **Verdict**: PASS

## 4. Durability
- **Commit performed**: `txn1` inserts a user.
- **Restart method**: `DBManager` is re-initialized, replaying the WAL.
- **Post-restart state**:
  ```
  Restarting again to verify Durability...
    Users[1] = {"name": "Alice", "balance": 1000}
  ```
- **Verdict**: PASS

## 5. Recovery
- **Crash point**: Transaction `txn2` starts and updates a value but does not commit before the system "crashes" (re-initialization).
- **Uncommitted txn IDs**: `T2`
- **Undo actions applied**: Recovery replays only committed transactions, effectively undoing `T2`.
- **Final state**:
  ```
  Simulating Crash & Restarting DBManager (Recovery)...
  State After Recovery:
    Users[1] = {"name": "Alice", "balance": 1000}
  ```
- **Verdict**: PASS
