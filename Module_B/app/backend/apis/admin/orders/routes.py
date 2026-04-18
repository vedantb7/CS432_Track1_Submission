from flask import Blueprint, jsonify, request
from db import get_connection
from shard_router import N_SHARDS, get_table, locate_order_shard

orders_bp = Blueprint('admin_orders', __name__)

@orders_bp.route('/orders', methods=['GET'])
def get_all_orders():
    """Get all laundry orders with optional cross-shard date range filtering."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        filters = []
        params = []
        if start_date:
            filters.append("lo.order_date >= %s")
            params.append(start_date)
        if end_date:
            filters.append("lo.order_date <= %s")
            params.append(end_date)
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        results = []
        for shard_id in range(N_SHARDS):
            table_lo = f"freshwash.shard_{shard_id}_laundry_order"
            cur.execute(
                f"SELECT lo.order_id, lo.member_id, m.name, lo.order_date, lo.pickup_time, "
                f"lo.total_amount, lo.current_status "
                f"FROM {table_lo} lo "
                f"JOIN freshwash.member m ON lo.member_id = m.member_id "
                f"{where_clause} "
                f"ORDER BY lo.order_date DESC",
                tuple(params),
            )
            results.extend(cur.fetchall())
        
        results.sort(key=lambda r: r[3], reverse=True)

        orders = []
        for r in results:
            orders.append({
                "order_id": r[0],
                "member_id": r[1],
                "member_name": r[2],
                "order_date": r[3].isoformat(),
                "pickup_time": r[4].isoformat(),
                "total_amount": float(r[5]),
                "order_status": r[6]
            })
        return jsonify(orders), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cur.close()
        conn.close()

@orders_bp.route('/orders', methods=['POST'])
def create_order():
    """Create a new laundry order (admin: unrestricted)."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    required = ('member_id', 'pickup_time', 'expected_delivery_time', 'total_amount')
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    conn = get_connection()
    cur = conn.cursor()
    try:
        member_id = data['member_id']
        table_lo = get_table('laundry_order', member_id)
        table_p = get_table('payment', member_id)
        table_ps = get_table('payment_status', member_id)
        table_osl = get_table('order_status_log', member_id)

        cur.execute(
            f"""
            INSERT INTO {table_lo}
                (member_id, pickup_time, expected_delivery_time, total_amount, current_status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING order_id, order_date
            """,
            (
                member_id,
                data['pickup_time'],
                data['expected_delivery_time'],
                data['total_amount'],
                data.get('current_status', 'Pending'),
            ),
        )
        order_id, order_date = cur.fetchone()
        
        # 2. Create the payment record (default mode: Pending)
        cur.execute(
            f"INSERT INTO {table_p} (order_id, payment_mode, payment_amount, payment_date) "
            f"VALUES (%s, 'Pending', %s, CURRENT_TIMESTAMP) RETURNING payment_id",
            (order_id, data['total_amount'])
        )
        payment_id = cur.fetchone()[0]
        
        # 3. Create the payment status record
        cur.execute(
            f"INSERT INTO {table_ps} (payment_id, status_name) VALUES (%s, 'Pending')",
            (payment_id,)
        )

        # 4. Optional: create an initial status log entry
        cur.execute(
            f"INSERT INTO {table_osl} (order_id, status_name) VALUES (%s, %s)",
            (order_id, data.get('current_status', 'Pending')),
        )

        conn.commit()
        return jsonify({"message": "Order created", "order_id": order_id, "order_date": order_date.isoformat(), "payment_id": payment_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cur.close()
        conn.close()

@orders_bp.route('/orders/<int:order_id>', methods=['GET'])
def get_order_details(order_id):
    """Get specific order details"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        shard_id, member_id = locate_order_shard(cur, order_id)
        if member_id is None:
            return jsonify({"error": "Order not found"}), 404

        table_lo = get_table('laundry_order', member_id)
        cur.execute(
            f"SELECT lo.order_id, lo.member_id, m.name, m.email, m.contact_number, "
            f"lo.order_date, lo.pickup_time, lo.total_amount, lo.current_status "
            f"FROM {table_lo} lo "
            f"JOIN freshwash.member m ON lo.member_id = m.member_id "
            f"WHERE lo.order_id = %s",
            (order_id,)
        )
        row = cur.fetchone()
        if row:
            return jsonify({
                "order_id": row[0],
                "member_id": row[1],
                "member_name": row[2],
                "member_email": row[3],
                "member_contact": row[4],
                "order_date": row[5].isoformat(),
                "pickup_time": row[6].isoformat(),
                "total_amount": float(row[7]),
                "order_status": row[8]
            }), 200
        return jsonify({"error": "Order not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cur.close()
        conn.close()

@orders_bp.route('/orders/<int:order_id>', methods=['PUT'])
def update_order_status(order_id):
    """
    Update an order (admin: unrestricted).
    Backwards compatible:
      - If body has {"status": "..."} → updates current_status
      - Otherwise can update pickup_time/expected_delivery_time/total_amount/current_status
    """
    data = request.get_json(silent=True) or {}
    conn = get_connection()
    cur = conn.cursor()
    try:
        shard_id, member_id = locate_order_shard(cur, order_id)
        if member_id is None:
            return jsonify({"error": "Order not found"}), 404

        table_lo = get_table('laundry_order', member_id)
        table_osl = get_table('order_status_log', member_id)

        if 'status' in data and len(data.keys()) == 1:
            # Legacy client: status only
            new_status = data['status']
            cur.execute(
                f"UPDATE {table_lo} SET current_status = %s WHERE order_id = %s",
                (new_status, order_id),
            )
            cur.execute(
                f"INSERT INTO {table_osl} (order_id, status_name) VALUES (%s, %s)",
                (order_id, new_status),
            )
        else:
            allowed = ('pickup_time', 'expected_delivery_time', 'total_amount', 'current_status')
            updates = {k: data.get(k) for k in allowed if k in data}
            if not updates:
                return jsonify({"error": f"At least one of {', '.join(allowed)} is required"}), 400

            set_parts = []
            params = []
            for k, v in updates.items():
                set_parts.append(f"{k} = %s")
                params.append(v)
            params.append(order_id)
            cur.execute(
                f"UPDATE {table_lo} SET {', '.join(set_parts)} WHERE order_id = %s",
                tuple(params),
            )

            if 'current_status' in updates:
                cur.execute(
                    f"INSERT INTO {table_osl} (order_id, status_name) VALUES (%s, %s)",
                    (order_id, updates['current_status']),
                )

        conn.commit()
        return jsonify({"message": "Order updated"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cur.close()
        conn.close()

@orders_bp.route('/orders/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    """Delete an order (admin: unrestricted)."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        shard_id, member_id = locate_order_shard(cur, order_id)
        if member_id is None:
            return jsonify({"error": "Order not found"}), 404

        table_lo = get_table('laundry_order', member_id)
        cur.execute(f"DELETE FROM {table_lo} WHERE order_id = %s", (order_id,))
        if cur.rowcount == 0:
            return jsonify({"error": "Order not found"}), 404
        conn.commit()
        return jsonify({"message": "Order deleted", "order_id": order_id}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cur.close()
        conn.close()
