import os
import sys
from bplustree import BPlusTree
from db import get_connection

# Shared instance of the B+ Tree for Lost Items
# lost_id (int) -> item_description (str)
lost_items_tree = BPlusTree(order=4)

def refresh_lost_items_cache():
    """Synchronizes the B+ Tree with the database records."""
    print("Syncing B+ Tree cache with database...")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT lost_id, item_description FROM freshwash.lost_item")
        rows = cur.fetchall()
        
        # Clear/Re-insert logic: For simplicity in this assignment, 
        # we re-initialize the tree to reflect the latest DB state.
        global lost_items_tree
        # In a real system, we'd handle deltas, but here we demonstrate the B+ Tree integration.
        for row in rows:
            lost_id, description = row
            lost_items_tree.insert(lost_id, description)
            
        print(f"Successfully cached {len(rows)} lost items in B+ Tree.")
    except Exception as e:
        print(f"Error refreshing B+ Tree cache: {e}")
    finally:
        cur.close()
        conn.close()

def search_lost_item_fast(lost_id):
    """Performs a high-speed O(log N) search using the B+ Tree engine."""
    return lost_items_tree.search(lost_id)

def get_all_lost_items_range(start_id, end_id):
    """Demonstrates range query capability of the B+ Tree integration."""
    return lost_items_tree.range_query(start_id, end_id)

# Initialize the cache on module load — fail gracefully if DB is unavailable
try:
    refresh_lost_items_cache()
except Exception as e:
    print(f"Warning: Could not sync B+ Tree cache on startup (DB unavailable?): {e}")
