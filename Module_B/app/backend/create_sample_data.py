import os
import random
import pymysql
from faker import Faker
from datetime import datetime, timedelta

fake = Faker()

# Configuration
SHARD_HOST = os.getenv("SHARD_HOST", "10.0.116.184")
SHARD_PORTS = [3307, 3308, 3309]
SHARD_DB = os.getenv("SHARD_DATABASE", "BottleNeck")
SHARD_USER = os.getenv("SHARD_USER", "BottleNeck")
SHARD_PASS = os.getenv("SHARD_PASSWORD", "password@123")

def get_shard_connection(port):
    return pymysql.connect(
        host=SHARD_HOST,
        port=port,
        user=SHARD_USER,
        password=SHARD_PASS,
        database=SHARD_DB,
        autocommit=True
    )

def seed_master_data(cur):
    # Seed roles
    cur.execute("INSERT IGNORE INTO roles (role_id, role_name, description) VALUES (1, 'Admin', 'Admin access'), (2, 'User', 'User access'), (3, 'Employee', 'Employee access')")
    
    # Seed clothing types
    types = [('Cotton Shirt', 'Cold wash'), ('Silk Saree', 'Dry clean'), ('Denim Jeans', 'Warm wash'), ('Woolen Sweater', 'Hand wash')]
    for name, instr in types:
        cur.execute("INSERT IGNORE INTO clothing_type (type_name, wash_instruction) VALUES (%s, %s)", (name, instr))
    
    # Seed services
    services = [('Wash & Fold', 'Standard wash', 50.00), ('Dry Cleaning', 'Chemical clean', 150.00), ('Steam Ironing', 'Steam press', 30.00)]
    for name, desc, price in services:
        cur.execute("INSERT IGNORE INTO service (service_name, service_description, base_price) VALUES (%s, %s, %s)", (name, desc, price))
    
    # Seed employees
    for _ in range(10):
        cur.execute("INSERT INTO employee (employee_name, role, contact_number, joining_date) VALUES (%s, %s, %s, %s)",
                    (fake.name(), random.choice(['Washer', 'Driver', 'Manager']), fake.phone_number()[:15], fake.date_between(start_date='-2y', end_date='today')))
    
    # Seed prices
    cur.execute("SELECT service_id FROM service")
    s_ids = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT type_id FROM clothing_type")
    t_ids = [r[0] for r in cur.fetchall()]
    for sid in s_ids:
        for tid in t_ids:
            cur.execute("INSERT IGNORE INTO price (service_id, type_id, price) VALUES (%s, %s, %s)", (sid, tid, random.uniform(20, 200)))
            
    # Seed default users
    cur.execute("INSERT IGNORE INTO users (user_id, username, password_hash, role_id) VALUES (1, 'admin', 'nimba', 1)")
    cur.execute("INSERT IGNORE INTO users (user_id, username, password_hash, role_id) VALUES (4, 'ramesh.kumar', 'emp123', 3)")

