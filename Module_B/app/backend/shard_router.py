N_SHARDS = 3

def get_shard_id(member_id: int) -> int:
    """Returns the shard ID for a given member_id based on hash partitioning."""
    return member_id % N_SHARDS

def get_table(table_name: str, member_id: int) -> str:
    """Returns the correct shard table name for a given member_id."""
    shard_id = get_shard_id(member_id)
    print(f"[SHARD ROUTE] member_id={member_id} -> shard={shard_id}")
    table = f"freshwash.shard_{shard_id}_{table_name}"
    assert "shard_" in table
    return table

def scatter_gather(cur, table_name: str, where_sql: str = "", params=()):
    results = []
    for shard_id in range(N_SHARDS):
        table = f"freshwash.shard_{shard_id}_{table_name}"
        query = f"SELECT * FROM {table} {where_sql}"
        cur.execute(query, params)
        results.extend(cur.fetchall())
    return results

def locate_order_shard(cur, order_id: int):
    """Locates the shard_id and member_id for a given order_id using scatter-gather."""
    for shard_id in range(N_SHARDS):
        table_lo = f"freshwash.shard_{shard_id}_laundry_order"
        cur.execute(f"SELECT member_id FROM {table_lo} WHERE order_id = %s", (order_id,))
        row = cur.fetchone()
        if row:
            return shard_id, row[0]
    raise ValueError(f"Record not found in any shard for order_id={order_id}")

def locate_payment_shard(cur, payment_id: int):
    """Locates the shard_id and member_id for a given payment_id using scatter-gather."""
    for shard_id in range(N_SHARDS):
        table_p = f"freshwash.shard_{shard_id}_payment"
        table_lo = f"freshwash.shard_{shard_id}_laundry_order"
        cur.execute(
            f"SELECT lo.member_id FROM {table_p} p JOIN {table_lo} lo ON p.order_id = lo.order_id WHERE p.payment_id = %s",
            (payment_id,)
        )
        row = cur.fetchone()
        if row:
            return shard_id, row[0]
    raise ValueError(f"Record not found in any shard for payment_id={payment_id}")

def locate_lost_item_shard(cur, lost_id: int):
    """Locates the shard_id and member_id for a given lost_id using scatter-gather."""
    for shard_id in range(N_SHARDS):
        table_li = f"freshwash.shard_{shard_id}_lost_item"
        table_lo = f"freshwash.shard_{shard_id}_laundry_order"
        cur.execute(
            f"SELECT lo.member_id FROM {table_li} li JOIN {table_lo} lo ON li.order_id = lo.order_id WHERE li.lost_id = %s",
            (lost_id,)
        )
        row = cur.fetchone()
        if row:
            return shard_id, row[0]
    raise ValueError(f"Record not found in any shard for lost_id={lost_id}")

def locate_feedback_shard(cur, feedback_id: int):
    """Locates the shard_id and member_id for a given feedback_id using scatter-gather."""
    for shard_id in range(N_SHARDS):
        table_f = f"freshwash.shard_{shard_id}_feedback"
        cur.execute(
            f"SELECT member_id FROM {table_f} WHERE feedback_id = %s",
            (feedback_id,)
        )
        row = cur.fetchone()
        if row:
            return shard_id, row[0]
    raise ValueError(f"Record not found in any shard for feedback_id={feedback_id}")
