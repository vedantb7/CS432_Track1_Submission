#include "BPlusTree.h"
#include <algorithm>
#include <iostream>
#include <cstdint>
#include <stdexcept>

template <typename K, typename V>
static void destroy_node(BPlusTreeNode<K, V>* node){
    if(node == nullptr) return;

    if(!node->leaf){
        for(size_t i = 0; i < node->children.size(); ++i){
            if(node->children[i] != nullptr){
                destroy_node(node->children[i]);
                node->children[i] = nullptr;
            }
        }
    }

    delete node;
}

template <typename K, typename V>
BPlusTree<K,V>::BPlusTree(int order): root(nullptr), order(order){
    if(order < 2){
        throw std::invalid_argument("BPlusTree order must be >= 2");
    }
    root = new BPlusTreeNode<K,V>(true);
}

template <typename K, typename V>
BPlusTree<K,V>::~BPlusTree(){
    if(root != nullptr){
        destroy_node(root);
        root = nullptr;
    }
}

template <typename K, typename V>
bool BPlusTree<K,V>::search(const K& key, V& out_value) const{
    if(root == nullptr) return false;

    BPlusTreeNode<K,V>* current = root;

    while(!current->leaf){
        auto it = std::upper_bound(current->keys.begin(), current->keys.end(), key);
        int index = static_cast<int>(std::distance(current->keys.begin(), it));
        current = current->children[index];
    }

    auto it = std::lower_bound(current->keys.begin(), current->keys.end(), key);
    int index = static_cast<int>(std::distance(current->keys.begin(), it));

    if(index < static_cast<int>(current->keys.size()) && current->keys[index] == key){
        out_value = current->values[index];
        return true;
    }

    return false;
}

template <typename K, typename V>
bool BPlusTree<K,V>::update(const K& key, const V& new_value){
    if(root == nullptr) return false;

    BPlusTreeNode<K,V>* current = root;

    while(!current->leaf){
        auto it = std::upper_bound(current->keys.begin(), current->keys.end(), key);
        int index = static_cast<int>(std::distance(current->keys.begin(), it));
        current = current->children[index];
    }

    auto it = std::lower_bound(current->keys.begin(), current->keys.end(), key);
    int index = static_cast<int>(std::distance(current->keys.begin(), it));

    if(index < static_cast<int>(current->keys.size()) && current->keys[index] == key){
        current->values[index] = new_value;
        return true;
    }

    return false;
}

template <typename K, typename V>
void BPlusTree<K,V>::insert(const K& key, const V& value){
    if(root->keys.size() == static_cast<size_t>(2*order - 1)){
        BPlusTreeNode<K,V>* new_root = new BPlusTreeNode<K,V>(false);
        new_root->children.push_back(root);
        _split_child(new_root, 0);
        root = new_root;
    }

    _insert_non_full(root, key, value);
}

template <typename K, typename V>
void BPlusTree<K,V>::_insert_non_full(BPlusTreeNode<K,V>* node, const K& key, const V& value){
    if(node->leaf){
        auto it = std::lower_bound(node->keys.begin(), node->keys.end(), key);
        int index = static_cast<int>(std::distance(node->keys.begin(), it));

        // Prevent duplicate-key rows: update existing value
        if(index < static_cast<int>(node->keys.size()) && node->keys[index] == key){
            node->values[index] = value;
            return;
        }

        node->keys.insert(node->keys.begin() + index, key);
        node->values.insert(node->values.begin() + index, value);
        return;
    }

    auto it = std::upper_bound(node->keys.begin(), node->keys.end(), key);
    int index = static_cast<int>(std::distance(node->keys.begin(), it));

    if(node->children[index]->keys.size() == static_cast<size_t>(2*order - 1)){
        _split_child(node, index);

        if(key >= node->keys[index]) index++;
    }

    _insert_non_full(node->children[index], key, value);
}

template <typename K, typename V>
void BPlusTree<K,V>::_split_child(BPlusTreeNode<K,V>* parent, int index){
    BPlusTreeNode<K,V>* child = parent->children[index];
    BPlusTreeNode<K,V>* new_node = new BPlusTreeNode<K,V>(child->leaf);

    // separator promoted to parent
    parent->keys.insert(parent->keys.begin() + index, child->keys[order - 1]);
    parent->children.insert(parent->children.begin() + index + 1, new_node);

    if(child->leaf){
        // In B+ split, right leaf keeps promoted key
        new_node->keys.assign(child->keys.begin() + (order - 1), child->keys.end());
        new_node->values.assign(child->values.begin() + (order - 1), child->values.end());

        child->keys.erase(child->keys.begin() + (order - 1), child->keys.end());
        child->values.erase(child->values.begin() + (order - 1), child->values.end());

        new_node->next = child->next;
        child->next = new_node;
    } else {
        // Internal split (B-tree-style separator move)
        new_node->keys.assign(child->keys.begin() + order, child->keys.end());
        new_node->children.assign(child->children.begin() + order, child->children.end());

        child->keys.erase(child->keys.begin() + (order - 1), child->keys.end());
        child->children.erase(child->children.begin() + order, child->children.end());
    }
}

