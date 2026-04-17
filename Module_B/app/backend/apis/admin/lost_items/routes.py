from flask import Blueprint, jsonify, request
from db import get_connection
from logging_utils import audit_log
from tree_cache import search_lost_item_fast, get_all_lost_items_range, refresh_lost_items_cache
from shard_router import N_SHARDS, get_table, locate_lost_item_shard

lost_items_bp = Blueprint('admin_lost_items', __name__)

@lost_items_bp.route('/lost-items', methods=['GET'])
@audit_log
def get_all_lost_items():
    """Get all reported lost items"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        results = []
        for shard_id in range(N_SHARDS):
            table_li = f"freshwash.shard_{shard_id}_lost_item"
            table_lo = f"freshwash.shard_{shard_id}_laundry_order"
            cur.execute(
                f"SELECT li.lost_id, li.order_id, lo.member_id, m.name, li.item_description, "
                f"li.compensation_amount, li.reported_date "
                f"FROM {table_li} li "
                f"JOIN {table_lo} lo ON li.order_id = lo.order_id "
                f"JOIN freshwash.member m ON lo.member_id = m.member_id "
            )
            results.extend(cur.fetchall())
        
        results.sort(key=lambda r: r[6] if r[6] is not None else '1970-01-01', reverse=True)

        lost_items = []
        for r in results:
            lost_items.append({
                "lost_item_id": r[0],
                "order_id": r[1],
                "member_id": r[2],
                "member_name": r[3],
                "item_description": r[4],
                "compensation_amount": float(r[5]),
                "reported_date": r[6].isoformat() if r[6] else None
            })
        return jsonify(lost_items), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cur.close()
        conn.close()

# --- Module A B+ Tree Integration Routes ---

@lost_items_bp.route('/lost-items/fast-search/<int:lost_item_id>', methods=['GET'])
@audit_log
def fast_search_lost_item(lost_item_id):
    """Demonstrates high-speed B+ Tree search for a lost item."""
    description = search_lost_item_fast(lost_item_id)
    if description:
        return jsonify({
            "lost_item_id": lost_item_id,
            "item_description": description,
            "engine": "Module A B+ Tree Indexer"
        }), 200
    return jsonify({"error": "Lost item not found in B+ Tree index"}), 404

@lost_items_bp.route('/lost-items/range-search', methods=['GET'])
@audit_log
def range_search_lost_items():
    """Demonstrates range query capability of the Module A B+ Tree."""
    start_id = request.args.get('start', type=int)
    end_id = request.args.get('end', type=int)
    
    if start_id is None or end_id is None:
        return jsonify({"error": "Please provide 'start' and 'end' parameters"}), 400
        
    results = get_all_lost_items_range(start_id, end_id)
    formatted_results = [{"lost_id": r[0], "description": r[1]} for r in results]
    
    return jsonify({
        "count": len(formatted_results),
        "results": formatted_results,
        "engine": "Module A B+ Tree Indexer"
    }), 200

@lost_items_bp.route('/lost-items/cache/refresh', methods=['POST'])
@audit_log
def refresh_cache_endpoint():
    """Endpoint to trigger a cache refresh manually."""
    refresh_lost_items_cache()
    return jsonify({"message": "B+ Tree index successfully refreshed from database"}), 200

# --- Standard Details Route ---

@lost_items_bp.route('/lost-items/<int:lost_item_id>', methods=['GET'])
@audit_log
def get_lost_item_details(lost_item_id):
    """Get specific lost item details"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        shard_id, member_id = locate_lost_item_shard(cur, lost_item_id)
        if member_id is None:
            return jsonify({"error": "Lost item not found"}), 404
            
        table_li = get_table('lost_item', member_id)
        table_lo = get_table('laundry_order', member_id)

        cur.execute(
            f"SELECT li.lost_id, li.order_id, lo.member_id, m.name, m.email, m.contact_number, "
            f"li.item_description, li.compensation_amount, li.reported_date "
            f"FROM {table_li} li "
            f"JOIN {table_lo} lo ON li.order_id = lo.order_id "
            f"JOIN freshwash.member m ON lo.member_id = m.member_id "
            f"WHERE li.lost_id = %s",
            (lost_item_id,)
        )
        row = cur.fetchone()
        if row:
            return jsonify({
                "lost_item_id": row[0],
                "order_id": row[1],
                "member_id": row[2],
                "member_name": row[3],
                "member_email": row[4],
                "member_contact": row[5],
                "item_description": row[6],
                "compensation_amount": float(row[7]),
                "reported_date": row[8].isoformat() if row[8] else None
            }), 200
        return jsonify({"error": "Lost item not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cur.close()
        conn.close()

@lost_items_bp.route('/lost-items/<int:lost_item_id>/status', methods=['PUT'])
@audit_log
def update_lost_item_status(lost_item_id):
    """Update lost item status"""
    data = request.json
    conn = get_connection()
    cur = conn.cursor()
    try:
        shard_id, member_id = locate_lost_item_shard(cur, lost_item_id)
        if member_id is None:
            return jsonify({"error": "Lost item not found"}), 404

        table_li = get_table('lost_item', member_id)

        cur.execute(
            f"UPDATE {table_li} SET item_description = %s WHERE lost_id = %s",
            (data.get('item_description', ''), lost_item_id)
        )
        conn.commit()
        # After updating DB, refresh our B+ Tree cache
        refresh_lost_items_cache()
        return jsonify({"message": "Lost item updated and cache refreshed"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cur.close()
        conn.close()
