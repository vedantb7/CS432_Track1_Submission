# FreshWash DBMS: B+ Tree Indexing & Management System

A high-performance database indexing engine with full ACID transaction support and a complete web application for laundry management.

**Course**: CS 432 – Databases (Assignment 3)  |  **Status**: ✅ Complete & Verified  |  **Test Pass Rate**: 9/9 (100%)

---

## 🎯 What's This Project?

**Module A**: A high-performance B+ Tree database engine (C++) with full ACID compliance, crash recovery, and ~1700x faster lookups than brute force.

**Module B (Assignment 3)**: A full-stack web application (Flask + React) with comprehensive concurrency testing: 100 threads, 10,000 operations, 994 ops/sec throughput, all ACID properties verified.

**Module B (Assignment 4 - NEW ✨)**: Implementation of **Horizontal Database Sharding**. We physically partitioned 8 core tables into 3 shards each, utilizing a `member_id % 3` hashing strategy. A centralized router (`shard_router.py`) handles point lookups, while dynamic scatter-gather logic parallelizes complex multi-shard queries across User, Employee, and Admin endpoints. Zero cross-shard writes ensure strict isolation while providing horizontal scalability!

---

## ⚡ Quick Start

### Verify Horizontal Sharding & ACID (Assignment 4)
```bash
cd Module_B/
bash VERIFY_COMPLETE.sh
```
*Note: This runs database checks, starts the Flask server, runs API validation, executes a Locust stress test (if installed), and generates a master evidence report.*

### Test Module B Concurrency Only (10 seconds)
```bash
cd Module_B/app/backend/
python3 test_module_b_complete_v2.py  # 9/9 tests PASS
```

Expected: All tests pass, results saved to `test_results.json` and `module_b_evidence.md`

### Test Module A Only (5 seconds)
```bash
cd Module_A/database/
python3 demo_acid.py  # All 5 ACID tests PASS
```

### Run the Full Web Application (15 minutes)
```bash
# Backend API
cd Module_B/app/backend/
pip install -r ../../requirements.txt
python3 main.py  # http://localhost:5001

# Frontend UI (another terminal)
cd Module_B/app/frontend/
npm install && npm run dev  # http://localhost:5173
```

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [Module_A/database/](Module_A/database/) | B+ Tree engine with ACID support |
| [Module_B/ReadMe.md](Module_B/ReadMe.md) | Setup guide with troubleshooting (10 parts) |
| [Module_B/app/backend/test_module_b_complete_v2.py](Module_B/app/backend/test_module_b_complete_v2.py) | Complete test suite (9 ACID tests) |
| [Module_B/app/backend/test_results.json](Module_B/app/backend/test_results.json) | Test metrics (generated after run) |
| [Module_B/app/backend/module_b_evidence.md](Module_B/app/backend/module_b_evidence.md) | Evidence report (generated after run) |

---

## 📊 Test Results Summary

### Module A: ACID Engine (5 Tests)
✅ Atomicity: Multi-table transactions commit as unit
✅ Consistency: All data satisfies constraints  
✅ Isolation: Concurrent access properly serialized
✅ Durability: Data persists across crashes
✅ Recovery: WAL replay restores state

### Module B: Concurrency & Stress Testing (9 Tests)

| Test | Status | What It Tests |
|------|--------|--------------|
| ATOMICITY_CONCURRENT_INSERTS | ✅ PASS | 50 inserts in 1 transaction |
| ATOMICITY_MULTI_TABLE_UPDATES | ✅ PASS | 3-table atomic transaction |
| CONSISTENCY_CONSTRAINT_VALIDATION | ✅ PASS | Valid data states |
| ISOLATION_CONCURRENT_UPDATES | ✅ PASS | 20 concurrent threads |
| RACE_CONDITION_SAME_KEY | ✅ PASS | 100 updates on same key |
| FAILURE_SIMULATION_ROLLBACK | ✅ PASS | Transaction undo |
| FAILURE_SIMULATION_RECOVERY | ✅ PASS | Crash recovery |
| STRESS_TEST_HIGH_THROUGHPUT | ✅ PASS | 10,000 ops @ 994 ops/sec |
| DURABILITY_PERSISTENCE | ✅ PASS | Data persists |

**Results**: 9/9 PASS (100%) | Duration: 10.23 seconds

---

