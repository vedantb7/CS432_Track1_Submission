from db import get_shard_connection
from shard_router import N_SHARDS

SHARDED_TABLES = [
    "laundry_order",
    "order_service",
    "order_status_log",
    "order_assignment",
    "payment",
    "payment_status",
    "feedback",
    "lost_item",
]


def _table_exists(cur, table_name: str) -> bool:
    cur.execute("SHOW TABLES LIKE %s", (table_name,))
    return cur.fetchone() is not None


def migrate():
    # Source is shard-0, which may still hold legacy logical shard tables
    source_conn = get_shard_connection(0)
    source_cur = source_conn.cursor()

    try:
        missing = []
        for shard_id in range(N_SHARDS):
            for base_table in SHARDED_TABLES:
                logical_table = f"shard_{shard_id}_{base_table}"
                if not _table_exists(source_cur, logical_table):
                    missing.append(logical_table)

        if missing:
            raise RuntimeError(
                "Legacy logical shard tables were not found on source shard-0. "
                f"Missing examples: {missing[:5]}"
            )

        for shard_id in range(N_SHARDS):
            target_conn = get_shard_connection(shard_id)
            target_cur = target_conn.cursor()
            try:
                for base_table in SHARDED_TABLES:
                    logical_table = f"shard_{shard_id}_{base_table}"
                    source_cur.execute(f"SELECT * FROM `{logical_table}`")
                    rows = source_cur.fetchall()
                    if not rows:
                        print(f"[shard {shard_id}] {base_table}: 0 rows")
                        continue

                    columns = [d[0] for d in source_cur.description]
                    cols_csv = ", ".join(f"`{c}`" for c in columns)
                    placeholders = ", ".join(["%s"] * len(columns))
                    insert_sql = (
                        f"INSERT IGNORE INTO `{base_table}` ({cols_csv}) "
                        f"VALUES ({placeholders})"
                    )
                    target_cur.executemany(insert_sql, rows)
                    print(
                        f"[shard {shard_id}] {base_table}: copied={len(rows)} "
                        f"inserted={target_cur.rowcount}"
                    )

                target_conn.commit()
            except Exception:
                target_conn.rollback()
                raise
            finally:
                target_cur.close()
                target_conn.close()
    finally:
        source_cur.close()
        source_conn.close()


if __name__ == "__main__":
    migrate()
