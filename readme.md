# FreshWash Laundry Management System
### CS 432 – Databases · Assignments 3 & 4 · IIT Gandhinagar

**Course**: CS 432 – Databases &nbsp;|&nbsp; **Instructor**: Dr. Yogesh K. Meena &nbsp;|&nbsp; **Semester**: II (2025–2026)  


---

## 📌 Project Overview

This repository contains a two-module database project built around **FreshWash**, a laundry order management system. Across Assignments 3 and 4, the work spans building a custom ACID-compliant storage engine from scratch, a full-stack web application with concurrency testing, and a production-grade horizontal sharding implementation over physical MySQL nodes.

---

## 🧱 Module A — Custom B+ Tree Database Engine (C++ + Python)

A self-contained, high-performance database engine implemented from the ground up in C++ with a Python binding layer.

### What Was Built
| Component | Description |
|-----------|-------------|
| `BPlusTree.cpp / .h` | Full B+ Tree implementation in C++17 with O(log N) search, insert, update, delete |
| `BruteForceDB.cpp` | Linear-scan baseline for benchmarking comparison |
| `wrapper.cpp` | C-style Python-callable interface; compiled to `libdbms.so` |
| `bplustree.py` | Python ctypes wrapper exposing the C++ engine to Python tests and the Flask backend |
| `db_manager.py` | Table management layer: `create_table`, `insert`, `search`, `update`, `delete` |
| `transaction_manager.py` | Full ACID transaction control: `begin`, `commit`, `rollback` with a global serialization lock |
| `log_manager.py` | Write-Ahead Logging (WAL): persists every operation before commit for crash recovery |
| `demo_acid.py` | End-to-end 5-test ACID validation suite |
| `performance_analyzer.py` | Benchmarks B+ Tree vs Brute Force across 10k–100k records |

### Key Results
- **~1700× faster** point lookups vs brute-force linear scan
- All **4 ACID properties verified**: Atomicity, Consistency, Isolation, Durability
- WAL-based crash recovery restores state correctly after simulated failures
- Shared library (`libdbms.so`) reused by Module B Flask backend as a caching layer

---

## 🌐 Module B — Full-Stack Web Application (Assignment 3)

A complete laundry management platform built with **Flask (REST API) + React (Vite frontend)** backed by **MySQL** for persistent storage and the **Module A B+ Tree engine** as a caching and transaction layer.

### Application Features

#### Role-Based Access Control
Three distinct user roles with separate dashboards and API namespaces:
- **Admin** — manage services, pricing matrices, employees, view all orders and lost-item reports, global dashboard analytics
- **Employee** — review and approve pending orders, schedule delivery, adjust pricing, manage lost items
- **User** — place itemized laundry orders, track order status, submit feedback, view payment history

#### Dynamic Order System
- **Itemized Selection**: Users choose cloth types (e.g., Silk Saree) × service types (e.g., Dry Clean) from an Admin-configured matrix
- **Automated Pricing**: Real-time price calculation based on Admin-defined `service_type × cloth_type` rate tables
- **Enhanced Approval Flow**: Employees review item details, adjust final pricing, and are required to schedule a delivery time window during order approval
- **Dual-mode Creation**: Both Users and Employees use the same itemized schema and validation logic for order creation

#### Backend API Structure (`Module_B/app/backend/apis/`)
| Namespace | Endpoints |
|-----------|-----------|
| `auth/` | Login, logout, token-based session management |
| `admin/dashboard/` | Aggregated stats, revenue, order counts (scatter-gather across shards) |
| `admin/lost_items/` | Report and resolve lost/damaged items |
| `employee/orders/` | List pending orders, approve/reject with delivery scheduling |
| `user/orders/` | Create, list, cancel user orders |
| `user/stats/` | Personal usage statistics and payment history |
| `landing/` | Public endpoints (service catalogue, pricing preview) |

#### B+ Tree Caching Integration
The Flask backend imports `libdbms.so` via `bplustree.py` and uses the `DBManager` as an in-process hot cache for frequently accessed records (products, users, orders), achieving **38× faster reads** vs direct MySQL queries for cached keys.

