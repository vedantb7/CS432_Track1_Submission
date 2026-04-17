# employee/orders/routes.py
from flask import Blueprint, jsonify, request
from db import get_connection
from ..utils import (
    _safe_float, _isoformat, _frontend_status,
    DB_STATUSES, STATUS_TRANSITIONS, FRONTEND_TO_DB
)

emp_orders_bp = Blueprint('emp_orders', __name__)

def _order_belongs_to_employee(cur, order_id: int, employee_id: int) -> bool:
    """
    Authorization helper.
    Returns True iff the order's member is assigned to employee_id.
    """
    cur.execute(
        """
        SELECT 1
        FROM freshwash.laundry_order lo
        JOIN freshwash.member m ON m.member_id = lo.member_id
        LEFT JOIN freshwash.order_assignment oa ON oa.order_id = lo.order_id
        WHERE lo.order_id = %s AND (m.assigned_employee_id = %s OR oa.employee_id = %s)
        """,
        (order_id, employee_id, employee_id),
    )
    return cur.fetchone() is not None

def _member_assigned_to_employee(cur, member_id: int, employee_id: int) -> bool:
    cur.execute(
        "SELECT 1 FROM freshwash.member WHERE member_id = %s AND assigned_employee_id = %s",
        (member_id, employee_id),
    )
    return cur.fetchone() is not None

@emp_orders_bp.route('/<int:employee_id>', methods=['GET'])
def get_assigned_orders(employee_id):
    """Fetch all orders assigned to this employee via order_assignment."""
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute(
            """
            SELECT DISTINCT
                lo.order_id, lo.member_id, m.name AS member_name,
                lo.order_date, lo.pickup_time, lo.expected_delivery_time,
                lo.total_amount, lo.current_status,
                oa.assigned_role, oa.assigned_date
            FROM freshwash.laundry_order lo
            JOIN freshwash.member m ON m.member_id = lo.member_id
            LEFT JOIN freshwash.order_assignment oa ON oa.order_id = lo.order_id
            WHERE m.assigned_employee_id = %s OR oa.employee_id = %s
            ORDER BY lo.order_date DESC
            """,
            (employee_id, employee_id)
        )
        rows = cur.fetchall()
        orders = []
        for r in rows:
            db_status = r[7]
            orders.append({
                "order_id":               r[0],
                "member_id":              r[1],
                "member_name":            r[2],
                "order_date":             _isoformat(r[3]),
                "pickup_time":            _isoformat(r[4]),
                "expected_delivery_time": _isoformat(r[5]),
                "total_amount":           _safe_float(r[6]),
                "order_status":           _frontend_status(db_status),
                "db_status":              db_status,
                "assigned_role":          r[8],
                "assigned_date":          _isoformat(r[9]),
            })
        return jsonify(orders), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@emp_orders_bp.route('/order/<int:order_id>', methods=['GET'])
