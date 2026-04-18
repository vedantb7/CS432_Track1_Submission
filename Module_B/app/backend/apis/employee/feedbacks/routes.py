# employee/feedbacks/routes.py
from flask import Blueprint, jsonify
from db import get_connection
from shard_router import N_SHARDS
from ..utils import _isoformat

emp_feedbacks_bp = Blueprint('emp_feedbacks', __name__)

@emp_feedbacks_bp.route('/<int:employee_id>', methods=['GET'])
def get_assigned_feedbacks(employee_id):
    """Return customer feedback entries for orders assigned to this employee."""
    conn = get_connection()
    cur  = conn.cursor()
    try:
        rows = []
        for shard_id in range(N_SHARDS):
            table_f = f"shard_{shard_id}_feedback"
            cur.execute(
                f"""
                SELECT DISTINCT
                    f.feedback_id, f.member_id, f.order_id, f.rating, f.comments, f.feedback_date
                FROM {table_f} f
                JOIN freshwash.member m ON m.member_id = f.member_id
                WHERE m.assigned_employee_id = %s
                """,
                (employee_id,)
            )
            rows.extend(cur.fetchall())

        rows.sort(key=lambda r: r[5] if r[5] is not None else '1970-01-01', reverse=True)
        feedbacks = []
        for r in rows:
            feedbacks.append({
                "feedback_id":   r[0],
                "member_id":     r[1],
                "order_id":      r[2],
                "rating":        r[3],
                "comments":      r[4],
                "feedback_date": _isoformat(r[5])
            })
        return jsonify(feedbacks), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()