### ACID & Concurrency Testing (9 Tests, 100% Pass Rate)

All tests run against the Module A B+ Tree transaction engine:

| Test | What It Verifies |
|------|-----------------|
| `ATOMICITY_CONCURRENT_INSERTS` | 50 inserts within a single transaction commit atomically |
| `ATOMICITY_MULTI_TABLE_UPDATES` | 3-table transaction (Users, Products, Orders) is all-or-nothing |
| `CONSISTENCY_CONSTRAINT_VALIDATION` | All data satisfies schema constraints post-transaction |
| `ISOLATION_CONCURRENT_UPDATES` | 20 concurrent threads on same key produce no dirty reads |
| `RACE_CONDITION_SAME_KEY` | 100 updates (10 threads × 10 iterations) on one key — no lost updates |
| `FAILURE_SIMULATION_ROLLBACK` | Deliberate failure triggers full rollback, no partial state |
| `FAILURE_SIMULATION_RECOVERY` | WAL replay restores committed data after simulated crash |
| `STRESS_TEST_HIGH_THROUGHPUT` | 10,000 ops across 100 threads — **~1,040 ops/sec**, 100% success |
| `DURABILITY_PERSISTENCE` | Committed data persists across process restart |

**Result**: 9/9 PASS in 9.70 seconds

---

## ⚡ Module B — Horizontal Database Sharding (Assignment 4)

The entire MySQL-backed data layer was re-architected to support **horizontal sharding** across 3 physical MySQL nodes, with zero downtime to the application's API surface.

### What Was Implemented

#### Physical Partitioning
8 core domain tables were split into **3 physical shard tables** per table (24 sharded tables total), distributed across 3 separate MySQL instances:
- `shard_0_laundry_order`, `shard_1_laundry_order`, `shard_2_laundry_order`
- Same pattern for: `payment`, `lost_item`, `feedback`, `order_item`, `member`, `employee`, `service_detail`

#### Deterministic Hash Routing (`shard_router.py`)
- **Strategy**: `shard_id = member_id % 3` — deterministic, no randomized memory hashing
- `get_table(table_name, member_id)` — resolves the correct physical shard table for any write or point-read
- All routing logic is centralized in `shard_router.py`; no inline shard logic exists in route handlers

#### Data Locality
All dependent tables (payments, lost items, feedback, order items) for a given order are stored in the **same shard as the parent order's member**. This eliminates cross-shard JOINs on the hot path.

#### Scatter-Gather for Global Queries
Admin and cross-user views (e.g., "all pending orders") fan out across all 3 shards in parallel via the `scatter_gather(cur, table_name, where_sql, params)` utility, then merge results in the application layer.

#### Locate-Then-Mutate Pattern
Mutations that arrive without a `member_id` (e.g., updating an order by `order_id` only) first call a `locate_<entity>_shard()` function that scans all shards to find the owning shard, then issues the mutation only to that shard. Direct cross-shard writes are structurally impossible.

#### `RoutedConnection` / `RoutedCursor` (`db.py`)
A transparent DB-API 2.0–compatible connection wrapper:
- Accepts **logical** shard table names (e.g., `freshwash.shard_0_laundry_order`) from existing route code
- Rewrites them to the correct **physical** MySQL node (host + port) at execution time
- Handles `INSERT … RETURNING` (PostgreSQL syntax) via a compatibility shim for MySQL's `LAST_INSERT_ID()`
- Translates PostgreSQL `interval 'N hours'` syntax to MySQL `DATE_ADD(... INTERVAL N HOUR)`
- Multi-shard single-statement detection raises a hard `ValueError` at runtime to prevent accidental cross-shard queries

#### Shard Configuration (Environment Variables)
```bash
export SHARD_HOST=10.0.116.184
export SHARD_PORTS=3307,3308,3309
export SHARD_DATABASE=BottleNeck
export SHARD_USER=BottleNeck
export SHARD_PASSWORD='password@123'
```

