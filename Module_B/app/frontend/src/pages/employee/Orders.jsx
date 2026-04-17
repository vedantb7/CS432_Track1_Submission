import React, { useState, useMemo, useEffect } from 'react';
import { useToast } from '../../components/Toast';
import {
  getAssignedOrders,
  getAssignedMembers,
  createOrder,
  updateOrderStatus,
  verifyOrder,
} from '../../utils/employeeApi';
import { Check, X, AlertCircle, Search, Plus, Edit2, Package } from 'lucide-react';
import OrderItemsForm from '../../components/OrderItemsForm';
import '../../styles/admin.css';

// DB lifecycle statuses shown in the manage modal dropdown
// Frontend → DB mapping handled by the backend.
const ORDER_STATUSES = [
  { label: 'Pending', value: 'Pending' },
  { label: 'Picked Up', value: 'Picked Up' },
  { label: 'Washing', value: 'Washing' },
  { label: 'Processing', value: 'Processing' },
  { label: 'Ironing', value: 'Ironing' },
  { label: 'Ready for Delivery', value: 'Ready for Delivery' },
  { label: 'Delivered', value: 'Delivered' },
  { label: 'Cancelled', value: 'Cancelled' },
];

const EmployeeOrders = () => {
  const currentEmployee = useMemo(() => {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    return user.employeeId;
  }, []);

  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [orders, setOrders] = useState([]);
  const [assignedMembers, setAssignedMembers] = useState([]);
  const [loading, setLoading] = useState(true);

  const [showAddOrderModal, setShowAddOrderModal] = useState(false);
  const [newOrderData, setNewOrderData] = useState({
    member_id: '',
    pickup_time: '',
    expected_delivery_time: '',
    items: [],
    total_amount: 0,
  });
  const [addingOrder, setAddingOrder] = useState(false);
  const [manageOrder, setManageOrder] = useState(null);
  const [newStatus, setNewStatus] = useState('');
  const [showManageModal, setShowManageModal] = useState(false);
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [verificationRemarks, setVerificationRemarks] = useState('');
  const [verificationPrice, setVerificationPrice] = useState('');
  const [verificationDelivery, setVerificationDelivery] = useState('');
  const [verifying, setVerifying] = useState(false);
  const [orderDetailLoading, setOrderDetailLoading] = useState(false);

  const addToast = useToast();

  // ── Fetch orders + members ──────────────────────────────────────────────
  const loadData = async () => {
    if (!currentEmployee) return;
    setLoading(true);
    try {
      const [fetchedOrders, fetchedMembers] = await Promise.all([
        getAssignedOrders(currentEmployee),
        getAssignedMembers(currentEmployee),
      ]);
      setOrders(fetchedOrders);
      setAssignedMembers(fetchedMembers);
    } catch (err) {
      addToast(err.message || 'Failed to load orders', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000); // Polling every 15s
    return () => clearInterval(interval);
  }, [currentEmployee]);

  // ── Filter (search uses String() because IDs are numbers) ───────────────
  const filteredOrders = orders.filter((order) => {
    const q = searchTerm.toLowerCase();
    const matchesSearch =
      String(order.order_id).toLowerCase().includes(q) ||
      String(order.member_id).toLowerCase().includes(q) ||
      (order.member_name || '').toLowerCase().includes(q);
    const matchesStatus =
      filterStatus === 'all' || order.order_status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  const getStatusBadgeClass = (status) => {
    const s = status || 'pending';
    return `badge ${s.replace(' ', '_')}`;
  };

  // Counts for filter buttons (use DB status for exact match)
  const countAwaiting = orders.filter((o) => o.db_status === 'Awaiting Verification').length;
  const countPending = orders.filter((o) => o.db_status === 'Pending').length;
  const countProcessing = orders.filter((o) => (o.db_status || '').includes('processing') || ['Picked Up', 'Washing', 'Ironing'].includes(o.db_status)).length;
  const countCompleted = orders.filter((o) => o.db_status === 'Completed' || o.db_status === 'Delivered').length;

  // ── Add Order ────────────────────────────────────────────────────────────
  const handleAddOrder = async () => {
    const { member_id, pickup_time, expected_delivery_time, items, total_amount } = newOrderData;
    if (!member_id || !pickup_time || !expected_delivery_time || !items.length) {
      addToast('Please select member, times and at least one item', 'error');
      return;
    }
    if (new Date(expected_delivery_time) <= new Date(pickup_time)) {
      addToast('Expected delivery time must be after pickup time', 'error');
      return;
    }
    setAddingOrder(true);
    try {
      await createOrder({
        member_id: parseInt(member_id),
        pickup_time,
        expected_delivery_time,
        items,
        employee_id: currentEmployee,
        assigned_role: 'Handler',
      });
      addToast('Order created successfully!', 'success');
      setShowAddOrderModal(false);
      setNewOrderData({ member_id: '', pickup_time: '', expected_delivery_time: '', items: [], total_amount: 0 });
      loadData();
    } catch (err) {
      addToast(err.message || 'Failed to add order', 'error');
    } finally {
      setAddingOrder(false);
    }
  };

  const [detailedOrder, setDetailedOrder] = useState(null);

  const handleManageClick = async (order) => {
    setManageOrder(order);
    setDetailedOrder(null);
    setNewStatus(order.db_status || 'Pending');
    setShowManageModal(true);
    
    // For awaiting verification, fetch the items user entered
    if (order.db_status === 'Awaiting Verification') {
      setOrderDetailLoading(true);
      try {
        const res = await fetch(`${window.location.origin}/api/employee/orders/order/${order.order_id}?employee_id=${currentEmployee}`);
        const data = await res.json();
        setDetailedOrder(data);
        setVerificationPrice(data.total_amount);
        // Default delivery time to +2 days from now if not set
        const defaultDelivery = new Date();
        defaultDelivery.setDate(defaultDelivery.getDate() + 2);
        setVerificationDelivery(defaultDelivery.toISOString().slice(0, 16));
      } catch (err) {
        addToast('Failed to load order details', 'error');
      } finally {
        setOrderDetailLoading(false);
      }
    }
  };

  // ── Update Status ─────────────────────────────────────────────────────────
  const handleUpdateStatus = async () => {
    if (!manageOrder || !newStatus) return;
    setUpdatingStatus(true);
    try {
      // Send the raw DB status — backend validates the transition
      await updateOrderStatus(manageOrder.order_id, newStatus);
      addToast(`Order status updated to "${newStatus}"`, 'success');
      setShowManageModal(false);
      setManageOrder(null);
      setNewStatus('');
      loadData();
    } catch (err) {
      addToast(err.message || 'Failed to update status', 'error');
    } finally {
      setUpdatingStatus(false);
    }
  };

  // ── Verify Order (Approve/Reject) ─────────────────────────────────────────
  const handleVerifyOrder = async (action) => {
    if (!manageOrder) return;
    if (action === 'reject' && !verificationRemarks.trim()) {
      addToast('Please provide rejection remarks', 'error');
      return;
    }
    if (action === 'approve' && (!verificationDelivery || !verificationPrice)) {
      addToast('Please provide delivery time and confirm price', 'error');
      return;
    }
    setVerifying(true);
    try {
      await verifyOrder(
        manageOrder.order_id, 
        action, 
        verificationRemarks, 
        action === 'approve' ? parseFloat(verificationPrice) : null,
        action === 'approve' ? verificationDelivery : null
      );
      addToast(
        `Order ${action === 'approve' ? 'approved' : 'rejected'} successfully`,
        'success'
      );
      setShowManageModal(false);
      setManageOrder(null);
      setVerificationRemarks('');
      setVerificationPrice('');
      setVerificationDelivery('');
      loadData();
    } catch (err) {
      addToast(err.message || 'Failed to verify order', 'error');
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="admin-page">
      <header className="page-header">
        <div>
          <h1>Assigned Orders</h1>
          <p>View and manage your assigned laundry orders</p>
        </div>
        <button
          className="btn-add-order"
          onClick={() => setShowAddOrderModal(true)}
        >
          <Plus size={18} /> Add Order
        </button>
      </header>

      {/* ── Stat boxes ── */}
      <div className="stats-section">
        <div className="stat-box">
          <h3>Total Assigned</h3>
          <p className="stat-value">{orders.length}</p>
          <span className="stat-label">Orders</span>
        </div>
        <div className="stat-box">
          <h3>Verification</h3>
          <p className="stat-value" style={{ color: '#92400e' }}>
            {countAwaiting}
          </p>
          <span className="stat-label">Pending Approval</span>
        </div>
        <div className="stat-box">
          <h3>Pending</h3>
          <p className="stat-value" style={{ color: '#f59e0b' }}>
            {countPending}
          </p>
          <span className="stat-label">Action Needed</span>
        </div>
        <div className="stat-box">
          <h3>In Progress</h3>
          <p className="stat-value" style={{ color: '#3b82f6' }}>
            {countProcessing}
          </p>
          <span className="stat-label">Being Handled</span>
        </div>
      </div>

      {/* ── Search + filter ── */}
      <div className="filters-section">
        <div className="search-box">
          <Search size={18} />
          <input
            type="text"
            placeholder="Search by Order ID, Member ID, or name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="filter-buttons" style={{ flexWrap: 'wrap', gap: '8px' }}>
          {[
            { label: `All (${orders.length})`, value: 'all' },
            { label: `Awaiting (${countAwaiting})`, value: 'awaiting' },
            { label: `Pending (${countPending})`, value: 'pending' },
            { label: `Processing (${countProcessing})`, value: 'processing' },
            { label: `Delivered (${countCompleted})`, value: 'completed' },
          ].map(({ label, value }) => (
            <button
              key={value}
              className={`filter-btn ${filterStatus === value ? 'active' : ''}`}
              onClick={() => setFilterStatus(value)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Orders table ── */}
      <div className="table-card">
        <div className="table-container">
          {loading ? (
            <p style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
              Loading orders…
            </p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Order ID</th>
                  <th>Member</th>
                  <th>Order Date</th>
                  <th>Pickup Time</th>
                  <th>Delivery Time</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Role</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredOrders.length > 0 ? (
                  filteredOrders.map((order) => (
                    <tr key={order.order_id}>
                      <td className="order-id">{order.order_id}</td>
                      <td>
                        <span title={`ID: ${order.member_id}`}>
                          {order.member_name || order.member_id}
                        </span>
                      </td>
                      <td>{order.order_date ? order.order_date.split('T')[0] : '—'}</td>
                      <td>{order.pickup_time ? order.pickup_time.split('T')[0] : '—'}</td>
                      <td>
                        {order.expected_delivery_time
                          ? order.expected_delivery_time.split('T')[0]
                          : '—'}
                      </td>
                      <td className="amount">₹{order.total_amount.toFixed(2)}</td>
                      <td>
                        {/* Badge class uses frontend bucket; show DB status as tooltip */}
                        <span
                          className={getStatusBadgeClass(order.db_status)}
                        >
                          {order.db_status}
                        </span>
                      </td>
                      <td>{order.assigned_role}</td>
                      <td>
                        <button
                          className="action-btn edit-btn icon-only"
                          onClick={() => handleManageClick(order)}
                          title="Update status"
                        >
                          <Edit2 size={16} />
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="9" className="no-data">
                      {orders.length === 0
                        ? 'No orders assigned to you'
                        : 'No orders match your search'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* ── Manage Order Modal ── */}
      {showManageModal && manageOrder && (
        <div className="modal-overlay" onClick={() => setShowManageModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Update Order Status</h2>
              <button className="close-modal" onClick={() => setShowManageModal(false)}>×</button>
            </div>
            <div className="modal-body">
              <div className="detail-grid">
                <div className="detail-item">
                  <label>Order ID</label>
                  <p>{manageOrder.order_id}</p>
                </div>
                <div className="detail-item">
                  <label>Member</label>
                  <p>{manageOrder.member_name || manageOrder.member_id}</p>
                </div>
                <div className="detail-item">
                  <label>Amount</label>
                  <p className="amount-highlight">₹{manageOrder.total_amount.toFixed(2)}</p>
                </div>
                <div className="detail-item">
                  <label>Current Status</label>
                  <p>
                    <span
                      className={getStatusBadgeClass(manageOrder.db_status)}
                    >
                      {manageOrder.db_status}
                    </span>
                  </p>
                </div>

                {manageOrder.db_status === 'Awaiting Verification' ? (
                  <div className="detail-item full-width verification-section">
                    {orderDetailLoading ? (
                      <p>Loading user items...</p>
                    ) : detailedOrder ? (
                      <>
                        <div className="user-items-review" style={{ background: '#f9fafb', padding: '12px', borderRadius: '8px', marginBottom: '1.5rem' }}>
                          <h4 style={{ margin: '0 0 8px 0', fontSize: '0.9rem' }}>User Selected Items</h4>
                          <div style={{ display: 'grid', gap: '8px' }}>
                            {detailedOrder.items?.map((it, idx) => (
                              <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                                <span>{it.quantity}x {it.type_name} ({it.service_name})</span>
                                <span style={{ fontWeight: 600 }}>₹{(it.quantity * it.applied_price).toFixed(2)}</span>
                              </div>
                            ))}
                          </div>
                          <div style={{ borderTop: '1px solid #e5e7eb', marginTop: '8px', paddingTop: '8px', textAlign: 'right', fontWeight: 700 }}>
                            Total: ₹{detailedOrder.total_amount.toFixed(2)}
                          </div>
                        </div>

                        <div className="verification-inputs" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                          <div className="form-group">
                            <label style={{ fontSize: '0.85rem', fontWeight: 600 }}>Confirmed Total Price (₹)</label>
                            <input 
                              type="number" 
                              className="form-select" 
                              value={verificationPrice} 
                              onChange={(e) => setVerificationPrice(e.target.value)} 
                            />
                          </div>
                          <div className="form-group">
                            <label style={{ fontSize: '0.85rem', fontWeight: 600 }}>Expected Delivery</label>
                            <input 
                              type="datetime-local" 
                              className="form-select" 
                              value={verificationDelivery} 
                              onChange={(e) => setVerificationDelivery(e.target.value)} 
                            />
                          </div>
                        </div>

                        <div className="rejection-box" style={{ marginTop: '1rem' }}>
                          <label htmlFor="rejection-remarks">Rejection Remarks (Required for rejection)</label>
                          <textarea
                            id="rejection-remarks"
                            className="form-textarea"
                            placeholder="Reason for rejection..."
                            value={verificationRemarks}
                            onChange={(e) => setVerificationRemarks(e.target.value)}
                            style={{ width: '100%', minHeight: '60px', marginTop: '4px', borderRadius: '8px', padding: '10px', border: '1px solid #e5e7eb' }}
                          />
                        </div>

                        <div className="verification-actions" style={{ display: 'flex', gap: '12px', marginTop: '1.5rem' }}>
                          <button
                            className="btn btn-primary"
                            onClick={() => handleVerifyOrder('approve')}
                            disabled={verifying}
                            style={{ flex: 1, background: '#10b981' }}
                          >
                            <Check size={18} style={{ marginRight: '8px' }} /> Approve
                          </button>
                          <button
                            className="btn"
                            onClick={() => handleVerifyOrder('reject')}
                            disabled={verifying}
                            style={{ flex: 1, background: '#ef4444', color: 'white' }}
                          >
                            <X size={18} style={{ marginRight: '8px' }} /> Reject
                          </button>
                        </div>
                      </>
                    ) : (
                      <p>Error loading items.</p>
                    )}
                  </div>
                ) : (
                  <div className="detail-item full-width">
                    <label htmlFor="status-select">Update Lifecycle Status</label>
                    <select
                      id="status-select"
                      className="form-select"
                      value={newStatus}
                      onChange={(e) => setNewStatus(e.target.value)}
                    >
                      <option value="">— Select New Status —</option>
                      {ORDER_STATUSES.map(({ label, value }) => (
                        <option key={value} value={value}>{label}</option>
                      ))}
                    </select>
                    <div className="modal-footer" style={{ border: 'none', padding: 0 }}>
                      <button
                        className="btn btn-primary"
                        onClick={handleUpdateStatus}
                        disabled={!newStatus || updatingStatus}
                        style={{ width: '100%' }}
                      >
                        {updatingStatus ? 'Updating…' : 'Update Status'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Add Order Modal ── */}
      {showAddOrderModal && (
        <div className="modal-overlay" onClick={() => setShowAddOrderModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Add New Order</h2>
              <button className="close-modal" onClick={() => setShowAddOrderModal(false)}>×</button>
            </div>
            <div className="modal-body">
              <div className="detail-grid">
                {/* Member select */}
                <div className="detail-item full-width">
                  <label htmlFor="member-select">Member *</label>
                  <select
                    id="member-select"
                    className="form-select"
                    value={newOrderData.member_id}
                    onChange={(e) =>
                      setNewOrderData({ ...newOrderData, member_id: e.target.value })
                    }
                  >
                    <option value="">— Select Member —</option>
                    {assignedMembers.map((m) => (
                      <option key={m.member_id} value={m.member_id}>
                        {m.member_name} (ID: {m.member_id})
                      </option>
                    ))}
                  </select>
                  {assignedMembers.length === 0 && (
                    <p style={{ color: '#dc2626', fontSize: '0.85rem', marginTop: 4 }}>
                      No members found for your assigned orders
                    </p>
                  )}
                </div>

                {/* Pickup time */}
                <div className="detail-item">
                  <label htmlFor="pickup-time">Pickup Time *</label>
                  <input
                    id="pickup-time"
                    type="datetime-local"
                    className="form-select"
                    value={newOrderData.pickup_time}
                    onChange={(e) =>
                      setNewOrderData({ ...newOrderData, pickup_time: e.target.value })
                    }
                  />
                </div>

                {/* Expected delivery (required by DB CHECK constraint) */}
                <div className="detail-item">
                  <label htmlFor="delivery-time">Expected Delivery *</label>
                  <input
                    id="delivery-time"
                    type="datetime-local"
                    className="form-select"
                    value={newOrderData.expected_delivery_time}
                    onChange={(e) =>
                      setNewOrderData({ ...newOrderData, expected_delivery_time: e.target.value })
                    }
                  />
                </div>

                {/* Order Items */}
                <div className="detail-item full-width">
                  <OrderItemsForm 
                    onChange={(items, total) => setNewOrderData({ ...newOrderData, items, total_amount: total })} 
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button
                  className="btn btn-secondary"
                  onClick={() => setShowAddOrderModal(false)}
                >
                  Cancel
                </button>
                <button
                  className="btn btn-primary"
                  onClick={handleAddOrder}
                  disabled={addingOrder}
                >
                  {addingOrder ? 'Creating…' : 'Create Order'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .btn-add-order {
          display: flex; align-items: center; gap: 0.5rem;
          padding: 0.75rem 1.5rem;
          background: linear-gradient(135deg, #3b82f6, #8b5cf6);
          color: white; border: none; border-radius: 8px;
          font-weight: 600; cursor: pointer; transition: all 0.2s;
          box-shadow: 0 4px 12px rgba(59,130,246,0.3);
        }
        .btn-add-order:hover { transform: translateY(-2px); box-shadow: 0 8px 16px rgba(59,130,246,0.4); }
        .form-select {
          width: 100%; padding: 10px; border: 1px solid #e5e7eb;
          border-radius: 8px; font-size: 14px; background-color: #fff;
          cursor: pointer; transition: border-color 0.2s;
        }
        .form-select:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.1); }
        .detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
        .detail-item { display: flex; flex-direction: column; gap: 6px; }
        .detail-item label { font-size: 0.85rem; font-weight: 600; color: #374151; }
        .detail-item.full-width { grid-column: 1 / -1; }
        .modal-footer { display: flex; gap: 12px; justify-content: flex-end; margin-top: 24px;
          padding-top: 16px; border-top: 1px solid #e5e7eb; }
        .btn { padding: 10px 20px; border: none; border-radius: 6px; font-size: 14px;
          font-weight: 500; cursor: pointer; transition: all 0.2s; }
        .btn-primary { background: #3b82f6; color: white; }
        .btn-primary:hover:not(:disabled) { background: #2563eb; }
        .btn-primary:disabled { background: #d1d5db; cursor: not-allowed; }
        .btn-secondary { background: #e5e7eb; color: #374151; }
        .btn-secondary:hover { background: #d1d5db; }
        .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5);
          display: flex; align-items: center; justify-content: center; z-index: 1000; }
        .modal-content { background: white; border-radius: 12px; max-width: 560px; width: 90%;
          box-shadow: 0 20px 40px rgba(0,0,0,0.15); overflow: hidden; }
        .modal-header { padding: 20px; border-bottom: 1px solid #e5e7eb;
          display: flex; justify-content: space-between; align-items: center; }
        .modal-header h2 { margin: 0; font-size: 1.25rem; color: #111827; }
        .close-modal { background: none; border: none; font-size: 24px; cursor: pointer; color: #9ca3af; }
        .close-modal:hover { color: #111827; }
        .modal-body { padding: 20px; }
        .action-buttons { display: flex; gap: 8px; }
        .edit-btn { background: #fef08a; color: #92400e; border: none; border-radius: 6px;
          cursor: pointer; transition: all 0.2s; display: flex; align-items: center;
          justify-content: center; }
        .edit-btn:hover { background: #fde047; }
        .edit-btn.icon-only { padding: 8px; }
        .amount-highlight { color: #059669; font-weight: 700; }
        .badge.awaiting_verification { background: #fef3c7; color: #92400e; }
        .badge.rejected { background: #fee2e2; color: #991b1b; }
        .badge.cancelled { background: #fee2e2; color: #dc2626; }
      `}</style>
    </div>
  );
};

export default EmployeeOrders;
