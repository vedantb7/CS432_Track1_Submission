// utils/employeeApi.js
// ─────────────────────────────────────────────────────────────────────────────
// All API helpers for the Employee Dashboard.
// Schema-aligned: uses order_assignment (not assigned_employee_id),
// and payment_status table (not payment_date nullability).
// ─────────────────────────────────────────────────────────────────────────────

const BASE = '/api/employee';

/** Generic fetch wrapper — throws on non-OK responses. */
async function apiFetch(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

// ── Dashboard (Stats) ──────────────────────────────────────────────────────

export const getEmployeeStats = (employeeId) =>
  apiFetch(`/dashboard/stats/${employeeId}`);

// ── Orders ─────────────────────────────────────────────────────────────────

export const getAssignedOrders = (employeeId) =>
  apiFetch(`/orders/${employeeId}`);

export const createOrder = (orderData) =>
  apiFetch('/orders', {
    method: 'POST',
    body: JSON.stringify(orderData),
  });

export const updateOrderStatus = (orderId, orderStatus) =>
  apiFetch(`/orders/${orderId}/status`, {
    method: 'PUT',
    body: JSON.stringify({
      order_status: orderStatus,
      employee_id: JSON.parse(localStorage.getItem('user') || '{}').employeeId,
    }),
  });

export const verifyOrder = (orderId, action, remarks = '', final_price = null, expected_delivery_time = null) =>
  apiFetch(`/orders/${orderId}/verify`, {
    method: 'PUT',
    body: JSON.stringify({
      employee_id: JSON.parse(localStorage.getItem('user') || '{}').employeeId,
      action,
      remarks,
      final_price,
      expected_delivery_time
    }),
  });

// ── Payments ───────────────────────────────────────────────────────────────

export const getAssignedPayments = (employeeId) =>
  apiFetch(`/payments/${employeeId}`);

export const updatePaymentStatus = (paymentId, paymentStatus) =>
  apiFetch(`/payments/${paymentId}`, {
    method: 'PUT',
    body: JSON.stringify({ payment_status: paymentStatus }),
  });

// ── Members ────────────────────────────────────────────────────────────────

export const getAssignedMembers = (employeeId) =>
  apiFetch(`/members/${employeeId}`);

// ── Lost Items ─────────────────────────────────────────────────────────────

export const getAssignedLostItems = (employeeId) =>
  apiFetch(`/lost-items/${employeeId}`);

// ── Feedbacks ──────────────────────────────────────────────────────────────

export const getAssignedFeedbacks = (employeeId) =>
  apiFetch(`/feedbacks/${employeeId}`);
