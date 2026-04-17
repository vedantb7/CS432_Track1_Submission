# employee/payments/routes.py
from flask import Blueprint, jsonify, request
from db import get_connection
from shard_router import N_SHARDS, get_table, locate_payment_shard
from ..utils import _safe_float, _isoformat

emp_payments_bp = Blueprint('emp_payments', __name__)

@emp_payments_bp.route('/<int:employee_id>', methods=['GET'])
def get_assigned_payments(employee_id):
    """Return all payments for orders assigned to this employee."""
    conn = get_connection()
    cur  = conn.cursor()
    try:
        # Scatter-Gather Pattern
        results = []
        for shard_id in range(N_SHARDS):
            table_p = f"freshwash.shard_{shard_id}_payment"
            table_lo = f"freshwash.shard_{shard_id}_laundry_order"
            table_oa = f"freshwash.shard_{shard_id}_order_assignment"
            table_ps = f"freshwash.shard_{shard_id}_payment_status"

            cur.execute(
                f"""
                SELECT DISTINCT
                    p.payment_id, p.order_id, p.payment_amount,
                    p.payment_mode, p.payment_date, ps.status_name AS payment_status
                FROM {table_p} p
                JOIN {table_lo} lo ON lo.order_id = p.order_id
                JOIN freshwash.member m ON m.member_id = lo.member_id
                LEFT JOIN {table_oa} oa ON oa.order_id = lo.order_id
                LEFT JOIN {table_ps} ps ON ps.payment_id = p.payment_id
                WHERE m.assigned_employee_id = %s OR oa.employee_id = %s
                """,
                (employee_id, employee_id)
            )
            results.extend(cur.fetchall())
            
        # Sort merged results by payment_date DESC NULLS LAST
        results.sort(key=lambda r: r[4] if r[4] is not None else '1970-01-01', reverse=True)
        
        payments = []
        for r in results:
            payments.append({
                "payment_id":     r[0],
                "order_id":       r[1],
                "payment_amount": _safe_float(r[2]),
                "payment_mode":   r[3],
                "payment_date":   _isoformat(r[4]),
                "payment_status": r[5]
            })
        return jsonify(payments), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@emp_payments_bp.route('/<int:payment_id>', methods=['PUT'])
def update_payment_status(payment_id):
    """Toggle the payment status (Success / Pending / Failed)."""
    data = request.get_json(silent=True)
    if data is None or 'payment_status' not in data:
        return jsonify({"error": "Request body must contain 'payment_status'"}), 400

    new_status = data['payment_status'].strip()
    if new_status not in ('Success', 'Pending', 'Failed'):
        return jsonify({"error": "payment_status must be 'Success', 'Pending', or 'Failed'"}), 400

    conn = get_connection()
    cur  = conn.cursor()
    try:
        shard_id, member_id = locate_payment_shard(cur, payment_id)
        if member_id is None:
            return jsonify({"error": f"Payment {payment_id} not found"}), 404

        table_p = get_table('payment', member_id)
        table_ps = get_table('payment_status', member_id)

        cur.execute(f"SELECT payment_status_id FROM {table_ps} WHERE payment_id = %s", (payment_id,))
        existing = cur.fetchone()

        if existing:
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
        return jsonify({"message": "Payment status updated", "payment_id": payment_id, "payment_status": new_status}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()
