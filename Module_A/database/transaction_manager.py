import threading
import json

class TransactionManager:
    def __init__(self, db_manager, log_manager):
        self.db_manager = db_manager
        self.log_manager = log_manager
        self.next_txn_id = 1
        self.active_txns = {} # txn_id -> list of undo actions
        self.lock = threading.Lock() # Global lock for serialized transactions as per Block E
        self.txn_locks = {} # Optional: more granular locks if needed
        self.committed_txns = set()

    def _generate_txn_id(self):
        txn_id = f"T{self.next_txn_id}"
        self.next_txn_id += 1
        return txn_id

    def begin(self):
        self.lock.acquire()
        txn_id = self._generate_txn_id()
        self.active_txns[txn_id] = []
        self.log_manager.append({"type": "BEGIN", "txn": txn_id})
        return txn_id

    def add_undo_action(self, txn_id, action):
        if txn_id in self.active_txns:
            self.active_txns[txn_id].append(action)

    def commit(self, txn_id):
        if txn_id not in self.active_txns:
            return False
        
        self.log_manager.append({"type": "COMMIT", "txn": txn_id})
        del self.active_txns[txn_id]
        self.committed_txns.add(txn_id)
        self.lock.release()
        return True

    def rollback(self, txn_id):
        if txn_id not in self.active_txns:
            return False
        
        # Replay undo actions in reverse order
        for action in reversed(self.active_txns[txn_id]):
            table_name = action['table']
            op_type = action['type']
            key = action['key']
            before = action.get('before')

            table = self.db_manager.get_table(table_name)
            if table:
                if op_type == 'INSERT':
                    # Undo an insert by deleting
                    table.delete(key)
                elif op_type == 'UPDATE':
                    # Undo an update by restoring before state
                    table.update(key, before)
                elif op_type == 'DELETE':
                    # Undo a delete by re-inserting
                    table.insert(key, before)

        self.log_manager.append({"type": "ROLLBACK", "txn": txn_id})
        del self.active_txns[txn_id]
        self.lock.release()
        return True
