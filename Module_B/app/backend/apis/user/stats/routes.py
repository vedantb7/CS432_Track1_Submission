from flask import Blueprint, jsonify
from db import get_connection
from shard_router import get_table

stats_bp = Blueprint('user_stats', __name__)

@stats_bp.route('/stats/<int:member_id>', methods=['GET'])
def get_user_stats(member_id):
    conn = get_connection()
    cur = conn.cursor()
    try:
        table_lo = get_table('laundry_order', member_id)
        table_p = get_table('payment', member_id)
        table_ps = get_table('payment_status', member_id)

        cur.execute(f"""
            SELECT 
                COALESCE((SELECT SUM(total_amount) FROM {table_lo} WHERE member_id = %s), 0) AS lifetime_spend,
                COALESCE((
                    SELECT SUM(payment_amount) 
                    FROM {table_p} p 
                    JOIN {table_lo} lo ON p.order_id = lo.order_id 
                    WHERE lo.member_id = %s 
                      AND p.payment_id NOT IN (
                          SELECT payment_id FROM {table_ps} WHERE status_name = 'Success'
                      )
                ), 0) AS pending_payment
        """, (member_id, member_id))
        row = cur.fetchone()
        if row:
            return jsonify({
                "totalSpent": float(row[0]),
                "pendingPayment": float(row[1])
            })
        return jsonify({"error": "Member not found"}), 404
    finally:
        cur.close()
        conn.close()
