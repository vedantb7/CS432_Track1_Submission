-- =============================================================================
-- Migration 001: User-Initiated Order Verification
-- FreshWash Laundry Management System
-- Date: 2026-04-18
-- =============================================================================
-- Adds the order_rejection table to store employee rejection remarks
-- when a user-placed order fails verification.
-- The laundry_order.current_status column is VARCHAR(50) with no CHECK constraint,
-- so the two new status values ('Awaiting Verification', 'Rejected') need no
-- column migration — only the application-layer transition map is extended.
-- =============================================================================

-- 1. order_rejection table -------------------------------------------------
CREATE TABLE IF NOT EXISTS freshwash.order_rejection (
    rejection_id  SERIAL       PRIMARY KEY,
    order_id      INT          NOT NULL,
    employee_id   INT          NOT NULL,
    remarks       TEXT         NOT NULL,
    rejected_at   TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_rejection_order
        FOREIGN KEY (order_id)    REFERENCES freshwash.laundry_order (order_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_rejection_employee
        FOREIGN KEY (employee_id) REFERENCES freshwash.employee (employee_id)
        ON DELETE CASCADE
);

COMMENT ON TABLE freshwash.order_rejection IS
    'Stores employee rejection remarks for user-submitted orders pending verification.';

CREATE INDEX IF NOT EXISTS idx_order_rejection_order_id
    ON freshwash.order_rejection (order_id);

-- 2. Audit trigger for order_rejection ------------------------------------
CREATE TRIGGER tr_audit_order_rejection
    AFTER INSERT OR UPDATE OR DELETE ON freshwash.order_rejection
    FOR EACH ROW EXECUTE FUNCTION freshwash.fn_audit_logger();

-- =============================================================================
-- END Migration 001
-- =============================================================================
