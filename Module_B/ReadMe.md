# Module B: FreshWash Web Application & Performance Optimization

This module contains the full-stack FreshWash application, a laundry management system built with PostgreSQL, Flask, and React. It also includes comprehensive benchmarking and optimization reports.

## Key Components

### 1. Database & Optimization
- sql/schema.sql: PostgreSQL schema with RBAC and audit triggers.
- optimization_report.ipynb: Analysis of SQL query optimization using B-Tree indexing.

### 2. Backend
- app/backend/main.py: Flask REST API server.
- app/backend/bplustree.py: Integration of Module A's B+ Tree as a high-performance cache.
- app/backend/benchmarks.ipynb: Performance benchmarking of Module B's indexing engine vs PostgreSQL.

### 3. Frontend
- app/frontend/: React-based administrative and user dashboard.

## Performance Summary
Module B leverages targeted SQL indexing to achieve an 85% reduction in complex query execution times and integrates an in-memory B+ Tree cache for near-instantaneous point lookups.
