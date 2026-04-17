# employee/utils.py
import datetime

# ── Valid DB statuses and the forward-only transition map ─────────────────────
DB_STATUSES = (
    'Awaiting Verification', 'Rejected',
    'Pending', 'Picked Up', 'Washing', 'Processing',
    'Ironing', 'Ready for Delivery', 'Delivered', 'Cancelled'
)

STATUS_TRANSITIONS = {
    'Awaiting Verification': ['Pending', 'Rejected'],
    'Rejected':              ['Awaiting Verification'],
    'Pending':              ['Picked Up',           'Cancelled'],
    'Picked Up':            ['Washing',             'Cancelled'],
    'Washing':              ['Processing',          'Cancelled'],
    'Processing':           ['Ironing',             'Ready for Delivery', 'Cancelled'],
    'Ironing':              ['Ready for Delivery',  'Cancelled'],
    'Ready for Delivery':   ['Delivered'],
    'Delivered':            [],      # terminal
    'Cancelled':            [],      # terminal
}

# Frontend-to-DB status mapping
FRONTEND_TO_DB = {
    'awaiting':   'Awaiting Verification',
    'rejected':   'Rejected',
    'pending':    'Pending',
    'processing': 'Processing',
    'completed':  'Delivered',   # "Completed" in UI maps to "Delivered" in DB
    'cancelled':  'Cancelled',
}

# DB-to-frontend mapping for display
DB_TO_FRONTEND = {
    'Awaiting Verification': 'awaiting',
    'Rejected':              'rejected',
    'Pending':              'pending',
    'Picked Up':            'processing',
    'Washing':              'processing',
    'Processing':           'processing',
    'Ironing':              'processing',
    'Ready for Delivery':   'processing',
    'Delivered':            'completed',
    'Cancelled':            'cancelled',
}

def _safe_float(value):
    return float(value) if value is not None else 0.0

def _isoformat(value):
    if value is None:
        return None
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    return str(value)

def _frontend_status(db_status):
    """Return lowercase frontend status for a DB status value."""
    return DB_TO_FRONTEND.get(db_status, db_status.lower())
