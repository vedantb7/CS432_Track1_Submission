from flask import Flask, jsonify
from flask_cors import CORS
from routes import register_routes
from db import ensure_schema

try:
    from apis import init_apis
    _HAS_PSQL_APIS = True
except Exception:
    _HAS_PSQL_APIS = False

app = Flask(__name__)
CORS(app)

# Always register core transactional routes (no PostgreSQL required)
register_routes(app)

# Health-check used by test suite to detect server readiness
@app.route('/api/ping', methods=['GET'])
def ping():
    return jsonify({'status': 'ok'}), 200

# Seed endpoint: pre-populates the in-process B+Tree DBManager for tests
@app.route('/api/seed', methods=['POST'])
def seed():
    from db import get_db_manager
    import json
    dbm = get_db_manager()
    dbm.create_table('Products')
    dbm.create_table('Users')
    dbm.create_table('Orders')
    # Locust users/products
    txn = dbm.begin()
    for i in range(50):
        pid = 100000 + i
        if dbm.get_table('Products').search(pid) is None:
            dbm.txn_insert(txn, 'Products', pid,
                           {'name': f'Product_{i}', 'price': float(i % 10 + 1), 'stock': 10000})
    for i in range(100):
        uid = 200000 + i
        if dbm.get_table('Users').search(uid) is None:
            dbm.txn_insert(txn, 'Users', uid,
                           {'name': f'User_{i}', 'balance': 999999.0})
    dbm.commit(txn)
    return jsonify({'status': 'seeded'}), 200

# PostgreSQL-backed APIs (optional; gracefully absent in test environments)
try:
    ensure_schema()
except Exception:
    pass

if _HAS_PSQL_APIS:
    try:
        init_apis(app)
    except Exception:
        pass

@app.route('/api/test/query', methods=['GET'])
def test_query():
    from flask import request
    from db import get_db_manager
    import json
    table = request.args.get('table')
    key = int(request.args.get('key'))
    dbm = get_db_manager()
    val = dbm.get_table(table).search(key)
    return jsonify({"value": json.loads(val) if val else None}), 200

@app.route('/api/test/seed', methods=['POST'])
def test_seed():
    from flask import request
    from db import get_db_manager
    import json
    data = request.json
    dbm = get_db_manager()
    txn = dbm.begin()
    try:
        for t, recs in data.items():
            dbm.create_table(t)
            for k, v in recs.items():
                dbm.txn_insert(txn, t, int(k), v)
        dbm.commit(txn)
        return jsonify({"status": "seeded"}), 200
    except Exception as e:
        dbm.rollback(txn)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5001)