template <typename K, typename V>
bool BPlusTree<K,V>::remove(const K& key){
    if(root == nullptr || root->keys.empty()) return false;

    // only report true if key existed
    V tmp;
    if(!search(key, tmp)) return false;

    _delete(root, key);

    if(root->keys.empty() && !root->leaf){
        BPlusTreeNode<K,V>* old_root = root;
        root = root->children[0];
        delete old_root;
    }

    return true;
}

template <typename K, typename V>
void BPlusTree<K,V>::_delete(BPlusTreeNode<K,V>* node, const K& key){
    if(node->leaf){
        auto it = std::lower_bound(node->keys.begin(), node->keys.end(), key);
        int index = static_cast<int>(std::distance(node->keys.begin(), it));
        if(index < static_cast<int>(node->keys.size()) && node->keys[index] == key){
            node->keys.erase(node->keys.begin() + index);
            node->values.erase(node->values.begin() + index);
        }
        return;
    }

    auto it = std::upper_bound(node->keys.begin(), node->keys.end(), key);
    int index = static_cast<int>(std::distance(node->keys.begin(), it));

    if(node->children[index]->keys.size() < static_cast<size_t>(order)){
        _fill_child(node, index);
        if(index > static_cast<int>(node->keys.size())){
            index--;
        }
    }

    _delete(node->children[index], key);
}

template <typename K, typename V>
void BPlusTree<K,V>::_fill_child(BPlusTreeNode<K,V>* node, int index){
    if(index != 0 && node->children[index - 1]->keys.size() >= static_cast<size_t>(order)){
        _borrow_from_prev(node, index);
    } else if(index != static_cast<int>(node->keys.size()) &&
              node->children[index + 1]->keys.size() >= static_cast<size_t>(order)){
        _borrow_from_next(node, index);
    } else {
        if(index != static_cast<int>(node->keys.size())){
            _merge(node, index);
        } else {
            _merge(node, index - 1);
        }
    }
}

template <typename K, typename V>
void BPlusTree<K,V>::_borrow_from_prev(BPlusTreeNode<K,V>* node, int index){
    BPlusTreeNode<K,V>* child = node->children[index];
    BPlusTreeNode<K,V>* sibling = node->children[index - 1];

    if(!child->leaf){
        child->keys.insert(child->keys.begin(), node->keys[index - 1]);
        child->children.insert(child->children.begin(), sibling->children.back());
        sibling->children.pop_back();

        node->keys[index - 1] = sibling->keys.back();
        sibling->keys.pop_back();
    } else {
        child->keys.insert(child->keys.begin(), sibling->keys.back());
        child->values.insert(child->values.begin(), sibling->values.back());
        sibling->keys.pop_back();
        sibling->values.pop_back();

        node->keys[index - 1] = child->keys.front();
    }
}

template <typename K, typename V>
void BPlusTree<K,V>::_borrow_from_next(BPlusTreeNode<K,V>* node, int index){
    BPlusTreeNode<K,V>* child = node->children[index];
    BPlusTreeNode<K,V>* sibling = node->children[index + 1];

    if(!child->leaf){
        child->keys.push_back(node->keys[index]);
        child->children.push_back(sibling->children.front());
        sibling->children.erase(sibling->children.begin());

        node->keys[index] = sibling->keys.front();
        sibling->keys.erase(sibling->keys.begin());
    } else {
        // Save first sibling entry before erase
        K moved_key = sibling->keys.front();
        V moved_val = sibling->values.front();

        child->keys.push_back(moved_key);
        child->values.push_back(moved_val);

        sibling->keys.erase(sibling->keys.begin());
        sibling->values.erase(sibling->values.begin());

        // Update parent separator safely
        if(!sibling->keys.empty()){
            node->keys[index] = sibling->keys.front();
        } else {
            // defensive fallback (should rarely happen in valid rebalance)
            node->keys[index] = child->keys.back();
        }
    }
}

template <typename K, typename V>
void BPlusTree<K,V>::_merge(BPlusTreeNode<K,V>* node, int index){
    BPlusTreeNode<K,V>* child = node->children[index];
    BPlusTreeNode<K,V>* sibling = node->children[index + 1];

    if(!child->leaf){
        child->keys.push_back(node->keys[index]);
        for(size_t i = 0; i < sibling->keys.size(); ++i){
            child->keys.push_back(sibling->keys[i]);
        }
        for(size_t i = 0; i < sibling->children.size(); ++i){
            child->children.push_back(sibling->children[i]);
        }
    } else {
        for(size_t i = 0; i < sibling->keys.size(); ++i){
            child->keys.push_back(sibling->keys[i]);
        }
        for(size_t i = 0; i < sibling->values.size(); ++i){
            child->values.push_back(sibling->values[i]);
        }
        child->next = sibling->next;
    }

    node->keys.erase(node->keys.begin() + index);
    node->children.erase(node->children.begin() + index + 1);

    delete sibling;
}

