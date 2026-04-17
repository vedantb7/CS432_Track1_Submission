from flask import Blueprint, jsonify
from db import get_connection
from shard_router import N_SHARDS, get_table, locate_feedback_shard

feedbacks_bp = Blueprint('admin_feedbacks', __name__)

@feedbacks_bp.route('/feedbacks', methods=['GET'])
def get_all_feedbacks():
    """Get all customer feedbacks"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        results = []
        for shard_id in range(N_SHARDS):
            table_f = f"freshwash.shard_{shard_id}_feedback"
            cur.execute(
                f"SELECT f.feedback_id, f.member_id, m.name, f.order_id, f.rating, f.comments, f.feedback_date "
                f"FROM {table_f} f "
                f"JOIN freshwash.member m ON f.member_id = m.member_id "
            )
            results.extend(cur.fetchall())
            
        results.sort(key=lambda r: r[6] if r[6] is not None else '1970-01-01', reverse=True)
        
        feedbacks = []
        for r in results:
            feedbacks.append({
                "feedback_id": r[0],
                "member_id": r[1],
                "member_name": r[2],
                "order_id": r[3],
                "rating": r[4],
                "comments": r[5],
                "feedback_date": r[6].isoformat() if r[6] else None
            })
        return jsonify(feedbacks), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cur.close()
        conn.close()

@feedbacks_bp.route('/feedbacks/<int:feedback_id>', methods=['GET'])
def get_feedback_details(feedback_id):
    """Get specific feedback details"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        shard_id, member_id = locate_feedback_shard(cur, feedback_id)
        if member_id is None:
            return jsonify({"error": "Feedback not found"}), 404

        table_f = get_table('feedback', member_id)

        cur.execute(
            f"SELECT f.feedback_id, f.member_id, m.name, m.email, f.order_id, f.rating, f.comments, f.feedback_date "
            f"FROM {table_f} f "
            f"JOIN freshwash.member m ON f.member_id = m.member_id "
            f"WHERE f.feedback_id = %s",
            (feedback_id,)
        )
        row = cur.fetchone()
        if row:
            return jsonify({
                "feedback_id": row[0],
                "member_id": row[1],
                "member_name": row[2],
                "member_email": row[3],
                "order_id": row[4],
                "rating": row[5],
                "comments": row[6],
                "feedback_date": row[7].isoformat() if row[7] else None
            }), 200
        return jsonify({"error": "Feedback not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cur.close()
        conn.close()

@feedbacks_bp.route('/feedbacks/member/<int:member_id>', methods=['GET'])
def get_member_feedbacks(member_id):
    """Get all feedbacks from a specific member"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        table_f = get_table('feedback', member_id)

        cur.execute(
            f"SELECT f.feedback_id, f.order_id, f.rating, f.comments, f.feedback_date "
            f"FROM {table_f} f "
            f"WHERE f.member_id = %s "
            f"ORDER BY f.feedback_date DESC",
            (member_id,)
        )
        rows = cur.fetchall()
        feedbacks = []
        for r in rows:
            feedbacks.append({
                "feedback_id": r[0],
                "order_id": r[1],
                "rating": r[2],
                "comments": r[3],
                "feedback_date": r[4].isoformat() if r[4] else None
            })
        return jsonify(feedbacks), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cur.close()
        conn.close()
