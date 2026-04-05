#!/usr/bin/env bash
# ============================================================================
# VERIFY_COMPLETE.sh — CS432 Track 1 Module B
# Single command to run ALL ACID + concurrency + stress validations
#
# Usage:
#   bash VERIFY_COMPLETE.sh
#
# Output:
#   Module_B/app/backend/acid_db_results.json
#   Module_B/app/backend/acid_api_results.json
#   Module_B/app/backend/locust_results_stats.csv
#   Module_B/app/backend/locust_summary.json
#   Module_B/app/backend/final_evidence_report.md
#   Module_B/app/backend/traceability_matrix.md
#   Module_B/app/backend/all_results.json
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/app/backend"
MODULE_A_DIR="$SCRIPT_DIR/../Module_A/database"
LOCUST_BIN="${HOME}/.local/bin/locust"

export PYTHONPATH="$MODULE_A_DIR:${PYTHONPATH:-}"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'  # No Color

info()    { echo -e "${YELLOW}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[PASS]${NC}  $*"; }
error()   { echo -e "${RED}[FAIL]${NC}  $*"; }

PASS_COUNT=0
FAIL_COUNT=0

run_step() {
    local label="$1"; shift
    if "$@"; then
        success "$label"
        ((PASS_COUNT++)) || true
    else
        error "$label"
        ((FAIL_COUNT++)) || true
    fi
}

echo ""
echo "========================================================================"
echo "  CS432 Track 1 Module B — Full ACID & Stress Validation"
echo "========================================================================"
echo "  Backend: $BACKEND_DIR"
echo "  Started: $(date -Iseconds)"
echo "========================================================================"

# ── Step 0: Clean up old stale log files ────────────────────────────────────
info "Step 0: Cleaning up stale test log files …"
cd "$BACKEND_DIR"
rm -f acid_a*.log acid_c*.log acid_i*.log acid_f*.log acid_d*.log acid_s*.log 2>/dev/null || true

# ── Step 1: DB-level ACID tests ──────────────────────────────────────────────
info "Step 1: Running DB-level ACID tests …"
run_step "DB-Level ACID Tests" \
    python3 "$BACKEND_DIR/test_acid_db_level.py"

# ── Step 2: Start Flask server ───────────────────────────────────────────────
info "Step 2: Starting Flask server …"
cd "$BACKEND_DIR"
# kill any existing server on port 5001
fuser -k 5001/tcp 2>/dev/null || true
sleep 1

PYTHONPATH="$MODULE_A_DIR:${PYTHONPATH:-}" python3 main.py \
    > "$BACKEND_DIR/flask_server.log" 2>&1 &
FLASK_PID=$!
echo "  Flask PID: $FLASK_PID"

# wait for server readiness
info "  Waiting for server to be ready …"
READY=0
for i in $(seq 1 30); do
    if curl -sf http://127.0.0.1:5001/api/ping > /dev/null 2>&1; then
        READY=1
        break
    fi
    sleep 1
done

if [[ $READY -eq 0 ]]; then
    error "Flask server did not start within 30s — check flask_server.log"
    cat "$BACKEND_DIR/flask_server.log" | tail -20
    ((FAIL_COUNT++)) || true
else
    success "Flask server is up (PID=$FLASK_PID)"
fi

# ── Step 3: Seed data ────────────────────────────────────────────────────────
info "Step 3: Seeding test data …"
SEED_RESP=$(curl -sf -X POST http://127.0.0.1:5001/api/seed 2>&1) && \
    success "Seed: $SEED_RESP" || error "Seed failed"

# ── Step 4: API-level ACID tests ─────────────────────────────────────────────
info "Step 4: Running API-level ACID tests …"
run_step "API-Level ACID Tests" \
    python3 "$BACKEND_DIR/test_acid_api_level.py"

# ── Step 5: Locust stress test ───────────────────────────────────────────────
info "Step 5: Running Locust stress test (120 s) …"
if command -v locust &>/dev/null || [[ -x "$LOCUST_BIN" ]]; then
    run_step "Locust Stress Test" \
        python3 "$BACKEND_DIR/run_locust_headless.py"
else
    error "Locust not found — install with: pip install locust --break-system-packages"
    ((FAIL_COUNT++)) || true
fi

# ── Step 6: Stop Flask server ────────────────────────────────────────────────
info "Step 6: Stopping Flask server …"
kill "$FLASK_PID" 2>/dev/null || true
wait "$FLASK_PID" 2>/dev/null || true
success "Flask server stopped"

# ── Step 7: Generate final evidence report ───────────────────────────────────
info "Step 7: Generating final evidence report …"
python3 "$BACKEND_DIR/generate_final_report.py"

# ── Final Summary ────────────────────────────────────────────────────────────
echo ""
echo "========================================================================"
echo "  VERIFICATION COMPLETE"
echo "========================================================================"
echo "  Steps Passed:  $PASS_COUNT"
echo "  Steps Failed:  $FAIL_COUNT"
echo ""
echo "  Artifacts:"
for f in acid_db_results.json acid_api_results.json locust_summary.json \
          locust_results_stats.csv final_evidence_report.md \
          traceability_matrix.md all_results.json; do
    fpath="$BACKEND_DIR/$f"
    if [[ -f "$fpath" ]]; then
        echo "    ✓ $f"
    else
        echo "    ✗ $f (not generated)"
    fi
done
echo "========================================================================"

if [[ $FAIL_COUNT -gt 0 ]]; then
    echo -e "${RED}  OVERALL: FAIL — $FAIL_COUNT step(s) failed${NC}"
    exit 1
else
    echo -e "${GREEN}  OVERALL: PASS — all validations succeeded${NC}"
    exit 0
fi
