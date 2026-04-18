from flask import Blueprint, jsonify, request
from db import get_connection, IntegrityError, ProgrammingError, OperationalError
from auth import add_employee
from logging_utils import audit_log

employees_bp = Blueprint('admin_employees', __name__)

def handle_db_error(error, context="operation"):
    """Convert database errors to user-friendly messages"""
    error_str = str(error).lower()
    
    if isinstance(error, IntegrityError):
        if 'unique' in error_str or 'duplicate' in error_str:
            return 'This record already exists'
        else:
            return 'This data conflicts with existing records'
    
    if isinstance(error, (ProgrammingError, OperationalError)):
        return 'Database operation failed. Please try again.'
    
    if 'not null' in error_str:
        return 'Missing required information'
    
    print(f"Database error during {context}: {error}")
    return 'An error occurred. Please try again.'

@employees_bp.route('/employees', methods=['GET'])
@audit_log
def get_all_employees():
    """Get all employees"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT employee_id, employee_name, role, contact_number, joining_date "
            "FROM freshwash.employee "
            "ORDER BY joining_date DESC"
        )
        rows = cur.fetchall()
        employees = []
        for r in rows:
            employees.append({
                "employee_id": r[0],
                "name": r[1],
                "role": r[2],
                "contact": r[3],
                "joining_date": r[4].isoformat() if r[4] else None
            })
        return jsonify(employees), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cur.close()
        conn.close()

@employees_bp.route('/employees/<int:employee_id>', methods=['GET'])
@audit_log
def get_employee_details(employee_id):
    """Get specific employee details"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT employee_id, employee_name, role, contact_number, joining_date "
            "FROM freshwash.employee "
            "WHERE employee_id = %s",
            (employee_id,)
        )
        row = cur.fetchone()
        if row:
            return jsonify({
                "employee_id": row[0],
                "name": row[1],
                "role": row[2],
                "contact": row[3],
                "joining_date": row[4].isoformat() if row[4] else None
            }), 200
        return jsonify({"error": "Employee not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cur.close()
        conn.close()

@employees_bp.route('/employees', methods=['POST'])
@audit_log
def create_employee():
    """
    Create new employee with user account
    
    Request body:
    {
        "name": string,
        "role": string,
        "contact_number": string,
        "joining_date": string (YYYY-MM-DD),
        "username": string (optional - for user account creation),
        "password": string (optional - for user account creation)
    }
    """
    data = request.json
    
    # If username and password provided, create with user account
    if data.get('username') and data.get('password'):
        try:
            result = add_employee({
                'name': data['name'],
                'contact_number': data['contact_number'],
                'role': data['role'],
                'joining_date': data['joining_date'],
                'username': data['username'],
                'password': data['password']
            })
            return jsonify({"message": "Employee created with user account", "data": result}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    # Otherwise create employee only
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO freshwash.employee (employee_name, role, contact_number, joining_date) "
            "VALUES (%s, %s, %s, %s) RETURNING employee_id",
            (data['name'], data['role'], data['contact_number'], data['joining_date'])
        )
        employee_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({"message": "Employee created", "employee_id": employee_id}), 201
    except (IntegrityError, ProgrammingError, OperationalError) as e:
        conn.rollback()
        return jsonify({"error": handle_db_error(e, "employee creation")}), 400
    except Exception as e:
        conn.rollback()
        print(f"Unexpected error creating employee: {e}")
        return jsonify({"error": "Failed to create employee"}), 400
    finally:
        cur.close()
        conn.close()

@employees_bp.route('/employees/<int:employee_id>', methods=['PUT'])
@audit_log
def update_employee(employee_id):
    """Update employee details"""
    data = request.json
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE freshwash.employee SET employee_name = %s, role = %s, contact_number = %s "
            "WHERE employee_id = %s",
            (data['name'], data['role'], data['contact_number'], employee_id)
        )
        conn.commit()
        return jsonify({"message": "Employee updated"}), 200
    except (IntegrityError, ProgrammingError, OperationalError) as e:
        conn.rollback()
        return jsonify({"error": handle_db_error(e, "employee update")}), 400
    except Exception as e:
        conn.rollback()
        print(f"Unexpected error updating employee: {e}")
        return jsonify({"error": "Failed to update employee"}), 400
    finally:
        cur.close()
        conn.close()


@employees_bp.route('/employees/<int:employee_id>', methods=['DELETE'])
@audit_log
def delete_employee(employee_id):
    """Delete employee"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "DELETE FROM freshwash.employee WHERE employee_id = %s",
            (employee_id,)
        )
        conn.commit()
        return jsonify({"message": "Employee deleted"}), 200
    except (IntegrityError, ProgrammingError, OperationalError) as e:
        conn.rollback()
        return jsonify({"error": handle_db_error(e, "employee deletion")}), 400
    except Exception as e:
        conn.rollback()
        print(f"Unexpected error deleting employee: {e}")
        return jsonify({"error": "Failed to delete employee"}), 400
    finally:
        cur.close()
        conn.close()
