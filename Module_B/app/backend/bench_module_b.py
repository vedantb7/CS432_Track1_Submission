import os
import sys
import time
import threading
import json
import concurrent.futures
import requests

# Add the current directory to sys.path to import modules
sys.path.append(os.getcwd())
from main import app
from db import get_db_manager

def run_server():
    app.run(port=5001, use_reloader=False)

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()
time.sleep(2) # Wait for server to start

dbm = get_db_manager()

def setup_data():
    txn = dbm.begin()
    dbm.txn_insert(txn, "Products", "p1", {"price": 10, "stock": 50})
    dbm.txn_insert(txn, "Users", "u1", {"balance": 1000})
    dbm.txn_insert(txn, "Products", "p2", {"price": 20, "stock": 1000})
    dbm.txn_insert(txn, "Users", "u2", {"balance": 50000})
    dbm.commit(txn)

def test_checkout(user_id, product_id, quantity, simulate_failure=False):
    url = "http://127.0.0.1:5001/checkout"
    if simulate_failure:
        url += "?simulate_failure=true"
    payload = {
        "user_id": user_id,
        "product_id": product_id,
        "quantity": quantity
    }
    try:
        res = requests.post(url, json=payload)
        return res.status_code, res.json()
    except Exception as e:
        return 500, str(e)

def race_condition_test():
    print("--- Race Condition Test ---")
    setup_data()
    # 100 threads buying p1 (stock=50). Max 50 should succeed.
    successes = 0
    failures = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(test_checkout, "u1", "p1", 1) for _ in range(100)]
        for f in concurrent.futures.as_completed(futures):
            status, json_res = f.result()
            if status == 200:
                successes += 1
            else:
                failures += 1
    
    product_str = dbm.get_table("Products").search("p1")
    product = json.loads(product_str)
    print(f"Successes: {successes}, Failures: {failures}, Final Stock: {product['stock']}")
    assert product['stock'] >= 0, "Stock dropped below zero!"
    assert successes == 50, "Expected exactly 50 successful checkouts"


def failure_simulation_test():
    print("\n--- Failure Simulation Test ---")
    setup_data() # Reset
    # send mix of normal and simulated failure requests
    successes = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = []
        for i in range(50):
            # 50% chance to fail
            sim_fail = (i % 2 == 0)
            futures.append(executor.submit(test_checkout, "u1", "p1", 1, sim_fail))
        for f in concurrent.futures.as_completed(futures):
            status, json_res = f.result()
            if status == 200:
                successes += 1
    
    product_str = dbm.get_table("Products").search("p1")
    product = json.loads(product_str)
    # If 25 failed, only 25 succeeded, stock should be 50 - 25 = 25
    print(f"Checkout Successes: {successes}, Final Stock: {product['stock']}")
    assert product['stock'] == 50 - successes, "Stock does not match successful checkouts! Rollback failed."


def stress_test():
    print("\n--- Stress Test ---")
    # 1000 requests
    # using p2 (1000 stock) and u2 (balance 50000)
    start = time.perf_counter()
    successes = 0
    failures = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(test_checkout, "u2", "p2", 1) for _ in range(1000)]
        for f in concurrent.futures.as_completed(futures):
            status, json_res = f.result()
            if status == 200:
                successes += 1
            else:
                failures += 1
    duration = time.perf_counter() - start
    print(f"Total Time: {duration:.2f} s")
    print(f"Average Response Time: {(duration / 1000) * 1000:.2f} ms")
    print(f"Success Rate: {successes/1000 * 100:.1f}%, Failure Rate: {failures/1000 * 100:.1f}%")

def automated_verification():
    print("\n--- Automated Verification Checks ---")
    product1_str = dbm.get_table("Products").search("p1")
    product1 = json.loads(product1_str)
    
    product2_str = dbm.get_table("Products").search("p2")
    product2 = json.loads(product2_str)
    
    user1_str = dbm.get_table("Users").search("u1")
    user1 = json.loads(user1_str)
    
    print(f"P1 Stock: {product1['stock']}")
    print(f"P2 Stock: {product2['stock']}")
    print(f"U1 Balance: {user1['balance']}")
    
    if product1['stock'] >= 0 and product2['stock'] >= 0 and user1['balance'] >= 0:
        print("Verification Passed: No negative stock or balance in DB. State remains completely valid.")
    else:
        print("Verification Failed: Data corruption found!")
        sys.exit(1)

if __name__ == "__main__":
    race_condition_test()
    failure_simulation_test()
    stress_test()
    automated_verification()
    
    print("\nAll Module B Implementation tests completed successfully.")
    os._exit(0)
