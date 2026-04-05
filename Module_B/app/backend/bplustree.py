import ctypes
import os
import platform
import json

# =============================================================================
# Library Loading & Environment Setup
# =============================================================================

# Pre-load system libstdc++ to avoid version mismatches in environments like Conda
if platform.system() == "Linux":
    paths = [
        "/usr/lib/libstdc++.so.6",
        "/usr/lib/x86_64-linux-gnu/libstdc++.so.6"
    ]
    for path in paths:
        if os.path.exists(path):
            try:
                ctypes.CDLL(path, mode=ctypes.RTLD_GLOBAL)
                break
            except Exception:
                pass

# Load the compiled C++ shared library
# Search in multiple locations: current dir, Module_A/database, parent directories
lib_path = None
search_paths = [
    "./libdbms.so",  # Current directory
    "../../../../../../Module_A/database/libdbms.so",  # From Module_B/app/backend
    "../../../database/libdbms.so",  # From Module_B/app backend variant
]

# Add absolute path if it exists
import sys
if 'CS432_Track1_Submission' in os.getcwd():
    # Running from within the workspace
    module_a_path = os.path.join(os.getcwd().split('CS432_Track1_Submission')[0], 
                                 'CS432_Track1_Submission/Module_A/database/libdbms.so')
    search_paths.append(module_a_path)

for path in search_paths:
    abs_path = os.path.abspath(path)
    if os.path.exists(abs_path):
        lib_path = abs_path
        break

if lib_path is None:
    raise FileNotFoundError(
        f"libdbms.so not found in any of the search paths:\n" +
        "\n".join(f"  - {os.path.abspath(p)}" for p in search_paths) +
        "\n\nPlease compile the C++ library using: g++ -shared -fPIC -O2 -o libdbms.so ../../../Module_A/database/*.cpp"
    )

lib = ctypes.CDLL(lib_path)


# =============================================================================
# C-Types Function Definitions
# =============================================================================

# Basic Tree Operations
lib.BPlusTree_new.argtypes = [ctypes.c_int]
lib.BPlusTree_new.restype = ctypes.c_void_p

lib.BPlusTree_delete.argtypes = [ctypes.c_void_p]

lib.BPlusTree_insert.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]

lib.BPlusTree_search.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
lib.BPlusTree_search.restype = ctypes.c_bool

lib.BPlusTree_remove.argtypes = [ctypes.c_void_p, ctypes.c_int]
lib.BPlusTree_remove.restype = ctypes.c_bool

lib.BPlusTree_update.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
lib.BPlusTree_update.restype = ctypes.c_bool

# Range & Collection Queries
lib.BPlusTree_range_query.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
lib.BPlusTree_range_query.restype = ctypes.c_void_p

lib.BPlusTree_get_all.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
lib.BPlusTree_get_all.restype = ctypes.c_void_p

# Vector Utilities
lib.Vector_get_key.argtypes = [ctypes.c_void_p, ctypes.c_int]
lib.Vector_get_key.restype = ctypes.c_int

lib.Vector_get_value.argtypes = [ctypes.c_void_p, ctypes.c_int]
lib.Vector_get_value.restype = ctypes.c_char_p

lib.Vector_delete.argtypes = [ctypes.c_void_p]

# Metadata & Visualisation
lib.BPlusTree_get_json.argtypes = [ctypes.c_void_p]
lib.BPlusTree_get_json.restype = ctypes.c_char_p

lib.BPlusTree_get_memory_usage.argtypes = [ctypes.c_void_p]
lib.BPlusTree_get_memory_usage.restype = ctypes.c_size_t

# Internal Logic Accessors
lib.BPlusTree_get_root.argtypes = [ctypes.c_void_p]
lib.BPlusTree_get_root.restype = ctypes.c_void_p

lib.BPlusTree__insert_non_full.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
lib.BPlusTree__split_child.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
lib.BPlusTree__delete.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
lib.BPlusTree__fill_child.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
lib.BPlusTree__borrow_from_prev.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
lib.BPlusTree__borrow_from_next.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
lib.BPlusTree__merge.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]


