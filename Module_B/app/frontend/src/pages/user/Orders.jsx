import React, { useState, useMemo, useEffect } from 'react';
import { Search, Eye } from 'lucide-react';
import '../../styles/admin.css';
import { getMemberId } from '../../utils/auth';

const UserOrders = () => {
  const currentMember = getMemberId();

  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!currentMember) return;

    const fetchOrders = async () => {
      try {
        setLoading(true);
        const response = await fetch(`http://127.0.0.1:5001/api/user/orders/${currentMember}`);
        const data = await response.json();
        if (response.ok) {
          setOrders(data);
        } else {
          setError(data.error || 'Failed to fetch orders');
        }
      } catch (err) {
        console.error('Error fetching orders:', err);
        setError('Connection error. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchOrders();
  }, [currentMember]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [selectedOrder, setSelectedOrder] = useState(null);

  const filteredOrders = useMemo(() => {
    return orders.filter((order) => {
      const matchesSearch = String(order.order_id).toLowerCase().includes(searchTerm.toLowerCase());
      const matchesStatus = filterStatus === 'all' || order.order_status === filterStatus;
      return matchesSearch && matchesStatus;
    });
  }, [orders, searchTerm, filterStatus]);

  const getStatusBadgeClass = (status) => {
    return `badge ${status || 'pending'}`;
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
        <h1>My Orders</h1>
        <p>View and track your laundry orders</p>
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
            className={`filter-btn ${filterStatus === 'pending' ? 'active' : ''}`}
            onClick={() => setFilterStatus('pending')}
          >
            Pending ({orders.filter((o) => o.order_status === 'pending').length})
          </button>
          <button
            className={`filter-btn ${filterStatus === 'processing' ? 'active' : ''}`}
            onClick={() => setFilterStatus('processing')}
          >
            Processing ({orders.filter((o) => (o.order_status || '').includes('processing')).length})
          </button>
          <button
            className={`filter-btn ${filterStatus === 'completed' ? 'active' : ''}`}
            onClick={() => setFilterStatus('completed')}
          >
            Completed ({orders.filter((o) => o.order_status === 'completed').length})
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
                    <td>{order.order_date}</td>
                    <td>{order.pickup_time}</td>
                    <td className="amount">₹{(order.total_amount || 0).toFixed(2)}</td>
                    <td>
                      <span className={getStatusBadgeClass(order.order_status)}>
                        {(order.order_status || 'Pending').charAt(0).toUpperCase() + (order.order_status || 'Pending').slice(1)}
                      </span>
                    </td>
                    <td>
                      <span className="employee-badge">
                        {order.handler_name || 'Unassigned'}
                      </span>
                    </td>
                    <td>
                      <button
                        className="action-btn view-btn"
                        onClick={() => setSelectedOrder(order)}
                        title="View Details"
                      >
                        <Eye size={16} />
                      </button>
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
              <div className="detail-grid">
                <div className="detail-item">
                  <label>Order ID</label>
                  <p>{selectedOrder.order_id}</p>
                </div>
                <div className="detail-item">
                  <label>Order Date</label>
                  <p>{selectedOrder.order_date}</p>
                </div>
                <div className="detail-item">
                  <label>Pickup Time</label>
                  <p>{selectedOrder.pickup_time}</p>
                </div>
                <div className="detail-item">
                  <label>Total Amount</label>
                  <p className="amount-highlight">₹{(selectedOrder.total_amount || 0).toFixed(2)}</p>
                </div>
                <div className="detail-item">
                  <label>Status</label>
                  <p>
                    <span
                      className={getStatusBadgeClass(selectedOrder.order_status)}
                      style={{ display: 'inline-block' }}
                    >
                      {(selectedOrder.order_status || 'Pending').charAt(0).toUpperCase() + (selectedOrder.order_status || 'Pending').slice(1)}
                    </span>
                  </p>
                </div>
                <div className="detail-item">
                  <label>Handler</label>
                  <p>
                    <span className="employee-badge">
                      {selectedOrder.handler_name || 'Unassigned'}
                    </span>
                  </p>
                </div>
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

        .employee-badge {
          display: inline-block;
          padding: 4px 12px;
          background: #dbeafe;
          color: #1e40af;
          border-radius: 12px;
          font-size: 0.85rem;
          font-weight: 500;
        }
      `}</style>
    </div>
  );
};

export default UserOrders;
