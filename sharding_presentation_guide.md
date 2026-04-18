# Horizontal Sharding Presentation Guide

This guide provides exactly what to say and the commands to run during your viva/presentation to flawlessly demonstrate your sharding implementation.

---

## Preparation
Before starting the presentation, ensure your backend terminal is running and your virtual environment is activated:
```bash
cd Module_B/app/backend/
source venv/bin/activate
```

---

## 1. Show Sharded Tables & Explain Partitioning Logic

**Action**: Open `change(1).md` or your SQL tools (like DBeaver) to show the databases on ports 3307, 3308, and 3309. Show the `shard_router.py` file.

**What to Say:**
> "To handle horizontal scaling without touching our core B+ Tree engine, we implemented physical database sharding at the application layer. We provisioned 3 distinct MySQL server instances operating on ports 3307, 3308, and 3309.
> 
> Our partitioning logic uses a deterministic hash-based strategy. Instead of complex MurmurHash, we opted for an elegant modulo arithmetic approach on the primary business entity: **`member_id % 3`**. 
> 
> We designated 8 core tracking tables (like `laundry_order`, `payment`, and `feedback`) to be horizontally partitioned. Because payments and feedback are always linked to an order, and an order is linked to a member, this strategy ensures critical data locality. A user querying their own invoices will only ever hit one physical shard, avoiding expensive cross-node JOINs."

---

## 2. Demonstrate a Query Being Routed to the Correct Shard

**Action**: Run the custom demo script I created for you in your terminal.

```bash
python3 demo_sharding.py
```

**What to Say:**
> "Let me demonstrate our point-lookup routing in action. I've written a script that resolves queries for specific members. 
> 
> Watch the terminal output. When we query for **Member ID 5**, the router calculates `5 % 3`, resulting in **Shard 2**. The backend exclusively connects to the database on Port 3309, retrieving the records seamlessly. 
> 
> When we query for **Member ID 13**, `13 % 3` evaluates to **Shard 1**. The connection is instantly routed to Port 3308. Notice how the application code abstracts this completely from the business logic—maintaining strict backward compatibility with our Module A engine."

---

## 3. Show a Range Query Spanning Multiple Shards (Scatter-Gather)

**Action**: The result for this is built into the bottom half of the `python3 demo_sharding.py` output. Alternatively, you can show the admin dashboard on the frontend (`http://localhost:5173/admin-auth` -> Log in as newadmin / admin123).

**What to Say:**
> "While point lookups are O(1), analytics queries like 'Total System Revenue' require reading from the entire dataset. In a sharded environment, you cannot run a global `SUM()` directly on one database.
> 
> To solve this, we implemented a **Scatter-Gather** mechanism. As you can see in the terminal Output, the application 'scatters' the `SELECT SUM(total_amount)` query to Shard 0, Shard 1, and Shard 2. 
> 
> Each physical node computes its local sum independently using its own CPU and memory. Finally, the application 'gathers' these intermediate results and aggregates them in-memory to present the single globally accurate Total Revenue. This exactly mirrors MapReduce concepts on a micro-scale."

---

## 4. Scalability Trade-Offs Analysis

**Action**: You can keep the slide or the terminal open as you explain this final point verbally.

**What to Say:**
> "To conclude, I performed a scalability capabilities and trade-offs analysis on this architecture.
> 
> **Advantages:**
> 1. **Horizontal Scalability:** We are no longer bound by vertical scaling (CPU/RAM of a single machine). We can theoretically add N shards.
> 2. **Fault Isolation:** If Shard 1 goes offline, User traffic hitting Shards 0 and 2 remains 100% unaffected. 
> 3. **Preserved B+Tree:** Because the abstraction sits in Python, we maintained 100% compatibility with our C++ B+Tree index engine from Module A without rewriting it.
> 
> **Trade-Offs:**
> 1. **Complex Aggregations:** Range or aggregate queries are slower because they trigger scatter-gather sweeps requiring network hops to all 3 shards.
> 2. **Rebalancing Overhead:** Unlike consistent hashing, using a hardcoded modulo (`% 3`) means if we ever want to scale to 4 shards, we must perform a complex data migration phase to redistribute the hashes.
> 
> Overall, this design perfectly balances High-Availability (HA) reads for standard users while isolating the complexity of distributed systems from our storage engine."
