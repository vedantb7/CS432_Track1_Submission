from flask import Blueprint, request, jsonify
from db import get_connection
from shard_router import get_table, locate_order_shard

interactions_bp = Blueprint('user_interactions', __name__)

@interactions_bp.route('/feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    conn = get_connection()
    cur = conn.cursor()
    try:
        member_id = int(data['member_id'])
        table_f = get_table('feedback', member_id)
        cur.execute(
            f"INSERT INTO {table_f} (member_id, order_id, rating, comments) VALUES (%s, %s, %s, %s)",
            (member_id, data['order_id'], data['rating'], data['comments'])
        )
        conn.commit()
        return jsonify({"message": "Feedback submitted"}), 201
    finally:
        cur.close()
        conn.close()

@interactions_bp.route('/lost-items', methods=['POST'])
def report_lost_item():
    data = request.json
    conn = get_connection()
    cur = conn.cursor()
    try:
        order_id = int(data['order_id'])
        _, member_id = locate_order_shard(cur, order_id)
        table_li = get_table('lost_item', member_id)
        cur.execute(
            f"INSERT INTO {table_li} (order_id, item_description, compensation_amount) VALUES (%s, %s, %s)",
            (order_id, data['item_description'], data.get('compensation_amount', 0))
        )
        conn.commit()
        return jsonify({"message": "Item reported"}), 201
    finally:
        cur.close()
        conn.close()
