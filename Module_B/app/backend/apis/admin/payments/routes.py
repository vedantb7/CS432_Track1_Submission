from flask import Blueprint, jsonify, request
from db import get_connection
from shard_router import N_SHARDS, get_table, locate_payment_shard

payments_bp = Blueprint('admin_payments', __name__)

@payments_bp.route('/payments', methods=['GET'])
def get_all_payments():
    """Get all payments with order and member details"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        results = []
        for shard_id in range(N_SHARDS):
            table_p = f"freshwash.shard_{shard_id}_payment"
            table_lo = f"freshwash.shard_{shard_id}_laundry_order"
            table_ps = f"freshwash.shard_{shard_id}_payment_status"
            
            cur.execute(
                f"SELECT p.payment_id, p.order_id, lo.member_id, m.name, p.payment_mode, "
                f"p.payment_amount, p.payment_date, ps.status_name "
                f"FROM {table_p} p "
                f"JOIN {table_lo} lo ON p.order_id = lo.order_id "
                f"JOIN freshwash.member m ON lo.member_id = m.member_id "
                f"LEFT JOIN {table_ps} ps ON p.payment_id = ps.payment_id "
            )
            results.extend(cur.fetchall())
            
        results.sort(key=lambda r: r[6] if r[6] is not None else '1970-01-01', reverse=True)
        
        payments = []
        for r in results:
            payments.append({
                "payment_id": r[0],
                "order_id": r[1],
                "member_id": r[2],
                "member_name": r[3],
                "payment_mode": r[4],
                "payment_amount": float(r[5]),
                "payment_date": r[6].isoformat() if r[6] else None,
                "status": r[7]
            })
        return jsonify(payments), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cur.close()
        conn.close()

@payments_bp.route('/payments/<int:payment_id>', methods=['GET'])
def get_payment_details(payment_id):
    """Get specific payment details"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        shard_id, member_id = locate_payment_shard(cur, payment_id)
        if member_id is None:
            return jsonify({"error": "Payment not found"}), 404

        table_p = get_table('payment', member_id)
        table_lo = get_table('laundry_order', member_id)
        table_ps = get_table('payment_status', member_id)

        cur.execute(
            f"SELECT p.payment_id, p.order_id, lo.member_id, m.name, m.email, m.contact_number, "
            f"p.payment_mode, p.payment_amount, p.payment_date, ps.status_name "
            f"FROM {table_p} p "
            f"JOIN {table_lo} lo ON p.order_id = lo.order_id "
            f"JOIN freshwash.member m ON lo.member_id = m.member_id "
            f"LEFT JOIN {table_ps} ps ON p.payment_id = ps.payment_id "
            f"WHERE p.payment_id = %s",
            (payment_id,)
        )
        row = cur.fetchone()
        if row:
            return jsonify({
                "payment_id": row[0],
                "order_id": row[1],
                "member_id": row[2],
                "member_name": row[3],
                "member_email": row[4],
                "member_contact": row[5],
                "payment_mode": row[6],
                "payment_amount": float(row[7]),
                "payment_date": row[8].isoformat() if row[8] else None,
                "status": row[9]
            }), 200
        return jsonify({"error": "Payment not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cur.close()
        conn.close()

@payments_bp.route('/payments/<int:payment_id>/status', methods=['PUT'])
def update_payment_status(payment_id):
    """Update payment status"""
    data = request.json
    conn = get_connection()
    cur = conn.cursor()
    try:
        shard_id, member_id = locate_payment_shard(cur, payment_id)
        if member_id is None:
            return jsonify({"error": "Payment not found"}), 404

        table_ps = get_table('payment_status', member_id)
        new_status = data.get('status', 'Pending')
        
        # Upsert payment status
        cur.execute(f"SELECT payment_status_id FROM {table_ps} WHERE payment_id = %s", (payment_id,))
        existing_status = cur.fetchone()
        
        if existing_status:
            cur.execute(
                f"UPDATE {table_ps} SET status_name = %s, status_timestamp = CURRENT_TIMESTAMP WHERE payment_id = %s",
                (new_status, payment_id)
            )
        else:
            cur.execute(
                f"INSERT INTO {table_ps} (payment_id, status_name) VALUES (%s, %s)",
                (payment_id, new_status)
            )
            
        conn.commit()
        return jsonify({"message": "Payment status updated", "status": new_status}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cur.close()
        conn.close()
