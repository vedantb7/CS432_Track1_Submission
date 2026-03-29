import os
import json
import threading
from db_manager import DBManager

def cleanup():
    if os.path.exists("wal.log"):
        os.remove("wal.log")

def print_table_state(db, table_name, keys):
    table = db.get_table(table_name)
    if not table:
        print(f"Table {table_name} does not exist.")
        return
    for key in keys:
        val = table.search(key)
        print(f"  {table_name}[{key}] = {val}")

def test_atomicity_and_rollback():
    print("\n=== Scenario 1: Atomicity & Rollback ===")
    cleanup()
    db = DBManager("wal.log")
    
    # 1. Success Case: Commit a 3-table transaction
    print("Performing Transaction T1 (Commit)...")
    txn1 = db.begin()
    db.txn_insert(txn1, "Users", 1, {"name": "Alice", "balance": 1000})
    db.txn_insert(txn1, "Products", 101, {"name": "Laptop", "stock": 10})
    db.txn_insert(txn1, "Orders", 5001, {"user_id": 1, "product_id": 101})
    db.commit(txn1)
    
    print("State after T1 Commit:")
    print_table_state(db, "Users", [1])
    print_table_state(db, "Products", [101])
    print_table_state(db, "Orders", [5001])
    
    # 2. Rollback Case: Failure in a multi-table transaction
    print("\nStarting Transaction T2 (Update User, Update Product, Insert Order) then Rolling Back...")
    txn2 = db.begin()
    db.txn_update(txn2, "Users", 1, {"name": "Alice", "balance": 900})
    db.txn_update(txn2, "Products", 101, {"name": "Laptop", "stock": 9})
    db.txn_insert(txn2, "Orders", 5002, {"user_id": 1, "product_id": 101})
    
    print("Intermediate State (Before Rollback):")
    print_table_state(db, "Users", [1])
    print_table_state(db, "Products", [101])
    print_table_state(db, "Orders", [5002])
    
    print("\nRolling back Transaction T2...")
    db.rollback(txn2)
    
    print("Post-Rollback State (Should match state after T1 Commit):")
    print_table_state(db, "Users", [1])
    print_table_state(db, "Products", [101])
    print_table_state(db, "Orders", [5002]) # Should be None

def test_crash_recovery():
    print("\n=== Scenario 2: Crash Recovery & Durability ===")
    cleanup()
    db = DBManager("wal.log")
    
    # 1. Committed Transaction
    txn1 = db.begin()
    db.txn_insert(txn1, "Users", 1, {"name": "Alice", "balance": 1000})
    db.commit(txn1)
    
    # 2. Uncommitted Transaction (to be lost on "crash")
    txn2 = db.begin()
    db.txn_update(txn2, "Users", 1, {"name": "Alice", "balance": 500})
    
    print("State Before 'Crash':")
    print_table_state(db, "Users", [1])
    
    # Simulate crash by re-initializing DBManager
    print("\nSimulating Crash & Restarting DBManager (Recovery)...")
    db_recovered = DBManager("wal.log")
    
    print("State After Recovery:")
    # Alice's balance should be 1000 (from T1), T2's change (500) should be gone.
    print_table_state(db_recovered, "Users", [1])
    
    # Verify Durability: Restart again, should still be 1000
    print("\nRestarting again to verify Durability...")
    db_durability = DBManager("wal.log")
    print_table_state(db_durability, "Users", [1])

def test_isolation():
    print("\n=== Scenario 3: Isolation (Basic Locking) ===")
    cleanup()
    db = DBManager("wal.log")
    
    # Setup
    txn_setup = db.begin()
    db.txn_insert(txn_setup, "Accounts", 1, {"balance": 100})
    db.commit(txn_setup)
    
    results = []
    
    def transaction_a():
        txn = db.begin()
        # Simulate work
        import time
        val_str = db.get_table("Accounts").search(1)
        val = json.loads(val_str)
        val['balance'] += 50
        time.sleep(0.1)
        db.txn_update(txn, "Accounts", 1, val)
        db.commit(txn)
        results.append("A committed")

    def transaction_b():
        txn = db.begin()
        val_str = db.get_table("Accounts").search(1)
        val = json.loads(val_str)
        val['balance'] += 100
        db.txn_update(txn, "Accounts", 1, val)
        db.commit(txn)
        results.append("B committed")

    # Our TransactionManager uses a global lock, so they should be serialized
    # and the final balance should be 250 (100 + 50 + 100)
    
    t1 = threading.Thread(target=transaction_a)
    t2 = threading.Thread(target=transaction_b)
    
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    
    print(f"Final Account Balance: {db.get_table('Accounts').search(1)}")
    print(f"Order of completion: {results}")

def test_consistency():
    print("\n=== Scenario 4: Consistency Constraints ===")
    cleanup()
    db = DBManager("wal.log")
    
    txn = db.begin()
    db.txn_insert(txn, "Users", 1, {"name": "Alice", "balance": 100})
    db.commit(txn)
    
    txn2 = db.begin()
    try:
        # Try to set balance to negative
        db.txn_update(txn2, "Users", 1, {"name": "Alice", "balance": -50})
        db.commit(txn2)
    except ValueError as e:
        print(f"Caught Expected Exception: {e}")
        db.rollback(txn2)
        
    print(f"Final Balance after failed invalid update: {db.get_table('Users').search(1)}")

if __name__ == "__main__":
    test_atomicity_and_rollback()
    test_crash_recovery()
    test_isolation()
    test_consistency()
    cleanup()
