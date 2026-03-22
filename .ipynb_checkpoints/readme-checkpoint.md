# FreshWash DBMS: B+ Tree Indexing & Management System

Welcome to the FreshWash DBMS project. This repository contains a high-performance database indexing engine (Module A) and a full-stack laundry management application (Module B) featuring role-based access control (RBAC), SQL optimization, and an integrated B+ Tree cache.

---

## Quick Start

### 1. Prerequisites
Ensure you have the following installed:
- C++ Compiler: g++ (with support for C++17)
- Python: 3.8+ (with psycopg2, Flask, Flask-CORS, pandas, matplotlib, Faker)
- Database: PostgreSQL 15+
- Frontend: Node.js (v18+) and npm

---

## Module A: The Indexing Engine

Module A implements a high-performance B+ Tree from scratch in C++ with a Python wrapper.

### Compilation
Compile the C++ core into a shared library for Python use:
```bash
cd Module_A/database/
g++ -shared -o libdbms.so -fPIC BPlusTree.cpp BruteForceDB.cpp wrapper.cpp
```

### Performance Benchmarking
Run the benchmarking suite to compare the B+ Tree against a linear search (Brute Force) approach:
```bash
# Pre-loading libstdc++ may be required in some Linux environments (e.g., Conda)
LD_PRELOAD=/usr/lib/libstdc++.so.6 python3 performance_analyzer.py
```

---

## Module B: FreshWash Web Application

Module B is a full-stack system for managing laundry operations, optimized for performance and security.

### 1. Database Setup
Initialize the PostgreSQL database:
```bash
# Create the database
sudo -u postgres psql -c "CREATE DATABASE freshwashdb ENCODING 'UTF8';"

# Load the schema (from the root directory)
sudo -u postgres psql -d freshwashdb -f Module_B/sql/schema.sql
```
*Default DB Credentials: User: postgres, Password: mypassword, DB: freshwashdb*

### 2. Backend Setup
```bash
cd Module_B/app/backend/
pip install -r ../../requirements.txt

# Run the Flask server
python3 main.py
```
The backend will be available at http://localhost:5001.

### 3. Frontend Setup
```bash
cd Module_B/app/frontend/
npm install
npm run dev
```
The UI will be available at http://localhost:5173.

### 4. Integration Benchmarking
Run the detailed integration benchmark to see the Module A B+ Tree engine acting as a cache for the PostgreSQL database:
```bash
cd Module_B/app/backend/
python3 bench_module_b.py
```

---

## Key Performance Insights

| Metric | Result | Impact |
| :--- | :--- | :--- |
| B+ Tree Search (vs Brute Force) | ~1700x Faster | Scales O(log N) for large datasets. |
| SQL Query Optimization | 85% Reduction | Targeted indexing on high-traffic JOINs. |
| Module A Cache Integration | 38x Faster Search | Outperforms DB-level B-Tree for point lookups. |

---

## Project Structure

- **Module_A/**: B+ Tree source code (C++/Python), benchmarks, and `report.ipynb`.
- **Module_B/**: 
  - `optimization_report.ipynb`: Detailed analysis of SQL optimizations and Module B performance.
  - `app/backend/`: Flask REST API, auth logic, cache integration, and `benchmarks.ipynb`.
  - `app/frontend/`: React-based dashboard UI.
  - `sql/`: PostgreSQL schema and optimization scripts.
- **dbms2.pdf**: Project documentation and requirements.
- **readme.md**: This overview file.

---

## Credentials for Testing

| Role | Username | Password |
| :--- | :--- | :--- |
| Admin | admin | nimba |
| Employee | ramesh.kumar | emp123 |
| User | (Register via UI) | - |

---

## License
This project is for academic purposes as part of the CS 432 Databases course.