def create_sharded_tables(cur):
    # Core sharded tables
    tables = [
        """CREATE TABLE IF NOT EXISTS laundry_order (
            order_id INT PRIMARY KEY,
            member_id INT NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            pickup_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expected_delivery_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_amount DECIMAL(10,2) DEFAULT 0.00,
            current_status VARCHAR(50) DEFAULT 'Pending'
        )""",
        """CREATE TABLE IF NOT EXISTS order_service (
            order_service_id INT AUTO_INCREMENT PRIMARY KEY,
            order_id INT NOT NULL,
            service_id INT NOT NULL,
            type_id INT NOT NULL,
            quantity INT DEFAULT 1,
            applied_price DECIMAL(10,2)
        )""",
        """CREATE TABLE IF NOT EXISTS order_status_log (
            status_id INT AUTO_INCREMENT PRIMARY KEY,
            order_id INT NOT NULL,
            status_name VARCHAR(50),
            status_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS order_assignment (
            assignment_id INT AUTO_INCREMENT PRIMARY KEY,
            order_id INT NOT NULL,
            employee_id INT NOT NULL,
            assigned_role VARCHAR(50),
            assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS payment (
            payment_id INT AUTO_INCREMENT PRIMARY KEY,
            order_id INT NOT NULL,
            payment_mode VARCHAR(50),
            payment_amount DECIMAL(10,2),
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS payment_status (
            payment_status_id INT AUTO_INCREMENT PRIMARY KEY,
            payment_id INT NOT NULL,
            status_name VARCHAR(50),
            status_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS feedback (
            feedback_id INT AUTO_INCREMENT PRIMARY KEY,
            member_id INT NOT NULL,
            order_id INT NOT NULL,
            rating INT CHECK (rating BETWEEN 1 AND 5),
            comments TEXT,
            feedback_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS lost_item (
            lost_id INT AUTO_INCREMENT PRIMARY KEY,
            order_id INT NOT NULL,
            item_description TEXT,
            reported_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            compensation_amount DECIMAL(10,2) DEFAULT 0.00
        )""",
        """CREATE TABLE IF NOT EXISTS order_rejection (
            rejection_id INT AUTO_INCREMENT PRIMARY KEY,
            order_id INT NOT NULL,
            employee_id INT NOT NULL,
            remarks TEXT NOT NULL,
            rejected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
    ]
    for table_sql in tables:
        cur.execute(table_sql)

def main():
    print("Connecting to shards...")
    shards = [get_shard_connection(p) for p in SHARD_PORTS]
    
    print("Creating tables on all shards...")
    for i, conn in enumerate(shards):
        print(f"  Shard {i}...")
        create_sharded_tables(conn.cursor())
    
    print("Seeding master data on Shard 0 (Metadata Shard)...")
    seed_master_data(shards[0].cursor())
    
    # Get current max IDs to prevent IntegrityError
    max_member_id = 0
    max_order_id = 0
    for conn in shards:
        cur = conn.cursor()
        cur.execute("SELECT MAX(member_id) FROM users")
        res = cur.fetchone()[0]
        if res: max_member_id = max(max_member_id, res)
        
        cur.execute("SELECT MAX(order_id) FROM laundry_order")
        res = cur.fetchone()[0]
        if res: max_order_id = max(max_order_id, res)

    print("Generating members...")
    members = []
    member_id_counter = max_member_id + 1
    for _ in range(180): # 60 per shard average
        member_id = member_id_counter
        member_id_counter += 1
        shard_id = member_id % 3
        
        # User account on Shard 0
        shards[0].cursor().execute(
            "INSERT INTO users (username, password_hash, role_id, member_id) VALUES (%s, %s, %s, %s)",
            (fake.unique.user_name(), fake.password(), 2, member_id)
        )
        
        # Member profile on correct shard
        shards[shard_id].cursor().execute(
            "INSERT INTO member (member_id, name, age, email, contact_number, address) VALUES (%s, %s, %s, %s, %s, %s)",
            (member_id, fake.name(), random.randint(18, 80), fake.email(), fake.phone_number()[:15], fake.address())
        )
        members.append(member_id)

    print("Generating sharded records...")
    order_id_counter = max_order_id + 1
    
    # Target: 60 orders per shard.
    shard_counts = [0, 0, 0]
    
    # We iterate until all shards have at least 60 orders.
    while min(shard_counts) < 60:
        member_id = random.choice(members)
        shard_id = member_id % 3
        
        if shard_counts[shard_id] >= 60:
            continue
            
        order_id = order_id_counter
        order_id_counter += 1
        
        cur = shards[shard_id].cursor()
        
        # 1. Order
        cur.execute(
            "INSERT INTO laundry_order (order_id, member_id, pickup_time, expected_delivery_time, total_amount, current_status) VALUES (%s, %s, %s, %s, %s, %s)",
            (order_id, member_id, datetime.now() - timedelta(days=2), datetime.now() + timedelta(days=2), random.uniform(100, 1000), 'Completed')
        )
        
        # 2. Services
        cur.execute(
            "INSERT INTO order_service (order_id, service_id, type_id, quantity, applied_price) VALUES (%s, %s, %s, %s, %s)",
            (order_id, random.randint(1, 3), random.randint(1, 4), random.randint(1, 5), 50.0)
        )
        
        # 3. Status Log
        cur.execute(
            "INSERT INTO order_status_log (order_id, status_name) VALUES (%s, %s)",
            (order_id, 'Completed')
        )
        
        # 4. Assignment
        cur.execute(
            "INSERT INTO order_assignment (order_id, employee_id, assigned_role) VALUES (%s, %s, %s)",
            (order_id, random.randint(1, 10), 'Processing')
        )
        
        # 5. Payment
        cur.execute(
            "INSERT INTO payment (order_id, payment_amount, payment_mode) VALUES (%s, %s, %s)",
            (order_id, random.uniform(100, 1000), 'Cash')
        )
        payment_id = cur.lastrowid
        
        # 6. Payment Status
        cur.execute(
            "INSERT INTO payment_status (payment_id, status_name) VALUES (%s, %s)",
            (payment_id, 'Paid')
        )
        
        # 7. Feedback
        cur.execute(
            "INSERT INTO feedback (member_id, order_id, rating, comments) VALUES (%s, %s, %s, %s)",
            (member_id, order_id, random.randint(4, 5), 'Great service!')
        )
        
        # 8. Lost Item (rare)
        if random.random() < 0.1:
            cur.execute(
                "INSERT INTO lost_item (order_id, item_description) VALUES (%s, %s)",
                (order_id, 'Blue socks missing')
            )
            
        shard_counts[shard_id] += 1
        if sum(shard_counts) % 30 == 0:
            print(f"  Progress: Shards orders counts {shard_counts}")

    print("Finalizing...")
    for conn in shards:
        conn.close()
    
    print("Sample data creation complete!")

if __name__ == "__main__":
    main()
