from db import get_connection

def verify_counts():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM freshwash.laundry_order_backup")
        orig = cur.fetchone()[0]

        cur.execute("""
            SELECT
            (SELECT COUNT(*) FROM freshwash.shard_0_laundry_order) +
            (SELECT COUNT(*) FROM freshwash.shard_1_laundry_order) +
            (SELECT COUNT(*) FROM freshwash.shard_2_laundry_order)
        """)
        sharded = cur.fetchone()[0]

        assert orig == sharded, f"Data loss or duplication detected! Orig: {orig}, Sharded: {sharded}"
        print(f"Data counts match! Original: {orig}, Sharded: {sharded}")

        # Check for duplication (No Duplication Guard)
        cur.execute("""
            SELECT order_id, COUNT(*) 
            FROM (
                SELECT order_id FROM freshwash.shard_0_laundry_order
                UNION ALL
                SELECT order_id FROM freshwash.shard_1_laundry_order
                UNION ALL
                SELECT order_id FROM freshwash.shard_2_laundry_order
            ) t
            GROUP BY order_id
            HAVING COUNT(*) > 1;
        """)
        duplicates = cur.fetchall()
        assert len(duplicates) == 0, f"Duplications found: {duplicates}"
        print("No duplication found!")

    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    verify_counts()
