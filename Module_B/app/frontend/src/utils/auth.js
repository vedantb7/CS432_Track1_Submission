const API_URL = '/api';

export const login = async (username, password, expectedRole = null) => {
  try {
    const body = { username, password };
    if (expectedRole) {
      body.expected_role = expectedRole;
    }
    
    const response = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Login failed');

    localStorage.setItem('freshwash_role', data.role);
    localStorage.setItem('freshwash_user', data.username);
    localStorage.setItem('freshwash_token', data.token);
    if (data.member_id) localStorage.setItem('member_id', data.member_id);
    if (data.employee_id) localStorage.setItem('employee_id', data.employee_id);
    
    localStorage.setItem('user', JSON.stringify({
      username: data.username,
      role: data.role,
      memberId: data.member_id,
      employeeId: data.employee_id
    }));
    
    return data.role;
  } catch (error) {
    console.error('Login Error:', error);
    throw error;
  }
};

export const signup = async (profileData) => {
  try {
    const response = await fetch(`${API_URL}/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profileData),
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Signup failed');

    // After successful signup, log the user in as 'user' role
    return await login(profileData.username, profileData.password, 'user');
  } catch (error) {
    console.error('Signup Error:', error);
    throw error;
  }
};

export const logout = () => {
  localStorage.clear();
  window.location.href = '/';
};

export const getRole = () => localStorage.getItem('freshwash_role');
export const getUser = () => localStorage.getItem('freshwash_user');
export const getMemberId = () => localStorage.getItem('member_id');
export const getEmployeeId = () => localStorage.getItem('employee_id');
export const isAuthenticated = () => !!localStorage.getItem('freshwash_role');
