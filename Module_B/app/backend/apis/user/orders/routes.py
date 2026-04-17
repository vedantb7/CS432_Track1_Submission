# user/orders/routes.py
from flask import Blueprint, jsonify, request
from db import get_connection

orders_bp = Blueprint('user_orders', __name__)

@orders_bp.route('/orders/<int:member_id>', methods=['GET'])
def get_user_orders(member_id):
    """Fetch member's orders including verification status and rejection remarks."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT
                lo.order_id, lo.order_date, lo.pickup_time,
                lo.expected_delivery_time, lo.total_amount, lo.current_status,
                e.employee_name AS handler_name,
                or2.remarks AS rejection_remarks,
                or2.rejected_at
            FROM freshwash.laundry_order lo
            LEFT JOIN freshwash.order_assignment oa
                ON oa.order_id = lo.order_id AND oa.assigned_role = 'Handler'
            LEFT JOIN freshwash.employee e ON e.employee_id = oa.employee_id
            LEFT JOIN LATERAL (
                SELECT remarks, rejected_at FROM freshwash.order_rejection
                WHERE order_id = lo.order_id ORDER BY rejected_at DESC LIMIT 1
            ) or2 ON TRUE
            WHERE lo.member_id = %s
            ORDER BY lo.order_date DESC
        """, (member_id,))
        rows = cur.fetchall()
        orders = []
        for r in rows:
            orders.append({
                "order_id": r[0],
                "order_date": r[1].isoformat() if r[1] else None,
                "pickup_time": r[2].isoformat() if r[2] else None,
                "expected_delivery_time": r[3].isoformat() if r[3] else None,
                "total_amount": float(r[4]) if r[4] is not None else 0.0,
                "order_status": r[5].lower().replace(' ', '_') if r[5] else 'pending',
                "db_status": r[5],
                "handler_name": r[6] or "Unassigned",
                "rejection_remarks": r[7],
                "rejected_at": r[8].isoformat() if r[8] else None
            })
        return jsonify(orders)
    finally:
        cur.close()
        conn.close()

@orders_bp.route('/orders', methods=['POST'])
def create_user_order():
    """User places a new itemized order → status 'Awaiting Verification'."""
    data = request.get_json(silent=True)
    if not data or 'items' not in data or 'member_id' not in data:
        return jsonify({"error": "member_id and items array required"}), 400
    
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Get assigned employee for this member
        cur.execute(
            "SELECT assigned_employee_id FROM freshwash.member WHERE member_id = %s",
            (data['member_id'],)
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Member not found"}), 404
        employee_id = row[0]
        if not employee_id:
            return jsonify({"error": "No employee assigned. Contact admin."}), 400

        # Calculate total price and validate items
        total_amount = 0
        items_to_insert = []
        for item in data['items']:
            cur.execute(
                "SELECT price FROM freshwash.price WHERE type_id = %s AND service_id = %s",
                (item['type_id'], item['service_id'])
            )
            price_row = cur.fetchone()
            if not price_row:
                return jsonify({"error": f"Invalid pricing rule for type {item['type_id']} and service {item['service_id']}"}), 400
            
            unit_price = float(price_row[0])
            qty = int(item['quantity'])
            total_amount += unit_price * qty
            items_to_insert.append({
                "service_id": item['service_id'],
                "type_id": item['type_id'],
                "quantity": qty,
                "applied_price": unit_price
            })

        # Insert order (delivery date set to +48h as placeholder until verification)
        cur.execute("""
            INSERT INTO freshwash.laundry_order
                (member_id, pickup_time, expected_delivery_time, total_amount, current_status)
            VALUES (%s, %s, %s::timestamp + interval '48 hours', %s, 'Awaiting Verification')
            RETURNING order_id, order_date
        """, (data['member_id'], data['pickup_time'], data['pickup_time'], total_amount))
        order_id, order_date = cur.fetchone()

        # Insert items
        for item in items_to_insert:
            cur.execute("""
                INSERT INTO freshwash.order_service (order_id, service_id, type_id, quantity, applied_price)
                VALUES (%s, %s, %s, %s, %s)
            """, (order_id, item['service_id'], item['type_id'], item['quantity'], item['applied_price']))

        # Assignment & Logs
        cur.execute("INSERT INTO freshwash.order_assignment (order_id, employee_id, assigned_role) VALUES (%s, %s, 'Handler')", (order_id, employee_id))
        cur.execute("INSERT INTO freshwash.order_status_log (order_id, status_name) VALUES (%s, 'Awaiting Verification')", (order_id,))

        # Payment record
        cur.execute("""
            INSERT INTO freshwash.payment (order_id, payment_mode, payment_amount, payment_date)
            VALUES (%s, 'Pending', %s, CURRENT_TIMESTAMP) RETURNING payment_id
        """, (order_id, total_amount))
        payment_id = cur.fetchone()[0]
        cur.execute("INSERT INTO freshwash.payment_status (payment_id, status_name) VALUES (%s, 'Pending')", (payment_id,))

        conn.commit()
        return jsonify({
            "message": "Order placed successfully",
            "order_id": order_id,
            "total_amount": total_amount,
            "order_date": order_date.isoformat()
        }), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@orders_bp.route('/orders/<int:order_id>', methods=['PATCH'])
def resubmit_user_order(order_id):
    """User edits a rejected order and resubmits for re-verification."""
    data = request.get_json(silent=True)
    if not data or 'member_id' not in data:
        return jsonify({"error": "member_id required"}), 400

    conn = get_connection()
    cur = conn.cursor()
    try:
        # Ownership + status guard
        cur.execute("""
            SELECT current_status FROM freshwash.laundry_order
            WHERE order_id = %s AND member_id = %s
        """, (order_id, data['member_id']))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Order not found or not yours"}), 404
        if row[0] != 'Rejected':
            return jsonify({"error": "Only rejected orders can be resubmitted"}), 422

        allowed = ('pickup_time', 'expected_delivery_time', 'total_amount')
        updates = {k: data[k] for k in allowed if k in data}

        if updates:
            set_parts = [f"{k} = %s" for k in updates]
            params = list(updates.values())
            params.append(order_id)
            cur.execute(
                f"UPDATE freshwash.laundry_order SET {', '.join(set_parts)} WHERE order_id = %s",
                tuple(params)
            )

        # Reset status
        cur.execute(
            "UPDATE freshwash.laundry_order SET current_status = 'Awaiting Verification' WHERE order_id = %s",
            (order_id,)
        )
        cur.execute(
            "INSERT INTO freshwash.order_status_log (order_id, status_name) VALUES (%s, 'Awaiting Verification')",
            (order_id,)
        )

        conn.commit()
        return jsonify({"message": "Order resubmitted for verification", "order_id": order_id}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()
