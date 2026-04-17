const API_URL = '/api';

// Dashboard APIs
export const getAdminDashboard = async () => {
  try {
    const response = await fetch(`${API_URL}/admin/dashboard`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to fetch dashboard');
    return data;
  } catch (error) {
    console.error('Dashboard Error:', error);
    throw error;
  }
};

// Orders APIs
export const getAllOrders = async () => {
  try {
    const response = await fetch(`${API_URL}/admin/orders`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to fetch orders');
    return data;
  } catch (error) {
    console.error('Orders Error:', error);
    throw error;
  }
};

export const createOrder = async (orderData) => {
  try {
    const response = await fetch(`${API_URL}/admin/orders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(orderData),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to create order');
    return data;
  } catch (error) {
    console.error('Create Order Error:', error);
    throw error;
  }
};

export const getOrderDetails = async (orderId) => {
  try {
    const response = await fetch(`${API_URL}/admin/orders/${orderId}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to fetch order details');
    return data;
  } catch (error) {
    console.error('Order Details Error:', error);
    throw error;
  }
};

export const updateOrderStatus = async (orderId, status) => {
  try {
    const response = await fetch(`${API_URL}/admin/orders/${orderId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to update order');
    return data;
  } catch (error) {
    console.error('Update Order Error:', error);
    throw error;
  }
};

export const deleteOrder = async (orderId) => {
  try {
    const response = await fetch(`${API_URL}/admin/orders/${orderId}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to delete order');
    return data;
  } catch (error) {
    console.error('Delete Order Error:', error);
    throw error;
  }
};

// Payments APIs
export const getAllPayments = async () => {
  try {
    const response = await fetch(`${API_URL}/admin/payments`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to fetch payments');
    return data;
  } catch (error) {
    console.error('Payments Error:', error);
    throw error;
  }
};

export const getPaymentDetails = async (paymentId) => {
  try {
    const response = await fetch(`${API_URL}/admin/payments/${paymentId}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to fetch payment details');
    return data;
  } catch (error) {
    console.error('Payment Details Error:', error);
    throw error;
  }
};

export const updatePaymentStatus = async (paymentId, status) => {
  try {
    const response = await fetch(`${API_URL}/admin/payments/${paymentId}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to update payment');
    return data;
  } catch (error) {
    console.error('Update Payment Error:', error);
    throw error;
  }
};

// Feedbacks APIs
export const getAllFeedbacks = async () => {
  try {
    const response = await fetch(`${API_URL}/admin/feedbacks`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to fetch feedbacks');
    return data;
  } catch (error) {
    console.error('Feedbacks Error:', error);
    throw error;
  }
};

export const getFeedbackDetails = async (feedbackId) => {
  try {
    const response = await fetch(`${API_URL}/admin/feedbacks/${feedbackId}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to fetch feedback details');
    return data;
  } catch (error) {
    console.error('Feedback Details Error:', error);
    throw error;
  }
};

export const getMemberFeedbacks = async (memberId) => {
  try {
    const response = await fetch(`${API_URL}/admin/feedbacks/member/${memberId}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to fetch member feedbacks');
    return data;
  } catch (error) {
    console.error('Member Feedbacks Error:', error);
    throw error;
  }
};

// Members APIs
export const getAllMembers = async () => {
  try {
    const response = await fetch(`${API_URL}/admin/members`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to fetch members');
    return data;
  } catch (error) {
    console.error('Members Error:', error);
    throw error;
  }
};

export const getMemberDetails = async (memberId) => {
  try {
    const response = await fetch(`${API_URL}/admin/members/${memberId}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to fetch member details');
    return data;
  } catch (error) {
    console.error('Member Details Error:', error);
    throw error;
  }
};

export const updateMember = async (memberId, memberData) => {
  try {
    const response = await fetch(`${API_URL}/admin/members/${memberId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(memberData),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to update member');
    return data;
  } catch (error) {
    console.error('Update Member Error:', error);
    throw error;
  }
};

export const deleteMember = async (memberId) => {
  try {
    const response = await fetch(`${API_URL}/admin/members/${memberId}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to delete member');
    return data;
  } catch (error) {
    console.error('Delete Member Error:', error);
    throw error;
  }
};

// Employees APIs
export const getAllEmployees = async () => {
  try {
    const response = await fetch(`${API_URL}/admin/employees`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to fetch employees');
    return data;
  } catch (error) {
    console.error('Employees Error:', error);
    throw error;
  }
};

export const getEmployeeDetails = async (employeeId) => {
  try {
    const response = await fetch(`${API_URL}/admin/employees/${employeeId}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to fetch employee details');
    return data;
  } catch (error) {
    console.error('Employee Details Error:', error);
    throw error;
  }
};

export const createEmployee = async (employeeData) => {
  try {
    const response = await fetch(`${API_URL}/admin/employees`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(employeeData),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to create employee');
    return data;
  } catch (error) {
    console.error('Create Employee Error:', error);
    throw error;
  }
};

export const updateEmployee = async (employeeId, employeeData) => {
  try {
    const response = await fetch(`${API_URL}/admin/employees/${employeeId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(employeeData),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to update employee');
    return data;
  } catch (error) {
    console.error('Update Employee Error:', error);
    throw error;
  }
};

export const deleteEmployee = async (employeeId) => {
  try {
    const response = await fetch(`${API_URL}/admin/employees/${employeeId}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to delete employee');
    return data;
  } catch (error) {
    console.error('Delete Employee Error:', error);
    throw error;
  }
};

// Lost Items APIs
export const getAllLostItems = async () => {
  try {
    const response = await fetch(`${API_URL}/admin/lost-items`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to fetch lost items');
    return data;
  } catch (error) {
    console.error('Lost Items Error:', error);
    throw error;
  }
};

export const getLostItemDetails = async (lostItemId) => {
  try {
    const response = await fetch(`${API_URL}/admin/lost-items/${lostItemId}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to fetch lost item details');
    return data;
  } catch (error) {
    console.error('Lost Item Details Error:', error);
    throw error;
  }
};

export const updateLostItemStatus = async (lostItemId, status) => {
  try {
    const response = await fetch(`${API_URL}/admin/lost-items/${lostItemId}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to update lost item');
    return data;
  } catch (error) {
    console.error('Update Lost Item Error:', error);
    throw error;
  }
};

export const fastSearchLostItem = async (lostItemId) => {
  try {
    const response = await fetch(`${API_URL}/admin/lost-items/fast-search/${lostItemId}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to fast search lost item');
    return data;
  } catch (error) {
    console.error('Fast Search Lost Item Error:', error);
    throw error;
  }
};

export const rangeSearchLostItems = async (startId, endId) => {
  try {
    const response = await fetch(`${API_URL}/admin/lost-items/range-search?start=${startId}&end=${endId}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to range search lost items');
    return data;
  } catch (error) {
    console.error('Range Search Lost Items Error:', error);
    throw error;
  }
};

export const refreshLostItemsCache = async () => {
  try {
    const response = await fetch(`${API_URL}/admin/lost-items/cache/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to refresh lost items cache');
    return data;
  } catch (error) {
    console.error('Refresh Cache Error:', error);
    throw error;
  }
};

// Services APIs
export const getAllServices = async () => {
  try {
    const response = await fetch(`${API_URL}/admin/services`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to fetch services');
    return data;
  } catch (error) {
    console.error('Services Error:', error);
    throw error;
  }
};

export const getServiceDetails = async (serviceId) => {
  try {
    const response = await fetch(`${API_URL}/admin/services/${serviceId}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to fetch service details');
    return data;
  } catch (error) {
    console.error('Service Details Error:', error);
    throw error;
  }
};

export const createService = async (serviceData) => {
  try {
    const response = await fetch(`${API_URL}/admin/services`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(serviceData),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to create service');
    return data;
  } catch (error) {
    console.error('Create Service Error:', error);
    throw error;
  }
};

export const updateService = async (serviceId, serviceData) => {
  try {
    const response = await fetch(`${API_URL}/admin/services/${serviceId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(serviceData),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to update service');
    return data;
  } catch (error) {
    console.error('Update Service Error:', error);
    throw error;
  }
};

export const deleteService = async (serviceId) => {
  try {
    const response = await fetch(`${API_URL}/admin/services/${serviceId}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to delete service');
    return data;
  } catch (error) {
    console.error('Delete Service Error:', error);
    throw error;
  }
};
// Pricing API Functions
export const getAllPricing = async () => {
  try {
    const response = await fetch(`${API_URL}/admin/pricing`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to fetch pricing');
    return data;
  } catch (error) {
    console.error('Pricing Error:', error);
    throw error;
  }
};

export const getPricingDetails = async (priceId) => {
  try {
    const response = await fetch(`${API_URL}/admin/pricing/${priceId}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to fetch pricing details');
    return data;
  } catch (error) {
    console.error('Pricing Details Error:', error);
    throw error;
  }
};

export const createPricing = async (pricingData) => {
  try {
    const response = await fetch(`${API_URL}/admin/pricing`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(pricingData),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to create pricing');
    return data;
  } catch (error) {
    console.error('Create Pricing Error:', error);
    throw error;
  }
};

export const updatePricing = async (priceId, pricingData) => {
  try {
    const response = await fetch(`${API_URL}/admin/pricing/${priceId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(pricingData),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to update pricing');
    return data;
  } catch (error) {
    console.error('Update Pricing Error:', error);
    throw error;
  }
};

export const deletePricing = async (priceId) => {
  try {
    const response = await fetch(`${API_URL}/admin/pricing/${priceId}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to delete pricing');
    return data;
  } catch (error) {
    console.error('Delete Pricing Error:', error);
    throw error;
  }
};

export const getClothingTypes = async () => {
  try {
    const response = await fetch(`${API_URL}/admin/clothing-types`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to fetch clothing types');
    return data;
  } catch (error) {
    console.error('Clothing Types Error:', error);
    throw error;
  }
};

// Profile Management APIs
export const getUserProfile = async (memberId) => {
  try {
    const response = await fetch(`${API_URL}/user/profile/${memberId}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to fetch profile');
    return data;
  } catch (error) {
    console.error('Get Profile Error:', error);
    throw error;
  }
};

export const updateUserProfile = async (memberId, profileData) => {
  try {
    const response = await fetch(`${API_URL}/user/profile/${memberId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profileData),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to update profile');
    return data;
  } catch (error) {
    console.error('Update Profile Error:', error);
    throw error;
  }
};

export const changeUserPassword = async (memberId, oldPassword, newPassword) => {
  try {
    const response = await fetch(`${API_URL}/user/profile/${memberId}/change-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to change password');
    return data;
  } catch (error) {
    console.error('Change Password Error:', error);
    throw error;
  }
};

export const getEmployeeProfile = async (employeeId) => {
  try {
    const response = await fetch(`${API_URL}/user/employee/${employeeId}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to fetch profile');
    return data;
  } catch (error) {
    console.error('Get Employee Profile Error:', error);
    throw error;
  }
};

export const updateEmployeeProfile = async (employeeId, profileData) => {
  try {
    const response = await fetch(`${API_URL}/user/employee/${employeeId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profileData),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to update profile');
    return data;
  } catch (error) {
    console.error('Update Employee Profile Error:', error);
    throw error;
  }
};

export const changeEmployeePassword = async (employeeId, oldPassword, newPassword) => {
  try {
    const response = await fetch(`${API_URL}/user/employee/${employeeId}/change-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to change password');
    return data;
  } catch (error) {
    console.error('Change Employee Password Error:', error);
    throw error;
  }
};