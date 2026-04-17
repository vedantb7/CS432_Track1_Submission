// utils/userApi.js
// ─────────────────────────────────────────────────────────────────────────────
// All API helpers for the User Dashboard.
// ─────────────────────────────────────────────────────────────────────────────

const BASE = '/api/user';

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

// ── Orders ─────────────────────────────────────────────────────────────────

export const getUserOrders = (memberId) =>
  apiFetch(`/orders/${memberId}`);

export const createUserOrder = (orderData) =>
  apiFetch('/orders', {
    method: 'POST',
    body: JSON.stringify(orderData),
  });

export const resubmitOrder = (orderId, orderData) =>
  apiFetch(`/orders/${orderId}`, {
    method: 'PATCH',
    body: JSON.stringify(orderData),
  });
