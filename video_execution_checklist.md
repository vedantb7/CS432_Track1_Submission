# Video Execution Checklist: Step-by-Step Commands

This checklist maps **directly** to the 4 video requirements from **Track1_Assignment4.pdf**:

| # | Requirement | Covered in |
|---|---|---|
| 1 | Show your sharded tables and explain the partitioning logic | **Phase 2** |
| 2 | Demonstrate a query being routed to the correct shard | **Phase 4** |
| 3 | Show a range query spanning multiple shards, returning correct results | **Phase 3** |
| 4 | Briefly explain your scalability trade-offs analysis | **Phase 5** |

---

### Phase 0: Prerequisites
Make sure you are on the **IITGN network** (required for shard access).

If you see "ModuleNotFoundError", run:
```bash
pip install pymysql cryptography
```

---

### Phase 1: Start Backend (Terminal 1)
```bash
cd Module_B/app/backend/
export SHARD_HOST=10.0.116.184
export SHARD_PORTS=3307,3308,3309
export SHARD_DATABASE=BottleNeck
export SHARD_USER=BottleNeck
export SHARD_PASSWORD='password@123'
python3 main.py
```
**What you should see**: Flask starting on `http://localhost:5001` without shard connection errors.

> If the backend is already running, skip this step.

---

### Phase 2: Show Sharded Tables & Explain Partitioning Logic — *Requirement #1*

**Goal**: Prove that data is split across 3 physical shards and explain how.

#### Step 2a — Run verification script (Terminal 2)
```bash
cd Module_B/app/backend/
python3 verify_sharding.py
```
**What you should see**:
```
Shard 0 (xxx) row_count=NN
Shard 1 (xxx) row_count=NN
Shard 2 (xxx) row_count=NN
Total sharded rows: NNN
No duplication found and ownership checks passed!
```

**Say**: *"This script connects to all 3 shards, counts rows in each, and validates that every order's member_id hashes to the correct shard — and no order_id is duplicated across shards."*

#### Step 2b — Show tables in phpMyAdmin (Browser)

