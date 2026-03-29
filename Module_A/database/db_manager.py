from table import Table
from log_manager import LogManager
from transaction_manager import TransactionManager
import json

class DBManager:
    """
    Manages multiple Table objects with WAL, Transactions, and Recovery.
    """

    def __init__(self, log_file="wal.log"):
        self.tables = {}
        self.log_manager = LogManager(log_file)
        self.transaction_manager = TransactionManager(self, self.log_manager)
        self.recover()

    def recover(self):
        """Rebuilds database state from WAL on startup."""
        logs = self.log_manager.read_logs()
        committed_txns = set()
        
        # Pass 1: Identify all committed transactions
        for log in logs:
            if log.get('type') == 'COMMIT':
                committed_txns.add(log.get('txn'))
        
        # Pass 2: Apply operations only for committed transactions
        # This ensures Atomicity (all or nothing) and Durability
        for log in logs:
            txn_id = log.get('txn')
            if txn_id not in committed_txns:
                continue
            
            op_type = log.get('type')
            table_name = log.get('table')
            key = log.get('key')
            
            if not table_name:
                continue

            if table_name not in self.tables:
                self.create_table(table_name)
            
            table = self.tables[table_name]
            
            if op_type == 'INSERT':
                val = log.get('after')
                val_str = json.dumps(val) if not isinstance(val, str) else val
                table.insert(key, val_str)
            elif op_type == 'UPDATE':
                val = log.get('after')
                val_str = json.dumps(val) if not isinstance(val, str) else val
                table.update(key, val_str)
            elif op_type == 'DELETE':
                table.delete(key)

    def create_table(self, name, order=4):
        """Initializes a new table if it doesn't already exist."""
        if name in self.tables:
            return False
            
        self.tables[name] = Table(name, order)
        return True

    def get_table(self, name):
        """Retrieves a table object by name."""
        return self.tables.get(name)

    def list_tables(self):
        """Returns a list of all table names in the database."""
        return list(self.tables.keys())

    def delete_table(self, name):
        """Removes a table from the database management system."""
        if name in self.tables:
            del self.tables[name]
            return True
        return False

    # --- Transactional API ---

    def begin(self):
        return self.transaction_manager.begin()

    def commit(self, txn_id):
        return self.transaction_manager.commit(txn_id)

    def rollback(self, txn_id):
        return self.transaction_manager.rollback(txn_id)

    def txn_insert(self, txn_id, table_name, key, value):
        table = self.get_table(table_name)
        if not table:
            self.create_table(table_name)
            table = self.get_table(table_name)
        
        # Ensure value is string for B+ Tree
        val_str = json.dumps(value) if not isinstance(value, str) else value

        # WAL record
        record = {
            "type": "INSERT",
            "txn": txn_id,
            "table": table_name,
            "key": key,
            "after": value
        }
        self.log_manager.append(record)
        
        # In-memory update
        table.insert(key, val_str)
        
        # Track undo action
        self.transaction_manager.add_undo_action(txn_id, {
            "table": table_name,
            "type": "INSERT",
            "key": key
        })
        return True

    def txn_update(self, txn_id, table_name, key, new_value):
        table = self.get_table(table_name)
        if not table:
            return False
            
        # Consistency checks
        if table_name == "Users" and isinstance(new_value, dict) and new_value.get("balance", 0) < 0:
            raise ValueError(f"Consistency Error: User {key} balance cannot be negative.")
        if table_name == "Products" and isinstance(new_value, dict) and new_value.get("stock", 0) < 0:
            raise ValueError(f"Consistency Error: Product {key} stock cannot be negative.")

        before_str = table.search(key)
        before = json.loads(before_str) if before_str else None
        
        val_str = json.dumps(new_value) if not isinstance(new_value, str) else new_value

        # WAL record
        record = {
            "type": "UPDATE",
            "txn": txn_id,
            "table": table_name,
            "key": key,
            "before": before,
            "after": new_value
        }
        self.log_manager.append(record)
        
        # In-memory update
        table.update(key, val_str)
        
        # Track undo action
        self.transaction_manager.add_undo_action(txn_id, {
            "table": table_name,
            "type": "UPDATE",
            "key": key,
            "before": before_str
        })
        return True

    def txn_delete(self, txn_id, table_name, key):
        table = self.get_table(table_name)
        if not table:
            return False
            
        before_str = table.search(key)
        before = json.loads(before_str) if before_str else None
        
        # WAL record
        record = {
            "type": "DELETE",
            "txn": txn_id,
            "table": table_name,
            "key": key,
            "before": before
        }
        self.log_manager.append(record)
        
        # In-memory update
        table.delete(key)
        
        # Track undo action
        self.transaction_manager.add_undo_action(txn_id, {
            "table": table_name,
            "type": "DELETE",
            "key": key,
            "before": before_str
        })
        return True
