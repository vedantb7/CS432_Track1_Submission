import os
import pymysql

# Configuration
SHARD_HOST = os.getenv("SHARD_HOST", "10.0.116.184")
SHARD_PORTS = [3307, 3308, 3309]
SHARD_DB = os.getenv("SHARD_DATABASE", "BottleNeck")
SHARD_USER = os.getenv("SHARD_USER", "BottleNeck")
SHARD_PASS = os.getenv("SHARD_PASSWORD", "password@123")

def get_shard_connection(port):
    return pymysql.connect(
        host=SHARD_HOST,
        port=port,
        user=SHARD_USER,
        password=SHARD_PASS,
        database=SHARD_DB,
        autocommit=True
    )

def cleanup():
    print("Connecting to shards for cleanup...")
    shards = [get_shard_connection(p) for p in SHARD_PORTS]
    
    sharded_tables = [
        "laundry_order", "order_service", "order_status_log", 
        "order_assignment", "payment", "payment_status", 
        "feedback", "lost_item", "order_rejection", "member"
    ]
    
    # 1. Clear Sharded Tables on all shards
    for i, conn in enumerate(shards):
        print(f"  Cleaning Shard {i} (Port {SHARD_PORTS[i]})...")
        cur = conn.cursor()
        
        # Disable foreign key checks for clean truncation
        cur.execute("SET FOREIGN_KEY_CHECKS = 0")
        for table in sharded_tables:
            try:
                cur.execute(f"TRUNCATE TABLE {table}")
                print(f"    Truncated {table}")
            except Exception as e:
                print(f"    Skipping {table}: {e}")
        cur.execute("SET FOREIGN_KEY_CHECKS = 1")

    # 2. Clear Users on Shard 0 (Metadata Shard) but keep Admin if possible?
    # Actually, if we want a full reset, just delete non-admins or truncate and re-seed in next step.
    # The user asked to delete "all", so let's truncate.
    print("  Cleaning Shared Metadata on Shard 0...")
    cur0 = shards[0].cursor()
    cur0.execute("SET FOREIGN_KEY_CHECKS = 0")
    cur0.execute("TRUNCATE TABLE users")
    print("    Truncated users")
    cur0.execute("SET FOREIGN_KEY_CHECKS = 1")

    for conn in shards:
        conn.close()
    
    print("\nAll sample data deleted successfully!")

if __name__ == "__main__":
    cleanup()
