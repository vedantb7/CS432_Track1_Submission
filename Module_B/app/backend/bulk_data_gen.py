import random
from datetime import datetime, timedelta
from faker import Faker
import sys
import os

# Ensure the parent directory is in the path to import db
sys.path.append(os.getcwd())
from db import get_connection

fake = Faker('en_IN')

def generate_bulk_data(num_members=1000, num_orders=5000):
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        print(f"Generating {num_members} members...")
        # Get existing employee IDs for assignment
        cur.execute("SELECT employee_id FROM freshwash.employee")
        employee_ids = [r[0] for r in cur.fetchall()]
        
        # 1. Insert Members
        members = []
        for _ in range(num_members):
            name = fake.name()
            age = random.randint(18, 70)
            email = fake.unique.email()
            contact = fake.unique.numerify('##########')
            address = fake.address().replace('\n', ', ')
            assigned_emp = random.choice(employee_ids)
            created_at = datetime.now() - timedelta(days=random.randint(30, 365))
            
            cur.execute(
                "INSERT INTO freshwash.member (name, age, email, contact_number, address, assigned_employee_id, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING member_id",
                (name, age, email, contact, address, assigned_emp, created_at)
            )
            members.append(cur.fetchone()[0])

        print(f"Generating {num_orders} orders...")
        # Get existing service IDs and price info
        cur.execute("SELECT service_id, base_price FROM freshwash.service")
        services = [(r[0], r[1]) for r in cur.fetchall()]
        
        # 2. Insert Orders & Related Data
        for i in range(num_orders):
            member_id = random.choice(members)
            order_date = datetime.now() - timedelta(days=random.randint(0, 30))
            pickup_time = order_date + timedelta(hours=random.randint(1, 5))
            delivery_time = pickup_time + timedelta(days=random.randint(1, 3))
            status = random.choice(['Pending', 'Processing', 'Washing', 'Ready for Delivery', 'Delivered'])
            
            cur.execute(
                "INSERT INTO freshwash.laundry_order (member_id, order_date, pickup_time, expected_delivery_time, current_status) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING order_id",
                (member_id, order_date, pickup_time, delivery_time, status)
            )
            order_id = cur.fetchone()[0]
            
            # 3. Line Items (Order Services)
            total_amount = 0
            num_items = random.randint(1, 4)
            for _ in range(num_items):
                svc_id, base_p = random.choice(services)
                qty = random.randint(1, 5)
                price = float(base_p) * qty
                total_amount += price
                cur.execute(
                    "INSERT INTO freshwash.order_service (order_id, service_id, quantity, applied_price) VALUES (%s, %s, %s, %s)",
                    (order_id, svc_id, qty, price)
                )
            
            # Update order total
            cur.execute("UPDATE freshwash.laundry_order SET total_amount = %s WHERE order_id = %s", (total_amount, order_id))
            
            # 4. Payments
            if status in ['Delivered', 'Ready for Delivery'] or random.random() > 0.3:
                pay_mode = random.choice(['UPI', 'Cash', 'Credit Card', 'Debit Card'])
                cur.execute(
                    "INSERT INTO freshwash.payment (order_id, payment_mode, payment_amount) VALUES (%s, %s, %s) RETURNING payment_id",
                    (order_id, pay_mode, total_amount)
                )
                payment_id = cur.fetchone()[0]
                
                pay_status = 'Success' if status == 'Delivered' else random.choice(['Success', 'Pending'])
                cur.execute(
                    "INSERT INTO freshwash.payment_status (payment_id, status_name) VALUES (%s, %s)",
                    (payment_id, pay_status)
                )

            # 5. Feedback for Delivered Orders
            if status == 'Delivered' and random.random() > 0.5:
                rating = random.randint(3, 5)
                comments = fake.sentence()
                cur.execute(
                    "INSERT INTO freshwash.feedback (member_id, order_id, rating, comments) VALUES (%s, %s, %s, %s)",
                    (member_id, order_id, rating, comments)
                )

            if i % 1000 == 0:
                print(f"Processed {i} orders...")

        conn.commit()
        print("Bulk data generation complete!")
        
    except Exception as e:
        conn.rollback()
        print(f"Error during bulk generation: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    generate_bulk_data()