#### Idempotent Migration
`migrate_logical_shards_to_physical.py` uses explicit `SELECT 1` pre-checks before any `INSERT` to prevent duplicate data on system restarts. Original tables are preserved with `_backup` suffixes.

#### Verification
`verify_sharding.py` asserts row parity across shards and confirms zero cross-shard member ID overlaps.

---

## 📈 Performance Summary

| Metric | Value |
|--------|-------|
| B+ Tree vs Brute Force (point lookup) | **~1,700× faster** |
| B+ Tree cache vs direct MySQL | **38× faster** |
| Concurrent throughput (stress test) | **~1,040 ops/sec** |
| Max concurrent threads tested | **100** |
| Total stress-test operations | **10,000** |
| ACID test pass rate | **9/9 (100%)** |
| Sharded tables | **8 base tables × 3 shards = 24 physical tables** |
| Physical MySQL nodes | **3** |

---

## 📁 Repository Structure

```
CS432_Track1_Submission/
│
├── Module_A/
│   └── database/
│       ├── BPlusTree.cpp / .h          # C++17 B+ Tree core
│       ├── BruteForceDB.cpp / .h       # Baseline comparison engine
│       ├── wrapper.cpp                 # Python ctypes bridge
│       ├── libdbms.so                  # Compiled shared library (pre-built)
│       ├── bplustree.py                # Python wrapper
│       ├── db_manager.py               # Table + record management
│       ├── transaction_manager.py      # ACID transaction control (WAL)
│       ├── log_manager.py              # Write-Ahead Log manager
│       ├── demo_acid.py                # 5 ACID test scenarios
│       └── performance_analyzer.py    # Benchmark: B+ Tree vs brute force
│
├── Module_B/
│   ├── VERIFY_COMPLETE.sh              # One-shot verification script (Assignment 4)
│   ├── requirements.txt               # Python dependencies
│   ├── sql/schema.sql                 # MySQL schema with shard tables
│   │
│   └── app/
│       ├── backend/
│       │   ├── main.py                # Flask app entry point (port 5001)
│       │   ├── db.py                  # RoutedConnection / RoutedCursor (shard-aware DB-API)
│       │   ├── shard_router.py        # Centralized shard routing & scatter-gather
│       │   ├── auth.py                # JWT-based authentication
│       │   ├── routes.py              # Core B+ Tree–backed API routes
│       │   ├── bplustree.py           # Module A ctypes binding (Flask cache)
│       │   ├── tree_cache.py          # B+ Tree cache management
│       │   ├── migrate_logical_shards_to_physical.py  # Idempotent shard migration
│       │   ├── verify_sharding.py     # Row-parity & overlap validation
│       │   ├── test_module_b_complete_v2.py  # 9-test ACID+concurrency suite
│       │   ├── test_acid_api_level.py # API-level ACID tests
│       │   ├── test_acid_db_level.py  # DB-level ACID tests
│       │   ├── bench_module_b.py      # Throughput benchmark
│       │   ├── locustfile.py          # Locust load-test scenarios
│       │   └── apis/
│       │       ├── admin/             # Admin: dashboard, lost items, pricing
│       │       ├── employee/          # Employee: order approval & scheduling
│       │       ├── user/              # User: orders, payments, feedback, stats
│       │       ├── auth/              # Auth endpoints
│       │       └── landing/           # Public catalogue endpoints
│       │
│       └── frontend/                  # React (Vite) frontend (port 5173)
│           ├── src/
│           └── package.json
│
├── module_b_evidence.md               # Pre-generated ACID test evidence report
├── module_b_test.log                  # Full test execution log
├── test_results.json                  # Structured test metrics (JSON)
├── sharding_presentation_guide.md     # Sharding architecture walkthrough
└── readme.md                          # This file
```

---

## 🖥️ Local Setup & Running

### Prerequisites

