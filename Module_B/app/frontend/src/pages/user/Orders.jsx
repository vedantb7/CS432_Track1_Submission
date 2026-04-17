import React, { useState, useMemo, useEffect } from 'react';
import { Search, Eye, Plus, AlertCircle, Edit2 } from 'lucide-react';
import '../../styles/admin.css';
import { getMemberId } from '../../utils/auth';
import { getUserOrders, createUserOrder, resubmitOrder } from '../../utils/userApi';
import OrderItemsForm from '../../components/OrderItemsForm';

const UserOrders = () => {
  const currentMember = getMemberId();

  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [submitLoading, setSubmitLoading] = useState(false);

  // Modal States
  const [isPlaceModalOpen, setIsPlaceModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [newOrderData, setNewOrderData] = useState({
    pickup_time: '',
    items: [],
    total_amount: 0
  });
  const [editOrderData, setEditOrderData] = useState(null);

  const fetchOrders = async (showLoading = true) => {
    if (!currentMember) return;
    try {
      if (showLoading) setLoading(true);
      const data = await getUserOrders(currentMember);
      setOrders(data);
      setError(null);
    } catch (err) {
      console.error('Error fetching orders:', err);
      if (showLoading) setError(err.message || 'Connection error. Please try again later.');
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders(true);
    const interval = setInterval(() => fetchOrders(false), 10000); // Polling every 10s
    return () => clearInterval(interval);
  }, [currentMember]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [selectedOrder, setSelectedOrder] = useState(null);

  const handlePlaceOrder = async (e) => {
    e.preventDefault();
    if (!currentMember) return;
    try {
      setSubmitLoading(true);
      await createUserOrder({
        ...newOrderData,
        member_id: currentMember
      });
      setIsPlaceModalOpen(false);
      setNewOrderData({ pickup_time: '', items: [], total_amount: 0 });
      fetchOrders(false);
    } catch (err) {
      alert(err.message || 'Failed to place order');
    } finally {
      setSubmitLoading(false);
    }
  };

  const handleResubmitOrder = async (e) => {
    e.preventDefault();
    if (!editOrderData) return;
    try {
      setSubmitLoading(true);
      await resubmitOrder(editOrderData.order_id, {
        ...editOrderData,
        member_id: currentMember
      });
      setIsEditModalOpen(false);
      setEditOrderData(null);
      fetchOrders(false);
    } catch (err) {
      alert(err.message || 'Failed to resubmit order');
    } finally {
      setSubmitLoading(false);
    }
  };

  const filteredOrders = useMemo(() => {
    return orders.filter((order) => {
      const matchesSearch = String(order.order_id).toLowerCase().includes(searchTerm.toLowerCase());
      const matchesStatus = filterStatus === 'all' || order.order_status === filterStatus;
      return matchesSearch && matchesStatus;
    });
  }, [orders, searchTerm, filterStatus]);

  const getStatusBadgeClass = (status) => {
    const s = status || 'pending';
    return `badge ${s.replace(' ', '_')}`;
  };

  if (loading) {
    return (
      <div className="admin-page">
        <div className="loading-container">
          <div className="loader"></div>
          <p>Loading your orders...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="admin-page">
        <div className="error-container">
          <p className="error-message">Error: {error}</p>
          <button onClick={() => window.location.reload()} className="action-btn">Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-page">
      <header className="page-header">
        <div className="header-content">
          <h1>My Orders</h1>
          <p>View and track your laundry orders</p>
        </div>
        <button className="btn-primary" onClick={() => setIsPlaceModalOpen(true)}>
          <Plus size={18} />
          Place New Order
        </button>
      </header>

      <div className="stats-section">
        <div className="stat-box">
          <h3>Total Orders</h3>
          <p className="stat-value">{orders.length}</p>
        </div>
        <div className="stat-box">
          <h3>Pending</h3>
          <p className="stat-value" style={{ color: '#f59e0b' }}>
            {orders.filter((o) => o.order_status === 'pending').length}
          </p>
        </div>
        <div className="stat-box">
          <h3>Processing</h3>
          <p className="stat-value" style={{ color: '#3b82f6' }}>
            {orders.filter((o) => (o.order_status || '').includes('processing') || o.order_status === 'washing' || o.order_status === 'ironing').length}
          </p>
        </div>
        <div className="stat-box">
          <h3>Completed</h3>
          <p className="stat-value" style={{ color: '#10b981' }}>
            {orders.filter((o) => o.order_status === 'completed' || o.order_status === 'delivered').length}
          </p>
        </div>
      </div>

      <div className="filters-section">
        <div className="search-box">
          <Search size={18} />
          <input
            type="text"
            placeholder="Search by Order ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="filter-buttons">
          <button
            className={`filter-btn ${filterStatus === 'all' ? 'active' : ''}`}
            onClick={() => setFilterStatus('all')}
          >
            All ({orders.length})
          </button>
          <button
            className={`filter-btn ${filterStatus === 'awaiting' ? 'active' : ''}`}
            onClick={() => setFilterStatus('awaiting')}
          >
            Awaiting ({orders.filter((o) => o.db_status === 'Awaiting Verification').length})
          </button>
          <button
            className={`filter-btn ${filterStatus === 'rejected' ? 'active' : ''}`}
            onClick={() => setFilterStatus('rejected')}
          >
            Rejected ({orders.filter((o) => o.db_status === 'Rejected').length})
          </button>
          <button
            className={`filter-btn ${filterStatus === 'pending' ? 'active' : ''}`}
            onClick={() => setFilterStatus('pending')}
          >
            Pending ({orders.filter((o) => o.db_status === 'Pending').length})
          </button>
          <button
            className={`filter-btn ${filterStatus === 'processing' ? 'active' : ''}`}
            onClick={() => setFilterStatus('processing')}
          >
            Processing ({orders.filter((o) => (o.db_status || '').includes('processing') || ['Picked Up', 'Washing', 'Ironing'].includes(o.db_status)).length})
          </button>
          <button
            className={`filter-btn ${filterStatus === 'completed' ? 'active' : ''}`}
            onClick={() => setFilterStatus('completed')}
          >
            Completed ({orders.filter((o) => o.db_status === 'Completed' || o.db_status === 'Delivered').length})
          </button>
        </div>
      </div>

      <div className="table-card">
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Order ID</th>
                <th>Order Date</th>
                <th>Pickup Time</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Handler</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredOrders.length > 0 ? (
                filteredOrders.map((order) => (
                  <tr key={order.order_id}>
                    <td className="order-id">{order.order_id}</td>
                    <td>{new Date(order.order_date).toLocaleDateString()}</td>
                    <td>{new Date(order.pickup_time).toLocaleString()}</td>
                    <td className="amount">₹{(order.total_amount || 0).toFixed(2)}</td>
                    <td>
                      <span className={getStatusBadgeClass(order.db_status)}>
                        {order.db_status}
                      </span>
                    </td>
                    <td>
                      <span className="employee-badge">
                        {order.handler_name}
                      </span>
                    </td>
                    <td>
                      <div className="action-group" style={{ display: 'flex', gap: '8px' }}>
                        <button
                          className="action-btn view-btn"
                          onClick={() => setSelectedOrder(order)}
                          title="View Details"
                        >
                          <Eye size={16} />
                        </button>
                        {order.db_status === 'Rejected' && (
                          <button
                            className="action-btn edit-btn"
                            onClick={() => {
                              setEditOrderData(order);
                              setIsEditModalOpen(true);
                            }}
                            title="Edit & Resubmit"
                            style={{ color: '#ef4444' }}
                          >
                            <Edit2 size={16} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="7" className="no-data">
                    {searchTerm || filterStatus !== 'all' ? 'No orders match your criteria' : 'You haven\'t placed any orders yet'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Place Order Modal */}
      {isPlaceModalOpen && (
        <div className="modal-overlay" onClick={() => setIsPlaceModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Place New Order</h2>
              <button className="close-modal" onClick={() => setIsPlaceModalOpen(false)}>×</button>
            </div>
            <form onSubmit={handlePlaceOrder} className="modal-body">
              <div className="form-group">
                <label>Pickup Time</label>
                <input
                  type="datetime-local"
                  required
                  value={newOrderData.pickup_time}
                  onChange={(e) => setNewOrderData({...newOrderData, pickup_time: e.target.value})}
                />
              </div>

              <div className="form-group">
                <OrderItemsForm 
                  onChange={(items, total) => setNewOrderData({ ...newOrderData, items, total_amount: total })} 
                />
              </div>
              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setIsPlaceModalOpen(false)}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={submitLoading}>
                  {submitLoading ? 'Placing...' : 'Place Order'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit/Resubmit Modal */}
      {isEditModalOpen && editOrderData && (
        <div className="modal-overlay" onClick={() => setIsEditModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Resubmit Order</h2>
              <button className="close-modal" onClick={() => setIsEditModalOpen(false)}>×</button>
            </div>
            <form onSubmit={handleResubmitOrder} className="modal-body">
              <div className="rejection-card">
                <div className="rejection-header">
                  <AlertCircle size={18} />
                  <span>Rejection Remarks</span>
                </div>
                <p className="rejection-text">{editOrderData.rejection_remarks}</p>
              </div>

              <div className="form-group" style={{ marginTop: '1rem' }}>
                <label>Pickup Time</label>
                <input
                  type="datetime-local"
                  required
                  value={editOrderData.pickup_time.slice(0, 16)}
                  onChange={(e) => setEditOrderData({...editOrderData, pickup_time: e.target.value})}
                />
              </div>
              <p style={{ fontSize: '0.85rem', color: '#6b7280', margin: '0 0 1rem 0' }}>
                Note: Delivery date and final pricing will be set by the employee after verification.
              </p>
              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setIsEditModalOpen(false)}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={submitLoading}>
                  {submitLoading ? 'Resubmitting...' : 'Update & Resubmit'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Order Details Modal */}
      {selectedOrder && (
        <div className="modal-overlay" onClick={() => setSelectedOrder(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Order Details</h2>
              <button className="close-modal" onClick={() => setSelectedOrder(null)}>
                ×
              </button>
            </div>
            <div className="modal-body">
              {selectedOrder.db_status === 'Rejected' && (
                <div className="rejection-card" style={{ marginBottom: '1.5rem' }}>
                  <div className="rejection-header">
                    <AlertCircle size={18} />
                    <span>Rejection Remarks</span>
                  </div>
                  <p className="rejection-text">{selectedOrder.rejection_remarks}</p>
                </div>
              )}
              <div className="detail-grid">
                <div className="detail-item">
                  <label>Order ID</label>
                  <p>{selectedOrder.order_id}</p>
                </div>
                <div className="detail-item">
                  <label>Order Date</label>
                  <p>{new Date(selectedOrder.order_date).toLocaleString()}</p>
                </div>
                <div className="detail-item">
                  <label>Pickup Time</label>
                  <p>{new Date(selectedOrder.pickup_time).toLocaleString()}</p>
                </div>
                <div className="detail-item">
                  <label>Exp. Delivery</label>
                  <p>{selectedOrder.expected_delivery_time ? new Date(selectedOrder.expected_delivery_time).toLocaleString() : '—'}</p>
                </div>
                <div className="detail-item">
                  <label>Total Amount</label>
                  <p className="amount-highlight">₹{(selectedOrder.total_amount || 0).toFixed(2)}</p>
                </div>
                <div className="detail-item">
                  <label>Status</label>
                  <p>
                    <span
                      className={getStatusBadgeClass(selectedOrder.db_status)}
                      style={{ display: 'inline-block' }}
                    >
                      {selectedOrder.db_status}
                    </span>
                  </p>
                </div>
                <div className="detail-item">
                  <label>Handler</label>
                  <p>
                    <span className="employee-badge">
                      {selectedOrder.handler_name}
                    </span>
                  </p>
                </div>
              </div>

              {/* Added: Specific Items display */}
              <div className="order-items-review" style={{ marginTop: '1.5rem', background: '#f9fafb', padding: '12px', borderRadius: '8px' }}>
                <h4 style={{ margin: '0 0 8px 0', fontSize: '0.9rem' }}>Specific Items</h4>
                {selectedOrder.items && selectedOrder.items.length > 0 ? (
                  <div style={{ display: 'grid', gap: '8px' }}>
                    {selectedOrder.items.map((it, idx) => (
                      <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                        <span>{it.quantity}x {it.type_name} ({it.service_name})</span>
                        <span style={{ fontWeight: 600 }}>₹{(it.quantity * it.applied_price).toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p style={{ fontSize: '0.85rem', color: '#6b7280', fontStyle: 'italic' }}>Item details not available for this legacy order.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .loading-container, .error-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 400px;
          text-align: center;
        }

        .loader {
          width: 40px;
          height: 40px;
          border: 4px solid #f3f3f3;
          border-top: 4px solid var(--primary);
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin-bottom: 1rem;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        .error-message {
          color: #ef4444;
          font-weight: 600;
          margin-bottom: 1rem;
        }

        .badge.awaiting_verification {
          background: #fef3c7;
          color: #92400e;
        }

        .badge.rejected {
          background: #fee2e2;
          color: #991b1b;
        }

        .rejection-card {
          background: #fef2f2;
          border: 1px solid #fee2e2;
          border-radius: 8px;
          padding: 1rem;
        }

        .rejection-header {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          color: #991b1b;
          font-weight: 600;
          margin-bottom: 0.5rem;
        }

        .rejection-text {
          color: #7f1d1d;
          font-size: 0.9rem;
          margin: 0;
        }

        .form-group {
          margin-bottom: 1.25rem;
        }

        .form-group label {
          display: block;
          margin-bottom: 0.5rem;
          font-weight: 500;
        }

        .form-group input {
          width: 100%;
          padding: 0.625rem;
          border: 1px solid #e5e7eb;
          border-radius: 6px;
        }

        .modal-footer {
          display: flex;
          justify-content: flex-end;
          gap: 1rem;
          margin-top: 1.5rem;
        }

        .employee-badge {
          display: inline-block;
          padding: 4px 12px;
          background: #f3f4f6;
          color: #374151;
          border-radius: 12px;
          font-size: 0.85rem;
          font-weight: 500;
        }
      `}</style>
    </div>
  );
};

export default UserOrders;
