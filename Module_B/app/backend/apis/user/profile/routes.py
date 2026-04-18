from flask import Blueprint, jsonify, request
from db import get_connection, IntegrityError, ProgrammingError, OperationalError

profile_bp = Blueprint('user_profile', __name__)

def handle_db_error(error, context="operation"):
    """Convert database errors to user-friendly messages"""
    error_str = str(error).lower()
    
    if isinstance(error, IntegrityError):
        if 'email' in error_str:
            return 'Email already in use'
        elif 'unique' in error_str:
            return 'This data is already being used'
        else:
            return 'This data conflicts with existing records'
    
    if isinstance(error, (ProgrammingError, OperationalError)):
        return 'Database operation failed. Please try again.'
    
    if 'not null' in error_str:
        return 'Missing required information'
    
    print(f"Database error during {context}: {error}")
    return 'An error occurred. Please try again.'

@profile_bp.route('/profile/<int:member_id>', methods=['GET'])
def get_user_profile(member_id):
    """Get user profile details"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT m.member_id, m.name, m.age, m.email, m.contact_number, m.address, u.username "
            "FROM freshwash.member m "
            "LEFT JOIN freshwash.users u ON u.member_id = m.member_id "
            "WHERE m.member_id = %s",
            (member_id,)
        )
        row = cur.fetchone()
        if row:
            return jsonify({
                "member_id": row[0],
                "name": row[1],
                "age": row[2],
                "email": row[3],
                "contact": row[4],
                "address": row[5],
                "username": row[6]
            })
        return jsonify({"error": "Member not found"}), 404
    finally:
        cur.close()
        conn.close()

@profile_bp.route('/profile/<int:member_id>', methods=['PUT'])
def update_user_profile(member_id):
    """Update user profile details"""
    data = request.json
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE freshwash.member SET name = %s, age = %s, email = %s, contact_number = %s, address = %s "
            "WHERE member_id = %s",
            (data.get('name'), data.get('age'), data.get('email'), data.get('contact'), data.get('address'), member_id)
        )
        conn.commit()
        return jsonify({"message": "Profile updated successfully"}), 200
    except (IntegrityError, ProgrammingError, OperationalError) as e:
        conn.rollback()
        return jsonify({"error": handle_db_error(e, "profile update")}), 400
    except Exception as e:
        conn.rollback()
        print(f"Unexpected error updating profile: {e}")
        return jsonify({"error": "Failed to update profile"}), 400
    finally:
        cur.close()
        conn.close()

@profile_bp.route('/profile/<int:member_id>/change-password', methods=['POST'])
def change_user_password(member_id):
    """Change user password"""
    data = request.json
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not old_password or not new_password:
        return jsonify({"error": "Old password and new password are required"}), 400
    
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Get the user associated with this member
        cur.execute(
            "SELECT user_id, password_hash FROM freshwash.users WHERE member_id = %s",
            (member_id,)
        )
        user_row = cur.fetchone()
        
        if not user_row:
            return jsonify({"error": "User not found"}), 404
        
        user_id, password_hash = user_row
        
        # Verify old password
        if password_hash != old_password:
            return jsonify({"error": "Old password is incorrect"}), 401
        
        # Update password
        cur.execute(
            "UPDATE freshwash.users SET password_hash = %s WHERE user_id = %s",
            (new_password, user_id)
        )
        conn.commit()
        return jsonify({"message": "Password changed successfully"}), 200
    except (IntegrityError, ProgrammingError, OperationalError) as e:
        conn.rollback()
        return jsonify({"error": handle_db_error(e, "password change")}), 400
    except Exception as e:
        conn.rollback()
        print(f"Unexpected error changing password: {e}")
        return jsonify({"error": "Failed to change password"}), 400
    finally:
        cur.close()
        conn.close()


@profile_bp.route('/employee/<int:employee_id>', methods=['GET'])
def get_employee_profile(employee_id):
    """Get employee profile details"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT e.employee_id, e.employee_name, e.role, e.contact_number, e.joining_date, u.username "
            "FROM freshwash.employee e "
            "LEFT JOIN freshwash.users u ON u.employee_id = e.employee_id "
            "WHERE e.employee_id = %s",
            (employee_id,)
        )
        row = cur.fetchone()
        if row:
            return jsonify({
                "employee_id": row[0],
                "name": row[1],
                "role": row[2],
                "contact": row[3],
                "joining_date": row[4].isoformat() if row[4] else None,
                "username": row[5]
            })
        return jsonify({"error": "Employee not found"}), 404
    finally:
        cur.close()
        conn.close()

@profile_bp.route('/employee/<int:employee_id>', methods=['PUT'])
def update_employee_profile(employee_id):
    """Update employee profile details"""
    data = request.json
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE freshwash.employee SET employee_name = %s, role = %s, contact_number = %s, joining_date = %s "
            "WHERE employee_id = %s",
            (data.get('name'), data.get('role'), data.get('contact'), data.get('joining_date'), employee_id)
        )
        conn.commit()
        return jsonify({"message": "Profile updated successfully"}), 200
    except (IntegrityError, ProgrammingError, OperationalError) as e:
        conn.rollback()
        return jsonify({"error": handle_db_error(e, "employee profile update")}), 400
    except Exception as e:
        conn.rollback()
        print(f"Unexpected error updating employee profile: {e}")
        return jsonify({"error": "Failed to update profile"}), 400
    finally:
        cur.close()
        conn.close()

@profile_bp.route('/employee/<int:employee_id>/change-password', methods=['POST'])
def change_employee_password(employee_id):
    """Change employee password"""
    data = request.json
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not old_password or not new_password:
        return jsonify({"error": "Old password and new password are required"}), 400
    
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Get the user associated with this employee
        cur.execute(
            "SELECT user_id, password_hash FROM freshwash.users WHERE employee_id = %s",
            (employee_id,)
        )
        user_row = cur.fetchone()
        
        if not user_row:
            return jsonify({"error": "User not found"}), 404
        
        user_id, password_hash = user_row
        
        # Verify old password
        if password_hash != old_password:
            return jsonify({"error": "Old password is incorrect"}), 401
        
        # Update password
        cur.execute(
            "UPDATE freshwash.users SET password_hash = %s WHERE user_id = %s",
            (new_password, user_id)
        )
        conn.commit()
        return jsonify({"message": "Password changed successfully"}), 200
    except (IntegrityError, ProgrammingError, OperationalError) as e:
        conn.rollback()
        return jsonify({"error": handle_db_error(e, "employee password change")}), 400
    except Exception as e:
        conn.rollback()
        print(f"Unexpected error changing employee password: {e}")
        return jsonify({"error": "Failed to change password"}), 400
    finally:
        cur.close()
        conn.close()
