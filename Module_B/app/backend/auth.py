from db import get_connection, IntegrityError, ProgrammingError, OperationalError
import uuid
from datetime import datetime, timedelta
import re

def handle_db_error(error, context="operation"):
    """
    Convert database errors to user-friendly messages.
    
    Args:
        error: The exception from the configured DB driver
        context: Context about what operation was attempted
    
    Returns:
        User-friendly error message
    """
    error_str = str(error).lower()
    
    # Unique constraint violations
    if isinstance(error, IntegrityError):
        if 'username' in error_str:
            return 'Username already exists'
        elif 'email' in error_str:
            return 'Email already registered'
        elif 'contact' in error_str or 'phone' in error_str:
            return 'Phone number already registered'
        elif 'unique' in error_str:
            return 'This data is already in use'
        else:
            return 'This data conflicts with existing records'
    
    # Programming errors (SQL syntax, etc.)
    if isinstance(error, ProgrammingError):
        return 'Database operation failed. Please try again.'
    
    # Connection/operational errors
    if isinstance(error, OperationalError):
        return 'Database connection failed. Please try again.'
    
    # Generic database errors
    if 'not null' in error_str:
        return 'Missing required information'
    elif 'foreign key' in error_str:
        return 'Referenced record not found'
    elif 'duplicate' in error_str:
        return 'This record already exists'
    
    # Default: don't expose raw SQL, but log it
    print(f"Database error during {context}: {error}")
    return 'An error occurred. Please try again.'

def validate_email(email):
    """Validate email format"""
    pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    return bool(re.match(pattern, email))

def validate_phone_number(phone):
    """Validate phone number (exactly 10 digits)"""
    digits_only = re.sub(r'\D', '', phone)
    return len(digits_only) == 10

def validate_password(password):
    """Validate password strength"""
    errors = []
    
    if len(password) < 8:
        errors.append('Password must be at least 8 characters')
    if not re.search(r'[A-Z]', password):
        errors.append('Password must contain at least 1 uppercase letter')
    if not re.search(r'[a-z]', password):
        errors.append('Password must contain at least 1 lowercase letter')
    if not re.search(r'\d', password):
        errors.append('Password must contain at least 1 number')
    if not re.search(r'[@$!%*?&]', password):
        errors.append('Password must contain at least 1 special character (@$!%*?&)')
    
    return errors

def validate_age(age):
    """Validate age (between 18 and 100)"""
    try:
        age_int = int(age)
        if age_int < 18:
            return 'Age must be at least 18 years old'
        if age_int > 100:
            return 'Age must be 100 or less'
        return None
    except (ValueError, TypeError):
        return 'Age must be a valid number'

def validate_username(username):
    """Validate username (3-20 chars, alphanumeric and underscore)"""
    pattern = r'^[a-zA-Z0-9_]{3,20}$'
    if not re.match(pattern, username):
        return 'Username must be 3-20 characters, only letters, numbers, and underscores'
    return None

def validate_full_name(name):
    """Validate full name"""
    if len(name) < 2:
        return 'Name must be at least 2 characters'
    if len(name) > 50:
        return 'Name must be less than 50 characters'
    pattern = r"^[a-zA-Z\s'-]+$"
    if not re.match(pattern, name):
        return 'Name can only contain letters, spaces, hyphens, and apostrophes'
    return None

def signup_user(data):
    # data: {username, password, name, age, email, contact, address}
    
    # Validate username
    username_error = validate_username(data.get('username', ''))
    if username_error:
        raise ValueError(username_error)
    
    # Validate password
    password_errors = validate_password(data.get('password', ''))
    if password_errors:
        raise ValueError('Password: ' + ', '.join(password_errors))
    
    # Validate full name
    name_error = validate_full_name(data.get('name', ''))
    if name_error:
        raise ValueError(name_error)
    
    # Validate phone number
    if not validate_phone_number(data.get('contact', '')):
        raise ValueError('Phone number must be exactly 10 digits')
    
    # Validate email
    if not validate_email(data.get('email', '')):
        raise ValueError('Please enter a valid email address')
    
    # Validate age
    age_error = validate_age(data.get('age', ''))
    if age_error:
        raise ValueError(age_error)
    
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Check if username already exists
        cur.execute(
            "SELECT user_id FROM freshwash.users WHERE username = %s",
            (data['username'],)
        )
        if cur.fetchone():
            raise ValueError('Username already exists')
        
        # Check if email already exists
        cur.execute(
            "SELECT member_id FROM freshwash.member WHERE email = %s",
            (data['email'],)
        )
        if cur.fetchone():
            raise ValueError('Email already registered')
        
        # 1. Create User (User role_id = 2)
        try:
            cur.execute(
                "INSERT INTO freshwash.users (username, password_hash, role_id) VALUES (%s, %s, 2) RETURNING user_id",
                (data['username'], data['password']) # Note: Should be hashed in production
            )
            user_id = cur.fetchone()[0]
        except (IntegrityError, ProgrammingError, OperationalError) as e:
            conn.rollback()
            raise ValueError(handle_db_error(e, "user creation"))
        
        # 2. Create Member
        try:
            cur.execute(
                "INSERT INTO freshwash.member (name, age, email, contact_number, address) VALUES (%s, %s, %s, %s, %s) RETURNING member_id",
                (data['name'], data['age'], data['email'], data['contact'], data['address'])
            )
            member_id = cur.fetchone()[0]
        except (IntegrityError, ProgrammingError, OperationalError) as e:
            conn.rollback()
            raise ValueError(handle_db_error(e, "member creation"))

        # 3. Link member to user
        try:
            cur.execute(
                "UPDATE freshwash.users SET member_id = %s WHERE user_id = %s",
                (member_id, user_id)
            )
        except (IntegrityError, ProgrammingError, OperationalError) as e:
            conn.rollback()
            raise ValueError(handle_db_error(e, "linking member to user"))
        
        conn.commit()
        return {"user_id": user_id, "member_id": member_id}
    except ValueError:
        # Re-raise validation errors as-is
        raise
    except Exception as e:
        conn.rollback()
        # Convert any other database errors to user-friendly message
        raise ValueError(handle_db_error(e, "signup"))
    finally:
        cur.close()
        conn.close()