## 📈 Performance Metrics

| Metric | Value |
|--------|-------|
| B+ Tree Search (vs Brute Force) | ~1700x faster |
| Concurrent Throughput | 994 ops/sec |
| Max Concurrent Threads | 100 |
| Total Operations Stress Test | 10,000 |
| Test Success Rate | 100% |
| SQL Query Optimization | 85% faster |
| Cache Integration (vs PostgreSQL) | 38x faster |

---

## 📁 Project Structure

```
.
├── Module_A/
│   └── database/
│       ├── BPlusTree.cpp/h           # C++ B+ Tree implementation
│       ├── libdbms.so                # Compiled shared library
│       ├── db_manager.py             # Transaction manager
│       ├── transaction_manager.py    # ACID control
│       ├── log_manager.py            # Write-Ahead Logging
│       ├── demo_acid.py              # 5 ACID tests
│       └── report.ipynb              # Analysis
│
├── Module_B/
│   ├── ReadMe.md                     # Setup guide (Parts 1-10)
│   ├── app/backend/
│   │   ├── main.py                   # Flask API
│   │   ├── test_module_b_complete_v2.py  # 9 ACID+concurrency tests
│   │   ├── test_results.json         # Generated metrics
│   │   ├── module_b_evidence.md      # Generated evidence report
│   │   ├── bench_module_b.py         # Performance benchmark
│   │   └── bplustree.py              # Module A integration
│   ├── app/frontend/
│   │   ├── package.json
│   │   ├── src/
│   │   └── ...React components...
│   ├── sql/schema.sql                # PostgreSQL schema
│   └── report/optimization_report.ipynb  # Performance analysis
│
├── readme.md                         # This file
└── dbms2.pdf                         # Course specification
```

---

## 🔧 Prerequisites

- **C++ Compiler**: g++ (C++17 support)
- **Python**: 3.8+ with packages: psycopg2, Flask, Flask-CORS, pandas, matplotlib, Faker
- **Database**: PostgreSQL 15+ (optional - for Module B extended features)
- **Frontend**: Node.js v18+ with npm (optional - for web UI)
- **OS**: Linux

---

## 🧪 Test Coverage

### Module A: 5 ACID Test Scenarios
- ✅ Atomicity: Single and multi-table transactions
- ✅ Consistency: Constraint validation
- ✅ Isolation: Concurrent write serialization
- ✅ Durability: Persistence after restart
- ✅ Recovery: Crash recovery from transaction log

### Module B: 9 Comprehensive Tests
- ✅ 2 Atomicity tests (concurrent inserts, multi-table)
- ✅ 1 Consistency test (constraint validation)
- ✅ 2 Isolation tests (concurrent updates, race conditions)
- ✅ 2 Failure handling tests (rollback, recovery)
- ✅ 1 Stress test (10,000 ops, 100 concurrent threads)
- ✅ 1 Durability test (data persistence)

---

## 🚀 Execution Paths

### Path 1: Verify ACID Compliance (Minimum)
```bash
# Module A ACID tests
cd Module_A/database/ && python3 demo_acid.py

# Module B Concurrency tests  
cd Module_B/app/backend/ && python3 test_module_b_complete_v2.py
```
**Time**: ~15 seconds | **Result**: All tests pass ✅

### Path 2: View Generated Results
```bash
cd Module_B/app/backend/
cat test_results.json        # Structured metrics
cat module_b_evidence.md     # Full evidence report
```

### Path 3: Full Web Stack (Development)
```bash
# Setup database
sudo -u postgres psql -c "CREATE DATABASE freshwashdb ENCODING 'UTF8';"
sudo -u postgres psql -d freshwashdb -f Module_B/sql/schema.sql

# Start backend
cd Module_B/app/backend/
pip install -r ../../requirements.txt
python3 main.py

# Start frontend (another terminal)
cd Module_B/app/frontend/
npm install && npm run dev
```

### Path 4: Performance Benchmarking
```bash
# B+ Tree vs Brute Force
cd Module_A/database/ && python3 performance_analyzer.py

# Module B vs PostgreSQL
cd Module_B/app/backend/ && python3 bench_module_b.py
```

---

## 🔐 Test Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | admin | nimba |
| Employee | ramesh.kumar | emp123 |

---

## 📋 Key Features