1. **Shard 0**: Go to [http://10.0.116.184:8080](http://10.0.116.184:8080)
   - Login: `BottleNeck` / `password@123`
   - Click on database `BottleNeck` → table `laundry_order`
   - **Point out**: `member_id` values are all multiples of 3 (0, 3, 6, 9...)

2. **Shard 1**: Go to [http://10.0.116.184:8081](http://10.0.116.184:8081)
   - Click `laundry_order`
   - **Point out**: `member_id` values are 1, 4, 7, 10... (remainder 1)

3. **Shard 2**: Go to [http://10.0.116.184:8082](http://10.0.116.184:8082)
   - Click `laundry_order`
   - **Point out**: `member_id` values are 2, 5, 8, 11... (remainder 2)

**Say**:
> *"We chose `member_id` as our shard key because it has high cardinality — each member is unique — it's stable since member IDs don't change after creation, and it's query-aligned since most of our API queries filter by member.*
>
> *We use **hash-based partitioning** with the formula `shard_id = member_id % 3`. So member_id 6 goes to Shard 0 because 6 mod 3 = 0, member_id 7 goes to Shard 1 because 7 mod 3 = 1, and so on. As you can see, data is evenly distributed across all three nodes with no overlap or duplication."*

---

### Phase 3: Range Query Spanning Multiple Shards — *Requirement #3*

**Goal**: Show a query that hits ALL 3 shards and returns combined results.

#### Step 3a — Admin Dashboard API via curl (Terminal 2)
This endpoint aggregates order counts and revenue from all 3 shards:
```bash
curl -s http://localhost:5001/api/admin/dashboard | python3 -m json.tool
```
**What you should see**: JSON with `totalOrders`, `totalRevenue`, `pendingOrders` etc. — these numbers are the **sum across all 3 shards**.

**Say**:
> *"This Admin Dashboard endpoint uses a **scatter-gather pattern**. The code loops over all 3 shards, executes the same query — like SELECT COUNT and SUM — on each shard's `laundry_order` table, and then adds up the results in Python before returning the combined total. No single shard has all the data — the application has to query every shard to get the full picture."*

#### Step 3b — Employee Orders list (scatter-gather returning actual rows)
Pick an employee_id that has orders across shards. This queries all 3 shards and merges actual order rows:
```bash
curl -s http://localhost:5001/api/employee/orders/1 | python3 -m json.tool
```
**What you should see**: A JSON array of order objects with different `member_id` values — some will be from Shard 0, some from Shard 1, some from Shard 2.

**Say**:
> *"This is a true cross-shard range query. The employee orders endpoint queries `laundry_order` in each of the 3 shards, collects all matching rows, merges them in the application layer, and sorts by order_date. The response contains orders from members assigned to different shards — like member_id 3 from Shard 0 and member_id 1 from Shard 1 — all combined into a single result set."*

#### Step 3c (Optional) — Verify in code
You can briefly show the code at `apis/employee/orders/routes.py` lines 45-69 which has the explicit `for shard_id in range(N_SHARDS)` scatter-gather loop.

---

### Phase 4: Point Query Routed to Correct Shard — *Requirement #2*

**Goal**: Show that a single-key operation goes to exactly one shard (not all 3).

#### Step 4a — Fetch a single member's orders (Terminal 2)
```bash
curl -s http://localhost:5001/api/user/orders/3 | python3 -m json.tool
```

**Check Terminal 1 (backend logs)**: You should see:
```
[SHARD ROUTE] member_id=3 -> shard=0
```

**Say**: *"When we query orders for member_id 3, the shard router computes 3 mod 3 = 0 and routes directly to Shard 0. It doesn't touch Shard 1 or Shard 2 at all."*

#### Step 4b — Route to a different shard
```bash
curl -s http://localhost:5001/api/user/orders/1 | python3 -m json.tool
```

**Check Terminal 1**: You should see:
```
[SHARD ROUTE] member_id=1 -> shard=1
```

**Say**: *"Now with member_id 1, the router computes 1 mod 3 = 1 and goes to Shard 1 instead. The application always knows exactly which shard to query — this is the key advantage of hash-based routing for point lookups."*

#### Step 4c (Optional) — Data mutation routing
If you can update an order status via the UI or curl:
```bash
curl -s -X PUT http://localhost:5001/api/employee/orders/10/status \
  -H "Content-Type: application/json" \
  -d '{"order_status": "Processing", "employee_id": 1}'
```

**Check Terminal 1** for: `[SHARD ROUTE] member_id=... -> shard=...`

**Say**: *"Even write operations use the shard router — the system computed the shard from the member_id, connected to that one node, and executed the update without searching the entire cluster."*

---

### Phase 5: Scalability Trade-offs Analysis — *Requirement #4*

**Goal**: Briefly explain the trade-offs of your sharding design.

No commands needed — just speak with the dashboard or terminal visible on screen.

**Say**:
> *"Finally, the scalability trade-offs of our sharding design:*
>
> ***Horizontal vs Vertical Scaling**: Instead of upgrading a single database server with more CPU or RAM — which is vertical scaling — sharding lets us scale out by adding more nodes. Each shard handles only a fraction of the data and load, so the system can grow linearly.*
>
> ***Consistency**: Single-record operations are strongly consistent because each record lives in exactly one shard. However, our scatter-gather queries — like the dashboard — read from multiple nodes sequentially, so if a write happens on one shard while we're reading another, the aggregated result could be slightly stale.*
>
> ***Availability**: If one shard goes down, only about one-third of the data becomes unavailable. The other two shards continue serving requests normally. Users whose member_id maps to the failed shard would experience downtime, but the rest of the system stays operational.*
>
> ***Partition Tolerance**: Our system handles shard failures gracefully. Point queries to the downed shard return errors, while the remaining shards operate independently. We could improve this with replication across shards, but that's beyond our current scope."*

---

### Quick Reference — Pre-Recording Checklist

- [ ] Connected to **IITGN network**
- [ ] Backend (`main.py`) running on port 5001
- [ ] Two terminal windows visible (one for backend logs, one for commands)
- [ ] Browser ready for phpMyAdmin (3 tabs: ports 8080, 8081, 8082)
- [ ] Frontend running on `localhost:5173` (optional — curl demos work without it)

### Estimated Video Duration: ~5 minutes
| Phase | Time |
|---|---|
| Phase 1 (start backend) | 15s |
| Phase 2 (sharded tables) | 1.5 min |
| Phase 3 (range query) | 1.5 min |
| Phase 4 (point routing) | 1 min |
| Phase 5 (trade-offs) | 1 min |
