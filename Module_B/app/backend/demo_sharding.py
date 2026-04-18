import sys
import os

# Add Module_A to path so bplustree works if imported by db
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../Module_A/database")))

from db import get_shard_connection
from shard_router import get_shard_id, N_SHARDS

def demo_point_query(member_id):
    """Demonstrates Point 2: Query routed to the correct shard"""
    print("\n" + "="*60)
    print(f" POINT QUERY DEMO: Locating Member ID {member_id}")
    print("="*60)
    
    # 1. Determine the Shard
    # Partitioning Logic: Hash = member_id % N_SHARDS
    shard_id = get_shard_id(member_id)
    print(f"[Logic] Hash Calculation: {member_id} % {N_SHARDS} = Shard {shard_id}")
    print(f"[Action] Connecting EXCLUSIVELY to Shard {shard_id} (Port {3307 + shard_id})...")
    
    # 2. Execute Query
    conn = get_shard_connection(shard_id)
    cur = conn.cursor()
    cur.execute("SELECT order_id, total_amount, status FROM laundry_order WHERE member_id = %s LIMIT 3", (member_id,))
    orders = cur.fetchall()
    
    # 3. Output Results
    if orders:
        print(f"[Result] Found {len(orders)} orders for Member {member_id} on Shard {shard_id}:")
        for o in orders:
            print(f"         ➜ Order ID: {o[0]}, Amount: ${o[1]}, Status: {o[2]}")
    else:
        print(f"[Result] No orders found for Member {member_id} on Shard {shard_id}.")
    
    conn.close()

def demo_scatter_gather():
    """Demonstrates Point 3: Range query spanning multiple shards"""
    print("\n" + "="*60)
    print(" RANGE QUERY DEMO (SCATTER-GATHER): Calculating Total Revenue")
    print("="*60)
    
    print("[Action] Scattering query across ALL shards concurrently...")
    
    total_system_revenue = 0
    
    for shard_id in range(N_SHARDS):
        # 1. Scatter
        print(f"  [Scatter] Querying Shard {shard_id} (Port {3307 + shard_id})...")
        conn = get_shard_connection(shard_id)
        cur = conn.cursor()
        cur.execute("SELECT SUM(total_amount) FROM laundry_order")
        shard_sum = cur.fetchone()[0] or 0
        
        print(f"  [Gather]  Shard {shard_id} reported revenue: ${shard_sum:.2f}")
        total_system_revenue += float(shard_sum)
        conn.close()
        
    # 2. Gather / Aggregate
    print("-" * 60)
    print(f"[Result] Total System Revenue (Aggregated): ${total_system_revenue:.2f}")
    print("="*60 + "\n")

if __name__ == "__main__":
    # Test Member ID 5 (5 % 3 = Shard 2)
    demo_point_query(5)
    
    # Test Member ID 13 (13 % 3 = Shard 1)
    demo_point_query(13)
    
    # Run the scatter gather range sum
    demo_scatter_gather()
