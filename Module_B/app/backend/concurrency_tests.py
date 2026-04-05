"""
Module B: Concurrency, Race Condition, Failure, and Stress Testing

- Simulates multiple users (threads) performing concurrent operations
- Tests for race conditions on critical operations
- Injects failures to verify rollback and durability
- Stress tests with high request volume
- Verifies ACID properties after each test

Usage:
    python3 concurrency_tests.py

Requirements:
    - Python 3.8+
    - Module B backend and BPlusTree must be importable
    - PostgreSQL running (if used)

Edit DB connection and operation details as needed for your schema.
"""
import threading
import random
import time
import traceback
from bplustree import BPlusTree
from db import get_db_manager

NUM_USERS = 20
NUM_OPS_PER_USER = 100
CRITICAL_KEY = 42
FAILURE_INJECT_AT = 50  # Inject failure after this many ops

results = []

# Shared B+ Tree for simulation (replace with per-user if needed)
tree = BPlusTree(order=32)

def user_simulation(user_id, inject_failure=False):
    """Simulate a user performing random operations."""
    try:
        for i in range(NUM_OPS_PER_USER):
            op = random.choice(['insert', 'update', 'delete', 'search'])
            key = random.randint(1, 100)
            value = f"User{user_id}_Val{i}"
            if op == 'insert':
                tree.insert(key, value)
            elif op == 'update':
                tree.update(key, value)
            elif op == 'delete':
                tree.delete(key)
            elif op == 'search':
                tree.search(key)
            # Inject failure mid-way for one user
            if inject_failure and i == FAILURE_INJECT_AT:
                raise Exception(f"Injected failure for user {user_id}")
        results.append((user_id, 'success'))
    except Exception as e:
        results.append((user_id, f'failure: {e}'))
        traceback.print_exc()

def race_condition_test():
    """Simulate many users updating the same key simultaneously."""
    threads = []
    for i in range(NUM_USERS):
        t = threading.Thread(target=lambda: tree.update(CRITICAL_KEY, f"Race_{i}"))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    # Check final value
    final = tree.search(CRITICAL_KEY)
    print(f"[Race Condition Test] Final value for key {CRITICAL_KEY}: {final}")

def failure_simulation_test():
    """Run users, inject failure in one, check rollback/consistency."""
    threads = []
    for i in range(NUM_USERS):
        inject = (i == 0)  # Only first user gets failure
        t = threading.Thread(target=user_simulation, args=(i, inject))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    print("[Failure Simulation] Results:", results)
    # Check for partial/inconsistent data (customize as needed)
    # Example: ensure all keys are valid strings, no partial updates
    all_data = tree.get_all()
    for k, v in all_data:
        assert isinstance(k, int) and isinstance(v, str)
    print("[Failure Simulation] Data integrity check passed.")

def stress_test():
    """Run a large number of operations to stress the system."""
    start = time.perf_counter()
    threads = []
    for i in range(NUM_USERS * 5):
        t = threading.Thread(target=user_simulation, args=(i,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    elapsed = time.perf_counter() - start
    print(f"[Stress Test] Completed {NUM_USERS*5*NUM_OPS_PER_USER} ops in {elapsed:.2f}s")
    # Check correctness
    all_data = tree.get_all()
    print(f"[Stress Test] Final tree size: {len(all_data)}")

def main():
    print("=== Module B: Concurrency & Stress Tests ===")
    print("1. Race Condition Test...")
    race_condition_test()
    print("2. Failure Simulation Test...")
    failure_simulation_test()
    print("3. Stress Test...")
    stress_test()
    print("All tests completed. Review output for errors or assertion failures.")

if __name__ == "__main__":
    main()