| Dependency | Version | Purpose |
|------------|---------|---------|
| g++ | C++17+ | Compile Module A (optional if using pre-built `libdbms.so`) |
| Python | 3.8+ | Backend, tests, scripts |
| Node.js + npm | v18+ | React frontend |
| MySQL | 8.0+ | 3 instances on ports 3307, 3308, 3309 (for full sharding) |

---

### Option 1 — Run ACID Tests Only (No database required, ~15 seconds)

```bash
# Module A: 5 ACID engine tests
cd Module_A/database/
python3 demo_acid.py

# Module B: 9 concurrency + ACID tests
cd Module_B/app/backend/
python3 test_module_b_complete_v2.py
```

Expected output: all tests pass, results written to `test_results.json` and `module_b_evidence.md`.

---

### Option 2 — Verify Horizontal Sharding (Assignment 4, requires MySQL shards)

**Step 1 — Configure shard environment variables:**
```bash
export SHARD_HOST=10.0.116.184
export SHARD_PORTS=3307,3308,3309
export SHARD_DATABASE=BottleNeck
export SHARD_USER=BottleNeck
export SHARD_PASSWORD='password@123'
```

**Step 2 — Run the complete verification script:**
```bash
cd Module_B/
bash VERIFY_COMPLETE.sh
```

This script: checks shard connectivity → validates row parity → starts Flask → runs API tests → runs a Locust stress test (if installed) → generates a master evidence report.

**Step 3 — Manual shard verification:**
```bash
cd Module_B/app/backend/
python3 verify_sharding.py
```

---

### Option 3 — Run the Full Web Application (Development)

**Step 1 — Install Python dependencies:**
```bash
pip install -r Module_B/requirements.txt
```

**Step 2 — Set shard environment variables** (same as Option 2 above).

**Step 3 — Start the Flask backend:**
```bash
cd Module_B/app/backend/
python3 main.py
# Listening on http://localhost:5001
```

**Step 4 — Start the React frontend (new terminal):**
```bash
cd Module_B/app/frontend/
npm install
npm run dev
# Listening on http://localhost:5173
```

**Step 5 — Open the app:**  
Navigate to `http://localhost:5173` in your browser.

---

### Option 4 — Performance Benchmarks

```bash
# B+ Tree vs Brute Force
cd Module_A/database/
python3 performance_analyzer.py

# Module B throughput benchmark
cd Module_B/app/backend/
python3 bench_module_b.py
```

---

## 🔑 Test Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `nimba` |
| Employee | `ramesh.kumar` | `emp123` |

---

## 🐛 Troubleshooting

### `ImportError` for Module A in Module B
```bash
export PYTHONPATH="/path/to/Module_A/database:$PYTHONPATH"
```

### `Permission denied` on backend directory
```bash
chmod 755 Module_B/app/backend/
pip install --user -r Module_B/requirements.txt
```

### MySQL shard connection refused
Ensure all three MySQL instances are running and accessible on the configured host/ports. Check with:
```bash
mysql -h $SHARD_HOST -P 3307 -u $SHARD_USER -p$SHARD_PASSWORD -e "SELECT @@hostname;"
```

### Clean up stale test artifacts
```bash
cd Module_B/app/backend/
rm -f module_b_*.log test_results.json
python3 test_module_b_complete_v2.py
```

---

## 📚 Further Documentation

| Document | Contents |
|----------|----------|
| [Module_B/app/backend/module_b_evidence.md](Module_B/app/backend/module_b_evidence.md) | Pre-generated ACID test evidence with pass/fail details |
| [Module_A/Module_A_Implementation_Report.md](Module_A/Module_A_Implementation_Report.md) | Deep-dive on B+ Tree design decisions |
| [Module_A/report.ipynb](Module_A/report.ipynb) | Performance analysis notebook |
| [Module_B/app/backend/traceability_matrix.md](Module_B/app/backend/traceability_matrix.md) | ACID requirement → test mapping |
| [Module_B/app/backend/benchmarks.ipynb](Module_B/app/backend/benchmarks.ipynb) | Throughput benchmark notebook |

---

*© 2026 Indian Institute of Technology, Gandhinagar. All rights reserved.*
