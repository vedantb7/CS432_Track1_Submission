from shard_router import N_SHARDS
from flask import Blueprint, jsonify
from db import get_connection

dashboard_bp = Blueprint('admin_dashboard', __name__)

@dashboard_bp.route('/dashboard', methods=['GET'])
def get_admin_dashboard():
    """Get admin dashboard statistics"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        total_orders = 0
        total_revenue = 0.0
        pending_orders = 0
        pending_payments = 0

        # Non-sharded tables
        cur.execute("SELECT COUNT(*) FROM freshwash.member")
        total_members = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM freshwash.employee")
        total_employees = cur.fetchone()[0]
        
        # Sharded tables
        for shard_id in range(N_SHARDS):
            table_lo = f"freshwash.shard_{shard_id}_laundry_order"
            table_p = f"freshwash.shard_{shard_id}_payment"
            table_ps = f"freshwash.shard_{shard_id}_payment_status"
            
            # Total orders count
            cur.execute(f"SELECT COUNT(*) FROM {table_lo}")
            total_orders += cur.fetchone()[0]
            
            # Total revenue
            cur.execute(f"SELECT COALESCE(SUM(total_amount), 0) FROM {table_lo}")
            total_revenue += float(cur.fetchone()[0])
            
            # Pending orders count
            cur.execute(
                f"SELECT COUNT(*) FROM {table_lo} WHERE current_status IN ('Pending', 'Processing', 'Washing', 'Ready for Delivery')"
            )
            pending_orders += cur.fetchone()[0]
            
            # Pending payments count
            cur.execute(
                f"SELECT COUNT(*) FROM {table_p} p "
                f"LEFT JOIN {table_ps} ps ON p.payment_id = ps.payment_id "
                f"WHERE ps.status_name != 'Success'"
            )
            pending_payments += cur.fetchone()[0]
        
        return jsonify({
            "totalOrders": total_orders,
            "totalRevenue": total_revenue,
            "totalMembers": total_members,
            "totalEmployees": total_employees,
            "pendingOrders": pending_orders,
            "pendingPayments": pending_payments
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cur.close()
        conn.close()