class BPlusTree:
    """
    Python wrapper for the C++ B+ Tree implementation.
    Provides a high-level API for database indexing.
    """

    def __init__(self, order=4):
        self.tree = lib.BPlusTree_new(order)

    def __del__(self):
        if hasattr(self, 'tree') and self.tree:
            lib.BPlusTree_delete(self.tree)

    # --- Public API ---

    def search(self, key):
        out_value = ctypes.create_string_buffer(1024)
        if lib.BPlusTree_search(self.tree, key, out_value, 1024):
            return out_value.value.decode('utf-8')
        return None

    def insert(self, key, value):
        lib.BPlusTree_insert(self.tree, key, str(value).encode('utf-8'))

    def delete(self, key):
        return lib.BPlusTree_remove(self.tree, key)

    def update(self, key, new_value):
        return lib.BPlusTree_update(self.tree, key, str(new_value).encode('utf-8'))

    def range_query(self, start_key, end_key):
        count = ctypes.c_int()
        vec_ptr = lib.BPlusTree_range_query(self.tree, start_key, end_key, ctypes.byref(count))
        
        results = []
        for i in range(count.value):
            key = lib.Vector_get_key(vec_ptr, i)
            val = lib.Vector_get_value(vec_ptr, i).decode('utf-8')
            results.append((key, val))
            
        lib.Vector_delete(vec_ptr)
        return results

    def get_all(self):
        count = ctypes.c_int()
        vec_ptr = lib.BPlusTree_get_all(self.tree, ctypes.byref(count))
        
        results = []
        for i in range(count.value):
            key = lib.Vector_get_key(vec_ptr, i)
            val = lib.Vector_get_value(vec_ptr, i).decode('utf-8')
            results.append((key, val))
            
        lib.Vector_delete(vec_ptr)
        return results

    def get_memory_usage(self):
        """Returns memory usage in bytes."""
        return lib.BPlusTree_get_memory_usage(self.tree)

    # --- Internal Logic Wrappers (Exposed for Appendix requirements) ---

    def _get_root(self):
        return lib.BPlusTree_get_root(self.tree)

    def _insert_non_full(self, node, key, value):
        lib.BPlusTree__insert_non_full(self.tree, node, key, str(value).encode('utf-8'))

    def _split_child(self, parent, index):
        lib.BPlusTree__split_child(self.tree, parent, index)

    def _delete(self, node, key):
        lib.BPlusTree__delete(self.tree, node, key)

    def _fill_child(self, node, index):
        lib.BPlusTree__fill_child(self.tree, node, index)

    def _borrow_from_prev(self, node, index):
        lib.BPlusTree__borrow_from_prev(self.tree, node, index)

    def _borrow_from_next(self, node, index):
        lib.BPlusTree__borrow_from_next(self.tree, node, index)

    def _merge(self, node, index):
        lib.BPlusTree__merge(self.tree, node, index)

    # --- Visualisation ---

    def visualize_tree(self):
        """Generates a Graphviz Digraph object for the tree."""
        try:
            import graphviz
            
            dot = graphviz.Digraph(format='png')
            dot.attr('node', shape='none', margin='0')
            dot.attr(rankdir='TB')
            
            json_str = lib.BPlusTree_get_json(self.tree).decode('utf-8')
            tree_data = json.loads(json_str)
            
            if tree_data:
                self._add_nodes(dot, tree_data)
                self._add_edges(dot, tree_data)
                
            return dot
            
        except ImportError:
            print("Graphviz not found. Returning JSON data instead.")
            return lib.BPlusTree_get_json(self.tree).decode('utf-8')

    def _add_nodes(self, dot, node):
        node_id = "n" + str(node['id'])
        
        if node['is_leaf']:
            # Leaf nodes: HTML table with grey background
            cells = "".join([f"<td>{k}</td>" for k in node['keys']])
            label = f'<<table border="0" cellborder="1" cellspacing="0" bgcolor="lightgrey"><tr>{cells}</tr></table>>'
            dot.node(node_id, label)
        else:
            # Internal nodes: HTML table with ports for children
            row = ""
            for i in range(len(node['keys'])):
                row += f'<td port="c{i}" bgcolor="white" width="10"></td>'
                row += f'<td>{node["keys"][i]}</td>'
            row += f'<td port="c{len(node["keys"])}" bgcolor="white" width="10"></td>'
            
            label = f'<<table border="0" cellborder="1" cellspacing="0"><tr>{row}</tr></table>>'
            dot.node(node_id, label)
        
        if not node['is_leaf']:
            for child in node['children']:
                self._add_nodes(dot, child)

    def _add_edges(self, dot, node):
        node_id = "n" + str(node['id'])
        
        if not node['is_leaf']:
            for i, child in enumerate(node['children']):
                child_id = "n" + str(child['id'])
                dot.edge(f"{node_id}:c{i}", child_id)
                self._add_edges(dot, child)
        elif node.get('next'):
            next_id = "n" + str(node['next'])
            dot.edge(node_id, next_id, style='dashed', constraint='false', color='blue', label='next')
