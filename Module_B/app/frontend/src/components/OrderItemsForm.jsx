import React, { useState, useEffect, useMemo } from 'react';
import { Plus, Trash2 } from 'lucide-react';

const OrderItemsForm = ({ onChange }) => {
  const [options, setOptions] = useState({ clothing_types: [], services: [], pricing: [] });
  const [items, setItems] = useState([{ type_id: '', service_id: '', quantity: 1 }]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchOptions = async () => {
      try {
        const res = await fetch('/api/user/options/services');
        const data = await res.json();
        setOptions(data);
      } catch (err) {
        console.error('Failed to fetch service options:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchOptions();
  }, []);

  const calculateTotal = (currentItems) => {
    return currentItems.reduce((acc, item) => {
      const priceRule = (options.pricing || []).find(
        (p) => Number(p.type_id) === Number(item.type_id) && Number(p.service_id) === Number(item.service_id)
      );
      return acc + (priceRule ? priceRule.price * item.quantity : 0);
    }, 0);
  };

  useEffect(() => {
    const total = calculateTotal(items);
    onChange(items, total);
  }, [items, options.pricing]);

  const addItem = () => {
    setItems([...items, { type_id: '', service_id: '', quantity: 1 }]);
  };

  const removeItem = (index) => {
    if (items.length > 1) {
      setItems(items.filter((_, i) => i !== index));
    }
  };

  const updateItem = (index, field, value) => {
    const newItems = [...items];
    newItems[index] = { ...newItems[index], [field]: value };
    setItems(newItems);
  };

  if (loading) return <p>Loading services...</p>;

  return (
    <div className="order-items-form">
      <div className="items-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ margin: 0, fontSize: '1rem' }}>Order Items</h3>
        <button type="button" onClick={addItem} className="btn-primary" style={{ padding: '6px 14px', fontSize: '0.85rem' }}>
          <Plus size={16} /> Add Item
        </button>
      </div>

      <div className="items-list">
        {items.map((item, index) => (
          <div key={index} className="item-row" style={{ 
            display: 'grid', 
            gridTemplateColumns: '1fr 1fr 80px 40px', 
            gap: '10px', 
            marginBottom: '10px',
            alignItems: 'end'
          }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label style={{ fontSize: '0.75rem' }}>Cloth Type</label>
              <select
                className="form-select"
                value={item.type_id}
                onChange={(e) => updateItem(index, 'type_id', e.target.value)}
                required
              >
                <option value="">Select Type</option>
                {options.clothing_types.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label style={{ fontSize: '0.75rem' }}>Service</label>
              <select
                className="form-select"
                value={item.service_id}
                onChange={(e) => updateItem(index, 'service_id', e.target.value)}
                required
                disabled={!item.type_id}
              >
                <option value="">Select Service</option>
                {(options.services || []).filter(s => 
                  (options.pricing || []).some(p => Number(p.service_id) === Number(s.id) && Number(p.type_id) === Number(item.type_id))
                ).map((s) => {
                  const pricingItem = options.pricing.find(p => Number(p.service_id) === Number(s.id) && Number(p.type_id) === Number(item.type_id));
                  return (
                    <option key={s.id} value={s.id}>
                      {s.name} {pricingItem ? `(₹${pricingItem.price})` : ''}
                    </option>
                  );
                })}
              </select>
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label style={{ fontSize: '0.75rem' }}>Qty</label>
              <input
                type="number"
                min="1"
                className="form-select"
                value={item.quantity}
                onChange={(e) => updateItem(index, 'quantity', parseInt(e.target.value) || 1)}
                required
              />
            </div>

            <button
              type="button"
              onClick={() => removeItem(index)}
              className="action-btn delete-btn"
              disabled={items.length === 1}
              title="Remove Item"
            >
              <Trash2 size={16} />
            </button>
          </div>
        ))}
      </div>

      <div className="total-display" style={{ 
        marginTop: '1.5rem', 
        paddingTeop: '1rem', 
        borderTop: '1px solid #e5e7eb',
        display: 'flex',
        justifyContent: 'flex-end'
      }}>
        <div style={{ textAlign: 'right' }}>
          <span style={{ fontSize: '0.9rem', color: '#6b7280' }}>Estimated Total: </span>
          <span style={{ fontSize: '1.25rem', fontWeight: '700', color: '#059669' }}>
            ₹{calculateTotal(items).toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  );
};

export default OrderItemsForm;