def get_order_details(order_id):
    """Get specific order details (employee scoped)."""
    employee_id = request.args.get('employee_id', type=int)
    if not employee_id:
        return jsonify({"error": "employee_id query param is required"}), 400

    conn = get_connection()
    cur = conn.cursor()
    try:
        if not _order_belongs_to_employee(cur, order_id, employee_id):
            return jsonify({"error": "Forbidden"}), 403

        cur.execute(
            """
            SELECT
                lo.order_id, lo.member_id, m.name AS member_name,
                lo.order_date, lo.pickup_time, lo.expected_delivery_time,
                lo.total_amount, lo.current_status
            FROM freshwash.laundry_order lo
            JOIN freshwash.member m ON m.member_id = lo.member_id
            WHERE lo.order_id = %s
            """,
            (order_id,),
        )
        r = cur.fetchone()
        if not r:
            return jsonify({"error": "Order not found"}), 404

        # Fetch items
        cur.execute("""
            SELECT s.service_name, ct.type_name, os.quantity, os.applied_price
            FROM freshwash.order_service os
            JOIN freshwash.service s ON s.service_id = os.service_id
            JOIN freshwash.clothing_type ct ON ct.type_id = os.type_id
            WHERE os.order_id = %s
        """, (order_id,))
        items = []
        for item_row in cur.fetchall():
            items.append({
                "service_name": item_row[0],
                "type_name": item_row[1],
                "quantity": item_row[2],
                "applied_price": float(item_row[3])
            })

        db_status = r[7]
        return jsonify({
            "order_id":               r[0],
            "member_id":              r[1],
            "member_name":            r[2],
            "order_date":             _isoformat(r[3]),
            "pickup_time":            _isoformat(r[4]),
            "expected_delivery_time": _isoformat(r[5]),
            "total_amount":           _safe_float(r[6]),
            "order_status":           _frontend_status(db_status),
            "db_status":              db_status,
            "items":                  items
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@emp_orders_bp.route('', methods=['POST'])
def create_order():
    """Create a new itemized laundry order and immediately assign it to the employee."""
    data = request.get_json(silent=True)
    if not data or 'items' not in data or 'member_id' not in data or 'employee_id' not in data:
        return jsonify({"error": "member_id, employee_id and items array required"}), 400

    assigned_role = data.get('assigned_role', 'Handler')
    conn = get_connection()
    cur  = conn.cursor()
    try:
        # Enforce: employees can only create/manage orders for their assigned members.
        if not _member_assigned_to_employee(cur, int(data['member_id']), int(data['employee_id'])):
            return jsonify({"error": "Forbidden: member not assigned to this employee"}), 403

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

        cur.execute(
            """
            INSERT INTO freshwash.laundry_order
                (member_id, pickup_time, expected_delivery_time, total_amount, current_status)
            VALUES (%s, %s, %s, %s, 'Pending')
            RETURNING order_id, order_date
            """,
            (data['member_id'], data['pickup_time'],
             data['expected_delivery_time'], total_amount)
        )
        order_row = cur.fetchone()
        order_id  = order_row[0]
        order_date = order_row[1]

        # Insert items
        for item in items_to_insert:
            cur.execute("""
                INSERT INTO freshwash.order_service (order_id, service_id, type_id, quantity, applied_price)
                VALUES (%s, %s, %s, %s, %s)
            """, (order_id, item['service_id'], item['type_id'], item['quantity'], item['applied_price']))

        cur.execute(
            """
            INSERT INTO freshwash.order_assignment
                (order_id, employee_id, assigned_role)
            VALUES (%s, %s, %s)
            """,
            (order_id, data['employee_id'], assigned_role)
        )

        cur.execute(
            """
            INSERT INTO freshwash.order_status_log (order_id, status_name)
            VALUES (%s, 'Pending')
            """,
            (order_id,)
        )

        # 4. Create the payment record (default mode: Pending)
        cur.execute(
            "INSERT INTO freshwash.payment (order_id, payment_mode, payment_amount, payment_date) "
            "VALUES (%s, 'Pending', %s, CURRENT_TIMESTAMP) RETURNING payment_id",
            (order_id, total_amount)
        )
        payment_id = cur.fetchone()[0]
        
        # 5. Create the payment status record
        cur.execute(
            "INSERT INTO freshwash.payment_status (payment_id, status_name) VALUES (%s, 'Pending')",
            (payment_id,)
        )

        conn.commit()
        return jsonify({
            "message":    "Order created and assigned successfully",
            "order_id":   order_id,
            "total_amount": total_amount,
            "order_date": _isoformat(order_date),
            "payment_id": payment_id
        }), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@emp_orders_bp.route('/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    """Update order lifecycle status with transition validation."""
    data = request.get_json(silent=True)
    if not data or 'order_status' not in data or 'employee_id' not in data:
        return jsonify({"error": "Request body must contain 'order_status' and 'employee_id'"}), 400

    try:
        employee_id = int(data['employee_id'])
    except Exception:
        return jsonify({"error": "employee_id must be an integer"}), 400

    incoming = data['order_status'].strip()
    if incoming in DB_STATUSES:
        new_db_status = incoming
    elif incoming.lower() in FRONTEND_TO_DB:
        new_db_status = FRONTEND_TO_DB[incoming.lower()]
    else:
        return jsonify({"error": f"Unknown status '{incoming}'"}), 400

    conn = get_connection()
    cur  = conn.cursor()
    try:
        if not _order_belongs_to_employee(cur, order_id, employee_id):
            return jsonify({"error": "Forbidden"}), 403

        cur.execute("SELECT current_status FROM freshwash.laundry_order WHERE order_id = %s", (order_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": f"Order {order_id} not found"}), 404

        current_db_status = row[0]
        if new_db_status == current_db_status:
            return jsonify({"message": "Order already has the requested status"}), 200

        allowed = STATUS_TRANSITIONS.get(current_db_status, [])
        if new_db_status not in allowed:
            return jsonify({"error": f"Cannot transition from '{current_db_status}' to '{new_db_status}'"}), 422

        cur.execute("UPDATE freshwash.laundry_order SET current_status = %s WHERE order_id = %s", (new_db_status, order_id))
        cur.execute("INSERT INTO freshwash.order_status_log (order_id, status_name) VALUES (%s, %s)", (order_id, new_db_status))
        conn.commit()

        return jsonify({
            "message":          "Order status updated",
            "order_id":         order_id,
            "previous_status":  _frontend_status(current_db_status),
            "new_status":       _frontend_status(new_db_status),
            "db_status":        new_db_status
        }), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@emp_orders_bp.route('/<int:order_id>/verify', methods=['PUT'])
def verify_order(order_id):
    """Employee approves or rejects a user-submitted order."""
    data = request.get_json(silent=True)
    if not data or 'employee_id' not in data or 'action' not in data:
        return jsonify({"error": "'employee_id' and 'action' required"}), 400

    action = data['action'].lower()   # 'approve' or 'reject'
    if action not in ('approve', 'reject'):
        return jsonify({"error": "action must be 'approve' or 'reject'"}), 400
    if action == 'reject' and not data.get('remarks', '').strip():
        return jsonify({"error": "remarks required when rejecting"}), 400
    if action == 'approve' and not data.get('expected_delivery_time'):
        return jsonify({"error": "expected_delivery_time required when approving"}), 400

    try:
        employee_id = int(data['employee_id'])
    except Exception:
        return jsonify({"error": "employee_id must be integer"}), 400

    conn = get_connection()
    cur = conn.cursor()
    try:
        if not _order_belongs_to_employee(cur, order_id, employee_id):
            return jsonify({"error": "Forbidden"}), 403

        cur.execute("SELECT current_status FROM freshwash.laundry_order WHERE order_id = %s", (order_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Order not found"}), 404
        if row[0] != 'Awaiting Verification':
            return jsonify({"error": f"Order is not awaiting verification (current: {row[0]})"}), 422

        new_status = 'Pending' if action == 'approve' else 'Rejected'

        if action == 'approve':
            # Update delivery time and optionally final price
            final_price = data.get('final_price')
            if final_price is not None:
                cur.execute(
                    "UPDATE freshwash.laundry_order SET current_status = %s, expected_delivery_time = %s, total_amount = %s WHERE order_id = %s",
                    (new_status, data['expected_delivery_time'], final_price, order_id)
                )
                # Update payment amount if price adjusted
                cur.execute(
                    "UPDATE freshwash.payment SET payment_amount = %s WHERE order_id = %s",
                    (final_price, order_id)
                )
            else:
                cur.execute(
                    "UPDATE freshwash.laundry_order SET current_status = %s, expected_delivery_time = %s WHERE order_id = %s",
                    (new_status, data['expected_delivery_time'], order_id)
                )
        else:
            # Reject
            cur.execute(
                "UPDATE freshwash.laundry_order SET current_status = %s WHERE order_id = %s",
                (new_status, order_id)
            )

        cur.execute(
            "INSERT INTO freshwash.order_status_log (order_id, status_name) VALUES (%s, %s)",
            (order_id, new_status)
        )

        if action == 'reject':
            cur.execute("""
                INSERT INTO freshwash.order_rejection (order_id, employee_id, remarks)
                VALUES (%s, %s, %s)
            """, (order_id, employee_id, data['remarks'].strip()))

        conn.commit()
        return jsonify({
            "message": f"Order {'approved' if action == 'approve' else 'rejected'}",
            "order_id": order_id,
            "new_status": new_status
        }), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@emp_orders_bp.route('/order/<int:order_id>', methods=['PUT'])
def update_order(order_id):
    """Update an order (employee scoped)."""
    data = request.get_json(silent=True)
    if not data or 'employee_id' not in data:
        return jsonify({"error": "Request body must contain 'employee_id'"}), 400
    try:
        employee_id = int(data['employee_id'])
    except Exception:
        return jsonify({"error": "employee_id must be an integer"}), 400

    allowed_fields = ('pickup_time', 'expected_delivery_time', 'total_amount')
    updates = {k: data.get(k) for k in allowed_fields if k in data}
    if not updates:
        return jsonify({"error": f"At least one of {', '.join(allowed_fields)} is required"}), 400

    conn = get_connection()
    cur = conn.cursor()
    try:
        if not _order_belongs_to_employee(cur, order_id, employee_id):
            return jsonify({"error": "Forbidden"}), 403

        set_parts = []
        params = []
        for k, v in updates.items():
            set_parts.append(f"{k} = %s")
            params.append(v)
        params.append(order_id)

        cur.execute(
            f"UPDATE freshwash.laundry_order SET {', '.join(set_parts)} WHERE order_id = %s",
            tuple(params),
        )
        conn.commit()
        return jsonify({"message": "Order updated", "order_id": order_id}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@emp_orders_bp.route('/order/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    """Delete an order (employee scoped)."""
    data = request.get_json(silent=True) or {}
    employee_id = data.get('employee_id')
    try:
        employee_id = int(employee_id)
    except Exception:
        return jsonify({"error": "Request body must contain integer 'employee_id'"}), 400

    conn = get_connection()
    cur = conn.cursor()
    try:
        if not _order_belongs_to_employee(cur, order_id, employee_id):
            return jsonify({"error": "Forbidden"}), 403

        cur.execute("DELETE FROM freshwash.laundry_order WHERE order_id = %s", (order_id,))
        if cur.rowcount == 0:
            return jsonify({"error": "Order not found"}), 404
        conn.commit()
        return jsonify({"message": "Order deleted", "order_id": order_id}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()
