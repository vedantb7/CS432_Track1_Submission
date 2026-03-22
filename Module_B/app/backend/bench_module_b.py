import time
import random
import psycopg2
import os
import sys
import pandas as pd

# Add the current directory to sys.path to import modules
sys.path.append(os.getcwd())
from bplustree import BPlusTree
from db import get_connection

def setup_pg_table():
    """Create a dedicated table for benchmarking PostgreSQL B-Tree."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DROP TABLE IF EXISTS freshwash.benchmark_test CASCADE")
        cur.execute("""
            CREATE TABLE freshwash.benchmark_test (
                id INT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error setting up PG table: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def run_benchmarks(data_size=5000):
    """Run comprehensive benchmarks for both PG and Module B B+ Tree."""
    print(f"\n--- Starting Benchmarks (Data Size: {data_size}) ---")
    
    test_keys = list(range(1, data_size + 1))
    random.shuffle(test_keys)
    data = [(k, f"Value_{k}") for k in test_keys]
    sample_keys = random.sample(test_keys, min(1000, data_size))
    
    results = []

    # --- PostgreSQL Benchmarks ---
    print("Running PostgreSQL benchmarks...")
    setup_pg_table()
    conn = get_connection()
    cur = conn.cursor()
    
    # 1. Insert
    start = time.perf_counter()
    cur.executemany("INSERT INTO freshwash.benchmark_test (id, value) VALUES (%s, %s)", data)
    conn.commit()
    results.append({"Engine": "PostgreSQL", "Operation": "INSERT", "Time (ms)": (time.perf_counter() - start) * 1000})
    
    # 2. Select (Point)
    start = time.perf_counter()
    for k in sample_keys:
        cur.execute("SELECT value FROM freshwash.benchmark_test WHERE id = %s", (k,))
        cur.fetchone()
    # Normalize to total data size for fair comparison with bulk operations
    results.append({"Engine": "PostgreSQL", "Operation": "SELECT_POINT", "Time (ms)": ((time.perf_counter() - start) * 1000) / len(sample_keys) * data_size})
    
    # 2b. Select (Miss)
    miss_keys = list(range(data_size + 1, data_size + 1001))
    start = time.perf_counter()
    for k in miss_keys:
        cur.execute("SELECT value FROM freshwash.benchmark_test WHERE id = %s", (k,))
        cur.fetchone()
    results.append({"Engine": "PostgreSQL", "Operation": "SELECT_MISS", "Time (ms)": ((time.perf_counter() - start) * 1000) / len(miss_keys) * data_size})
    
    # 3. Range Query
    num_ranges = 50
    ranges = [(s, s + 100) for s in [random.randint(1, data_size - 100) for _ in range(num_ranges)]]
    start = time.perf_counter()
    for s, e in ranges:
        cur.execute("SELECT * FROM freshwash.benchmark_test WHERE id BETWEEN %s AND %s", (s, e))
        cur.fetchall()
    results.append({"Engine": "PostgreSQL", "Operation": "SELECT_RANGE", "Time (ms)": ((time.perf_counter() - start) * 1000) / num_ranges})
    
    # 4. Update
    update_data = [(f"NewValue_{k}", k) for k in sample_keys]
    start = time.perf_counter()
    cur.executemany("UPDATE freshwash.benchmark_test SET value = %s WHERE id = %s", update_data)
    conn.commit()
    results.append({"Engine": "PostgreSQL", "Operation": "UPDATE", "Time (ms)": ((time.perf_counter() - start) * 1000) / len(sample_keys) * data_size})
    
    # 5. Delete
    start = time.perf_counter()
    cur.execute("DELETE FROM freshwash.benchmark_test")
    conn.commit()
    results.append({"Engine": "PostgreSQL", "Operation": "DELETE_ALL", "Time (ms)": (time.perf_counter() - start) * 1000})
    
    cur.close()
    conn.close()

    # --- Module B B+ Tree Benchmarks ---
    print("Running Module B B+ Tree benchmarks...")
    tree = BPlusTree(order=64)
    
    # 1. Insert
    start = time.perf_counter()
    for k, v in data:
        tree.insert(k, v)
    results.append({"Engine": "Module B B+ Tree", "Operation": "INSERT", "Time (ms)": (time.perf_counter() - start) * 1000})
    
    # 2. Select (Point)
    start = time.perf_counter()
    for k in sample_keys:
        tree.search(k)
    results.append({"Engine": "Module B B+ Tree", "Operation": "SELECT_POINT", "Time (ms)": ((time.perf_counter() - start) * 1000) / len(sample_keys) * data_size})
    
    # 2b. Select (Miss)
    start = time.perf_counter()
    for k in miss_keys:
        tree.search(k)
    results.append({"Engine": "Module B B+ Tree", "Operation": "SELECT_MISS", "Time (ms)": ((time.perf_counter() - start) * 1000) / len(miss_keys) * data_size})
    
    # 3. Range Query
    start = time.perf_counter()
    for s, e in ranges:
        tree.range_query(s, e)
    results.append({"Engine": "Module B B+ Tree", "Operation": "SELECT_RANGE", "Time (ms)": ((time.perf_counter() - start) * 1000) / num_ranges})
    
    # 4. Update
    start = time.perf_counter()
    for k in sample_keys:
        tree.update(k, f"NewValue_{k}")
    results.append({"Engine": "Module B B+ Tree", "Operation": "UPDATE", "Time (ms)": ((time.perf_counter() - start) * 1000) / len(sample_keys) * data_size})
    
    # 5. Delete
    start = time.perf_counter()
    for k in test_keys:
        tree.delete(k)
    results.append({"Engine": "Module B B+ Tree", "Operation": "DELETE_ALL", "Time (ms)": (time.perf_counter() - start) * 1000})
    
    # --- Summary & CSV ---
    df = pd.DataFrame(results)
    df['Data Size'] = data_size
    
    # Pivot for quick comparison
    summary = df.pivot(index='Operation', columns='Engine', values='Time (ms)')
    summary['Speedup (x)'] = summary['PostgreSQL'] / summary['Module B B+ Tree']
    
    print("\nBenchmark Summary (Times in ms):")
    print(summary.to_string())
    
    # Save to CSV
    csv_file = 'benchmark_results.csv'
    if os.path.exists(csv_file):
        df.to_csv(csv_file, mode='a', header=False, index=False)
    else:
        df.to_csv(csv_file, index=False)
    print(f"\nResults appended to {csv_file}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Run Module B Benchmarks')
    parser.add_argument('--size', type=int, default=5000, help='Number of records to benchmark')
    args = parser.parse_args()
    
    run_benchmarks(args.size)
