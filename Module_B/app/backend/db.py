from shard_router import N_SHARDS
import psycopg2
import sys
import os

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../Module_A/database"))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from db_manager import DBManager
db_manager = DBManager("module_b_wal.log")
db_manager.create_table("Users")
db_manager.create_table("Products")
db_manager.create_table("Orders")

def get_db_manager():
    return db_manager

def get_connection():
    conn = psycopg2.connect(
        host="localhost",
        database="freshwashdb",
        user="postgres",
        password="mypassword"
    )
    return conn

def ensure_schema():
    """
    Best-effort, idempotent schema patching for dev/demo environments.
    Ensures features added in code exist in the DB (without requiring a full reload).
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Ensure member.assigned_employee_id exists
        cur.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'freshwash'
              AND table_name = 'member'
              AND column_name = 'assigned_employee_id'
            """
        )
        has_col = cur.fetchone() is not None
        if not has_col:
            cur.execute("ALTER TABLE freshwash.member ADD COLUMN assigned_employee_id INT")

        # Ensure FK exists (safe even if column just added)
        cur.execute(
            """
            SELECT 1
            FROM information_schema.table_constraints
            WHERE constraint_schema = 'freshwash'
              AND table_name = 'member'
              AND constraint_name = 'fk_member_assigned_employee'
            """
        )
        has_fk = cur.fetchone() is not None
        if not has_fk:
            cur.execute(
                """
                ALTER TABLE freshwash.member
                ADD CONSTRAINT fk_member_assigned_employee
                FOREIGN KEY (assigned_employee_id)
                REFERENCES freshwash.employee (employee_id)
                ON DELETE SET NULL
                """
            )

        # Ensure index exists
        cur.execute(
            """
            SELECT 1
            FROM pg_indexes
            WHERE schemaname = 'freshwash'
              AND tablename = 'member'
              AND indexname = 'idx_member_assigned_employee_id'
            """
        )
        has_idx = cur.fetchone() is not None
        if not has_idx:
            cur.execute("CREATE INDEX idx_member_assigned_employee_id ON freshwash.member (assigned_employee_id)")

        # --- Sharding Implementation ---
        # Check if already sharded by looking for laundry_order_backup
        cur.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'freshwash'
              AND table_name = 'laundry_order_backup'
            """
        )
        is_sharded = cur.fetchone() is not None

        if not is_sharded:
            tables_to_shard = [
                'laundry_order', 'order_service', 'order_status_log', 
                'order_assignment', 'payment', 'payment_status', 
                'feedback', 'lost_item'
            ]
            
            # 1. Create 3 physical shard tables for each table
            for t in tables_to_shard:
                for i in range(N_SHARDS):
                    cur.execute(f"CREATE TABLE freshwash.shard_{i}_{t} (LIKE freshwash.{t} INCLUDING ALL)")
            
            # 2. Migrate existing data
            for i in range(N_SHARDS):
                # laundry_order
                cur.execute(f"INSERT INTO freshwash.shard_{i}_laundry_order SELECT * FROM freshwash.laundry_order WHERE member_id % 3 = {i}")
                
                # order_service
                cur.execute(f"INSERT INTO freshwash.shard_{i}_order_service SELECT os.* FROM freshwash.order_service os JOIN freshwash.laundry_order lo ON os.order_id = lo.order_id WHERE lo.member_id % 3 = {i}")

                # order_status_log
                cur.execute(f"INSERT INTO freshwash.shard_{i}_order_status_log SELECT osl.* FROM freshwash.order_status_log osl JOIN freshwash.laundry_order lo ON osl.order_id = lo.order_id WHERE lo.member_id % 3 = {i}")
                
                # order_assignment
                cur.execute(f"INSERT INTO freshwash.shard_{i}_order_assignment SELECT oa.* FROM freshwash.order_assignment oa JOIN freshwash.laundry_order lo ON oa.order_id = lo.order_id WHERE lo.member_id % 3 = {i}")
                
                # payment
                cur.execute(f"INSERT INTO freshwash.shard_{i}_payment SELECT p.* FROM freshwash.payment p JOIN freshwash.laundry_order lo ON p.order_id = lo.order_id WHERE lo.member_id % 3 = {i}")
                
                # payment_status
                cur.execute(f"INSERT INTO freshwash.shard_{i}_payment_status SELECT ps.* FROM freshwash.payment_status ps JOIN freshwash.payment p ON ps.payment_id = p.payment_id JOIN freshwash.laundry_order lo ON p.order_id = lo.order_id WHERE lo.member_id % 3 = {i}")
                
                # feedback
                cur.execute(f"INSERT INTO freshwash.shard_{i}_feedback SELECT f.* FROM freshwash.feedback f JOIN freshwash.laundry_order lo ON f.order_id = lo.order_id WHERE lo.member_id % 3 = {i}")
                
                # lost_item
                cur.execute(f"INSERT INTO freshwash.shard_{i}_lost_item SELECT li.* FROM freshwash.lost_item li JOIN freshwash.laundry_order lo ON li.order_id = lo.order_id WHERE lo.member_id % 3 = {i}")

            # 3. Rename original tables to *_backup to prevent accidental usage
            # First, drop foreign keys that point to the original tables to avoid issues after renaming
            for t in tables_to_shard:
                cur.execute(f"ALTER TABLE freshwash.{t} RENAME TO {t}_backup")

        conn.commit()
    except Exception:
        # Don't block app start in class projects; the API will surface DB errors if any.
        conn.rollback()
    finally:
        cur.close()
        conn.close()