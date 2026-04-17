from flask import Blueprint, jsonify
from db import get_connection

options_bp = Blueprint('options', __name__)

@options_bp.route('/services', methods=['GET'])
def get_service_options():
    """Fetch all available clothing types and services for order creation."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Get all clothing types
        cur.execute("SELECT type_id, type_name FROM freshwash.clothing_type ORDER BY type_name")
        clothing_types = [{"id": r[0], "name": r[1]} for r in cur.fetchall()]

        # Get all services
        cur.execute("SELECT service_id, service_name, base_price FROM freshwash.service ORDER BY service_name")
        services = [{"id": r[0], "name": r[1], "base_price": float(r[2])} for r in cur.fetchall()]

        # Get all pricing rules (mapping)
        cur.execute("""
            SELECT type_id, service_id, price 
            FROM freshwash.price
        """)
        pricing = []
        for r in cur.fetchall():
            pricing.append({
                "type_id": r[0],
                "service_id": r[1],
                "price": float(r[2])
            })

        return jsonify({
            "clothing_types": clothing_types,
            "services": services,
            "pricing": pricing
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()
