from flask import request, jsonify
from auth import signup_user, login_user
from db import get_connection, get_db_manager
import uuid
def register_routes(app):
    
    @app.route('/api/signup', methods=['POST'])
    def signup():
        data = request.json
        try:
            res = signup_user(data)
            return jsonify({"message": "User created", "data": res}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    @app.route('/api/login', methods=['POST'])
    def login():
        data = request.json
        res = login_user(data.get('username'), data.get('password'))
        if res:
            return jsonify(res), 200
        return jsonify({"error": "Invalid credentials"}), 401

    @app.route('/checkout', methods=['POST'])
    def checkout():
        data = request.json
        user_id = int(data.get('user_id'))
        product_id = int(data.get('product_id'))
        quantity = data.get('quantity', 1)
        simulate_failure = request.args.get('simulate_failure') == 'true'

        dbm = get_db_manager()
        txn_id = dbm.begin()
        
        try:
            # 1. Check Product Stock
            product_str = dbm.get_table("Products").search(product_id)
            if not product_str:
                raise ValueError("Product not found")
            import json
            product = json.loads(product_str)
            if product['stock'] < quantity:
                raise ValueError("Insufficient stock")
            
            # 2. Check User Balance
            user_str = dbm.get_table("Users").search(user_id)
            if not user_str:
                raise ValueError("User not found")
            user = json.loads(user_str)
            total_price = product['price'] * quantity
            if user['balance'] < total_price:
                raise ValueError("Insufficient balance")

            # Update Product Stock
            new_stock = product['stock'] - quantity
            dbm.txn_update(txn_id, "Products", product_id, {**product, "stock": new_stock})
            
            # Update User Balance
            new_balance = user['balance'] - total_price
            dbm.txn_update(txn_id, "Users", user_id, {**user, "balance": new_balance})

            # Insert Order
            import random
            order_id = random.randint(300000, 999999)
            order_record = {
                "user_id": user_id,
                "product_id": product_id,
                "quantity": quantity,
                "total_price": total_price
            }
            dbm.txn_insert(txn_id, "Orders", order_id, order_record)

            if simulate_failure:
                raise Exception("Simulated Failure")

            dbm.commit(txn_id)
            return jsonify({"status": "success", "order_id": order_id}), 200

        except Exception as e:
            dbm.rollback(txn_id)
            return jsonify({"status": "failed", "error": str(e)}), 400
