from flask import Blueprint, jsonify
from db import get_connection
from shard_router import get_table

payments_bp = Blueprint('user_payments', __name__)

@payments_bp.route('/<int:member_id>', methods=['GET'])
def get_user_payments(member_id):
    conn = get_connection()
    cur = conn.cursor()
    try:
        table_p = get_table('payment', member_id)
        table_lo = get_table('laundry_order', member_id)
        table_ps = get_table('payment_status', member_id)
        cur.execute(
            f"SELECT p.payment_id, p.order_id, p.payment_mode, p.payment_amount, p.payment_date, ps.status_name "
            f"FROM {table_p} p "
            f"JOIN {table_lo} lo ON p.order_id = lo.order_id "
            f"LEFT JOIN {table_ps} ps ON p.payment_id = ps.payment_id "
            f"WHERE lo.member_id = %s ORDER BY p.payment_date DESC",
            (member_id,)
        )
        rows = cur.fetchall()
        payments = []
        for r in rows:
            payments.append({
                "payment_id": r[0],
                "order_id": r[1],
                "payment_mode": r[2],
                "payment_amount": float(r[3]),
                "payment_date": r[4].isoformat() if r[4] else None,
                "status": r[5]
            })
        return jsonify(payments)
    finally:
        cur.close()
        conn.close()
