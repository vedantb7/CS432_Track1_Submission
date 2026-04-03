from flask import Blueprint, jsonify, request
from db import get_connection

orders_bp = Blueprint('user_orders', __name__)

@orders_bp.route('/orders/<int:member_id>', methods=['GET'])
def get_user_orders(member_id):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT 
                lo.order_id, lo.order_date, lo.pickup_time, lo.total_amount, lo.current_status,
                e.employee_name AS handler_name
            FROM freshwash.laundry_order lo
            LEFT JOIN freshwash.order_assignment oa ON oa.order_id = lo.order_id AND oa.assigned_role = 'Handler'
            LEFT JOIN freshwash.employee e ON e.employee_id = oa.employee_id
            WHERE lo.member_id = %s
            ORDER BY lo.order_date DESC
            """,
            (member_id,)
        )
        rows = cur.fetchall()
        orders = []
        for r in rows:
            orders.append({
                "order_id": r[0],
                "order_date": r[1].isoformat(),
                "pickup_time": r[2].isoformat(),
                "total_amount": float(r[3]),
                "order_status": r[4].lower(),
                "handler_name": r[5] if r[5] else "Unassigned"
            })
        return jsonify(orders)
    finally:
        cur.close()
        conn.close()