### Module A: Database Engine
- ✅ B+ Tree indexing (O(log N) complexity)
- ✅ Transaction ACID support
- ✅ Write-Ahead Logging (WAL)
- ✅ Crash recovery
- ✅ Serialization-based concurrency control
- ✅ ~1700x faster than brute force

### Module B: Web Application
- ✅ Flask REST API with role-based access
- ✅ React frontend dashboard
- ✅ PostgreSQL integration
- ✅ B+ Tree caching layer
- ✅ Full concurrency testing suite
- ✅ Performance benchmarking tools

### Dynamic Order System
- ✅ **Dynamic Itemized Selection**: Users select specific cloth types and services (e.g., Silk Saree + Dry Clean).
- ✅ **Automated Pricing**: Real-time price calculation based on Admin-defined service/type matrices.
- ✅ **Enhanced Verification Flow**: Employees review item detail, adjust final pricing, and must schedule delivery times during approval.
- ✅ **Dual-mode Creation**: Both users and employees use the same itemized schema and validation logic.

### Horizontal Database Sharding (Assignment 4)
- ✅ **Physical Partitioning**: 8 core tables split into 3 isolated physical shard tables (e.g., `shard_0_laundry_order`, `shard_1_laundry_order`).
- ✅ **Idempotent Data Migrations**: Initial migration scripts pre-check state explicitly using `SELECT 1` queries to safely prevent duplication faults on arbitrary system reboots.
- ✅ **Deterministic Routing**: Custom `shard_router.py` hashes traffic dynamically using `member_id % N_SHARDS` without relying on randomized memory hashing.
- ✅ **Data Locality**: Dependent tables (payments, lost items, services) strictly reside in the same shard as their parent order to eliminate cross-shard JOIN degradation.
- ✅ **Strict Locate-Then-Mutate Logic**: Direct mutations without a `member_id` query an explicit global `locate_` function. Natively throwing `ValueError`s ensures zero accidental cross-shard corruption during data mutation.
- ✅ **Scatter-Gather Parallelization**: Global APIs (like the Admin dashboard and cross-user list views) automatically aggregate shards via custom `scatter_gather` abstractions iteratively across all partitions.
- ✅ **Data Protection**: Zero data loss during initialization, and legacy tables securely preserved using `_backup` suffixes blocking any active regression.
- ✅ **Validation Guardrails**: Built-in verification scripts (`verify_sharding.py`) continuously monitor row parity and rigorously assert zero cross-shard overlaps.

---

## 📚 For More Details

- **Module A Deep Dive**: [Module_A/database/MODULE_A_EVIDENCE.md](Module_A/database/MODULE_A_EVIDENCE.md)
- **Module B Setup**: [Module_B/ReadMe.md](Module_B/ReadMe.md) (Parts 1-10)
- **Performance Analysis**: [Module_B/report/optimization_report.ipynb](Module_B/report/optimization_report.ipynb)

---

## ✅ Verification Checklist

Before submission:

- [x] Module A ACID compliance verified
- [x] Module B concurrency tests all pass (9/9)
- [x] Performance metrics captured (994 ops/sec)
- [x] Evidence documentation complete
- [x] Code compilable (C++ and Python)
- [x] No external dependencies needed (except Python packages)
- [x] Full documentation provided
- [x] Reproducible results

---

## 📞 Troubleshooting

### Import Errors
```bash
export PYTHONPATH="/path/to/Module_A/database:$PYTHONPATH"
```

### Permission Denied
```bash
chmod 755 Module_B/app/backend/
pip install --user -r Module_B/requirements.txt
```

### Clean Previous Runs
```bash
cd Module_B/app/backend/
rm -f module_b_*.log test_results.json
python3 test_module_b_complete_v2.py
```

### PostgreSQL Not Found
Module B tests work without PostgreSQL. Full web stack requires it.
```bash
sudo apt-get install postgresql postgresql-contrib
```

---

## 📜 Assignment Details

**Course**: CS 432 – Databases
**Assignment**: 3 (Track 1 - ACID Properties & Concurrency)
**Academic Year**: Semester II (2025-2026)
**Instructor**: Dr. Yogesh K. Meena
**Institution**: Indian Institute of Technology, Gandhinagar
**Date**: March 23 – April 5, 2026

© 2026 Indian Institute of Technology, Gandhinagar. All rights reserved.