def login_user(username, password, expected_role=None):
    """
    Login user with role-based validation.
    
    Args:
        username: Username
        password: Password
        expected_role: Expected role ('admin', 'user', or 'employee'). 
                      If provided, user must have this role to login.
    
    Returns:
        dict with token, role, member_id/employee_id, username on success
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT u.user_id, u.role_id, r.role_name, u.member_id, u.employee_id "
            "FROM freshwash.users u "
            "JOIN freshwash.roles r ON u.role_id = r.role_id "
            "WHERE u.username = %s AND u.password_hash = %s AND u.is_active = TRUE",
            (username, password)
        )
        user = cur.fetchone()
        
        if not user:
            return None
        
        user_id, role_id, role_name, member_id, employee_id = user
        
        # Normalize role_name for comparison
        role_lower = role_name.lower()
        
        # Check if the user's role matches expected_role
        if expected_role:
            expected_lower = expected_role.lower()
            if role_lower not in [expected_lower, 'admin']:  # Admin can access any role
                return None  # Role mismatch
        
        # Create session
        token = str(uuid.uuid4())
        expires = datetime.now() + timedelta(hours=24)
        
        cur.execute(
            "INSERT INTO freshwash.sessions (user_id, session_token, expires_at) VALUES (%s, %s, %s)",
            (user_id, token, expires)
        )
        conn.commit()
        
        return {
            "token": token,
            "role": role_lower,
            "member_id": member_id,
            "employee_id": employee_id,
            "username": username
        }
    except Exception as e:
        print(f"Login error: {e}")
        return None
    finally:
        cur.close()
        conn.close()


def add_employee(employee_data):
    """
    Add a new employee with user account.
    
    Args:
        employee_data: {name, contact_number, role, joining_date, username, password}
    
    Returns:
        dict with employee_id and user_id
    """
    # Validate password
    password_errors = validate_password(employee_data.get('password', ''))
    if password_errors:
        raise ValueError('Password: ' + ', '.join(password_errors))
    
    # Validate phone number
    if not validate_phone_number(employee_data.get('contact_number', '')):
        raise ValueError('Phone number must be exactly 10 digits')
    
    # Validate username
    username_error = validate_username(employee_data.get('username', ''))
    if username_error:
        raise ValueError(username_error)
    
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Check if username already exists
        cur.execute(
            "SELECT user_id FROM freshwash.users WHERE username = %s",
            (employee_data['username'],)
        )
        if cur.fetchone():
            raise ValueError('Username already exists')
        
        # 1. Create Employee
        try:
            cur.execute(
                "INSERT INTO freshwash.employee (employee_name, role, contact_number, joining_date) "
                "VALUES (%s, %s, %s, %s) RETURNING employee_id",
                (employee_data['name'], employee_data['role'], employee_data['contact_number'], employee_data['joining_date'])
            )
            employee_id = cur.fetchone()[0]
        except (IntegrityError, ProgrammingError, OperationalError) as e:
            conn.rollback()
            raise ValueError(handle_db_error(e, "employee creation"))
        
        # 2. Create User account (Employee role_id = 3)
        try:
            cur.execute(
                "INSERT INTO freshwash.users (username, password_hash, role_id, employee_id) "
                "VALUES (%s, %s, 3, %s) RETURNING user_id",
                (employee_data['username'], employee_data['password'], employee_id)
            )
            user_id = cur.fetchone()[0]
        except (IntegrityError, ProgrammingError, OperationalError) as e:
            conn.rollback()
            raise ValueError(handle_db_error(e, "user account creation"))
        
        conn.commit()
        return {"employee_id": employee_id, "user_id": user_id}
    except ValueError:
        # Re-raise validation errors as-is
        raise
    except Exception as e:
        conn.rollback()
        # Convert any other database errors to user-friendly message
        raise ValueError(handle_db_error(e, "employee addition"))
    finally:
        cur.close()
        conn.close()