template <typename K, typename V>
std::vector<std::pair<K,V>> BPlusTree<K,V>::range_query(const K& start_key, const K& end_key) const{
    std::vector<std::pair<K,V>> result;
    if(root == nullptr) return result;

    BPlusTreeNode<K,V>* current = root;

    while(!current->leaf){
        auto it = std::upper_bound(current->keys.begin(), current->keys.end(), start_key);
        int index = static_cast<int>(std::distance(current->keys.begin(), it));
        current = current->children[index];
    }

    while(current != nullptr){
        for(size_t i = 0; i < current->keys.size(); ++i){
            if(current->keys[i] >= start_key && current->keys[i] <= end_key){
                result.push_back({current->keys[i], current->values[i]});
            } else if(current->keys[i] > end_key){
                return result;
            }
        }
        current = current->next;
    }

    return result;
}

template <typename K, typename V>
std::vector<std::pair<K,V>> BPlusTree<K,V>::get_all() const{
    std::vector<std::pair<K,V>> result;
    if(root == nullptr) return result;

    BPlusTreeNode<K,V>* current = root;

    while(!current->leaf){
        current = current->children[0];
    }

    while(current != nullptr){
        for(size_t i = 0; i < current->keys.size(); ++i){
            result.push_back({current->keys[i], current->values[i]});
        }
        current = current->next;
    }

    return result;
}

template <typename K, typename V>
void BPlusTree<K,V>::visualize_tree() const{
    std::cout << get_dot();
}

template <typename K, typename V>
std::string BPlusTree<K,V>::get_dot() const{
    std::string dot = "digraph BPlusTree{\nnode [shape=record];\n";

    if(root != nullptr){
        _add_nodes(dot, root);
        _add_edges(dot, root);
    }

    dot += "}\n";
    return dot;
}

template <typename K, typename V>
std::string BPlusTree<K,V>::get_json() const{
    auto to_json = [&](auto self, BPlusTreeNode<K,V>* node) -> std::string {
        std::string s = "{";
        s += "\"id\":" + std::to_string(reinterpret_cast<uintptr_t>(node)) + ",";
        s += "\"is_leaf\":" + std::string(node->leaf ? "true" : "false") + ",";
        s += "\"keys\":[";
        for(size_t i = 0; i < node->keys.size(); ++i){
            if(i > 0) s += ",";
            s += std::to_string(node->keys[i]);
        }
        s += "]";

        if(node->leaf){
            s += ",\"values\":[";
            for(size_t i = 0; i < node->values.size(); ++i){
                if(i > 0) s += ",";
                s += "\"" + node->values[i] + "\"";
            }
            s += "],";
            s += "\"next\":" + (node->next ? std::to_string(reinterpret_cast<uintptr_t>(node->next)) : "null");
        } else {
            s += ",\"children\":[";
            for(size_t i = 0; i < node->children.size(); ++i){
                if(i > 0) s += ",";
                s += self(self, node->children[i]);
            }
            s += "]";
        }

        s += "}";
        return s;
    };

    if(root == nullptr) return "null";
    return to_json(to_json, root);
}

template <typename K, typename V>
void BPlusTree<K,V>::_add_nodes(std::string& dot, BPlusTreeNode<K,V>* node) const{
    dot += "node" + std::to_string(reinterpret_cast<uintptr_t>(node)) + " [label=\"";

    for(size_t i = 0; i < node->keys.size(); ++i){
        if(i > 0) dot += " | ";
        dot += std::to_string(node->keys[i]);
    }

    dot += "\"];\n";

    if(!node->leaf){
        for(auto child : node->children){
            _add_nodes(dot, child);
        }
    }
}

template <typename K, typename V>
void BPlusTree<K,V>::_add_edges(std::string& dot, BPlusTreeNode<K,V>* node) const{
    if(!node->leaf){
        for(size_t i = 0; i < node->children.size(); ++i){
            dot += "node" + std::to_string(reinterpret_cast<uintptr_t>(node)) +
                   " -> node" + std::to_string(reinterpret_cast<uintptr_t>(node->children[i])) + ";\n";
            _add_edges(dot, node->children[i]);
        }
    } else if(node->next != nullptr){
        dot += "{rank=same; node" + std::to_string(reinterpret_cast<uintptr_t>(node)) +
               " -> node" + std::to_string(reinterpret_cast<uintptr_t>(node->next)) +
               " [style=dashed, constraint=false, color=blue];}\n";
    }
}

template <typename K, typename V>
size_t BPlusTree<K,V>::get_memory_usage() const{
    auto node_usage = [&](auto self, BPlusTreeNode<K,V>* node) -> size_t {
        if(node == nullptr) return 0;

        size_t usage = sizeof(BPlusTreeNode<K,V>);
        usage += node->keys.capacity() * sizeof(K);
        usage += node->values.capacity() * sizeof(V);
        for(const auto& v : node->values) usage += v.capacity();
        usage += node->children.capacity() * sizeof(BPlusTreeNode<K,V>*);

        if(!node->leaf){
            for(auto child : node->children){
                usage += self(self, child);
            }
        }
        return usage;
    };

    return node_usage(node_usage, root);
}

template class BPlusTree<int, std::string>;