// api.js - API integration layer
const API_BASE_URL = '/api';

// Safe localStorage wrapper
const safeStorage = {
  getItem(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  },
  setItem(key, value) {
    try { localStorage.setItem(key, value); } catch (e) {}
  },
  removeItem(key) {
    try { localStorage.removeItem(key); } catch (e) {}
  }
};

// Helper function for API calls
async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include'
    };
    if (data && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(data);
    }
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.message || result.error || 'API call failed');
        }
        return result;
    } catch (error) {
        console.error('API Error:', error);
        // Suppress error toast for auth check endpoint (called on page load)
        const isAuthCheck = endpoint.includes('/auth/me');
        if (typeof showToast === 'function' && !isAuthCheck) {
            showToast('Error', error.message, 'danger');
        }
        throw error;
    }
}

// Authentication API
const AuthAPI = {
    login: async (email, password, remember = false) => {
        const result = await apiCall('/auth/login', 'POST', { email, password, remember });
        if (result.success) {
            safeStorage.setItem('currentUser', JSON.stringify(result.user));
        }
        return result;
    },
    register: async (userData) => {
        return await apiCall('/auth/register', 'POST', userData);
    },
    logout: async () => {
        const result = await apiCall('/auth/logout', 'POST');
        safeStorage.removeItem('currentUser');
        return result;
    },
    getCurrentUser: async () => {
        return await apiCall('/auth/me');
    }
};

// Files API
const FilesAPI = {
    getAll: async () => {
        return await apiCall('/files');
    },
    upload: async (formData) => {
        const response = await fetch(`${API_BASE_URL}/files`, {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });
        return await response.json();
    },
    delete: async (fileId) => {
        return await apiCall(`/files/${fileId}`, 'DELETE');
    },
    download: (fileId) => {
        window.open(`${API_BASE_URL}/files/${fileId}/download`, '_blank');
    }
};

// Accounts API
const AccountsAPI = {
    getAll: async () => {
        return await apiCall('/accounts');
    },
    create: async (accountData) => {
        return await apiCall('/accounts', 'POST', accountData);
    },
    update: async (userId, accountData) => {
        return await apiCall(`/accounts/${userId}`, 'PUT', accountData);
    },
    delete: async (userId) => {
        return await apiCall(`/accounts/${userId}`, 'DELETE');
    }
};

// Profile API
const ProfileAPI = {
    get: async () => {
        return await apiCall('/profile');
    },
    update: async (profileData) => {
        return await apiCall('/profile', 'PUT', profileData);
    },
    changePassword: async (passwordData) => {
        return await apiCall('/profile/password', 'PUT', passwordData);
    },
    uploadAvatar: async (formData) => {
        const response = await fetch(`${API_BASE_URL}/profile/avatar`, {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });
        return await response.json();
    },
    deleteAvatar: async () => {
        const response = await fetch(`${API_BASE_URL}/profile/avatar`, {
            method: 'DELETE',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' }
        });
        return await response.json();
    }
};

// Audit Trail API
const AuditAPI = {
    getAll: async (filters = {}) => {
        const params = new URLSearchParams(filters).toString();
        return await apiCall(`/audit-trail?${params}`);
    },
    getStats: async () => {
        return await apiCall('/audit-trail/stats');
    }
};

// Stats API
const StatsAPI = {
    get: async () => {
        return await apiCall('/stats');
    }
};

// Announcements API
const AnnouncementsAPI = {
    getAll: async (category = 'all') => {
        return await apiCall(`/announcements?category=${category}`);
    },
    create: async (data) => {
        return await apiCall('/announcements', 'POST', data);
    },
    update: async (id, data) => {
        return await apiCall(`/announcements/${id}`, 'PUT', data);
    },
    delete: async (id) => {
        return await apiCall(`/announcements/${id}`, 'DELETE');
    }
};