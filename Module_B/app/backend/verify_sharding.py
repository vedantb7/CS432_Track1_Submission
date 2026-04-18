from db import get_shard_connection
from shard_router import N_SHARDS


def verify_counts():
    order_ids = {}
    total_rows = 0

    for shard_id in range(N_SHARDS):
        conn = get_shard_connection(shard_id)
        cur = conn.cursor()
        try:
            cur.execute("SELECT @@hostname")
            hostname = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM laundry_order")
            shard_count = cur.fetchone()[0]
            total_rows += shard_count
            print(f"Shard {shard_id} ({hostname}) row_count={shard_count}")

            cur.execute("SELECT order_id, member_id FROM laundry_order")
            for order_id, member_id in cur.fetchall():
                owner_shard = member_id % N_SHARDS
                if owner_shard != shard_id:
                    raise AssertionError(
                        f"Ownership violation: order_id={order_id}, member_id={member_id}, "
                        f"expected_shard={owner_shard}, actual_shard={shard_id}"
                    )
                if order_id in order_ids:
                    raise AssertionError(
                        f"Duplicate order_id across shards: {order_id} "
                        f"(seen in shard {order_ids[order_id]} and {shard_id})"
                    )
                order_ids[order_id] = shard_id
        finally:
            cur.close()
            conn.close()

    print(f"Total sharded rows: {total_rows}")
    print("No duplication found and ownership checks passed!")

if __name__ == "__main__":
    verify_counts()
