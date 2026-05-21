// api.js - API integration layer (include this in your HTML after script.js)
// This file connects the frontend to the Flask backend

const API_BASE_URL = 'http://localhost:5000/api';

// Safe localStorage wrapper  prevents "SecurityError: Failed to read 'localStorage'" in sandboxed iframes
// (common in some preview environments, file:// protocol, or strict sandboxed contexts)
const safeStorage = {
  getItem(key) {
    try {
      return localStorage.getItem(key);
    } catch (err) {
      console.warn('[DocuManage] localStorage unavailable (sandboxed):', err.message);
      return null;
    }
  },
  setItem(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch (err) {
      console.warn('[DocuManage] localStorage unavailable (sandboxed):', err.message);
    }
  },
  removeItem(key) {
    try {
      localStorage.removeItem(key);
    } catch (err) {
      console.warn('[DocuManage] localStorage unavailable (sandboxed):', err.message);
    }
  }
};

// Helper function for API calls
async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        },
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
        if (typeof showToast === 'function') {
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
        const result = await apiCall('/auth/register', 'POST', userData);
        return result;
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

    download: (fileId) => {
        window.open(`${API_BASE_URL}/files/${fileId}`, '_blank');
    },

    delete: async (fileId) => {
        return await apiCall(`/files/${fileId}`, 'DELETE');
    },

    share: async (fileId, email, permission, message) => {
        return await apiCall(`/files/${fileId}/share`, 'POST', { email, permission, message });
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
    }
};

// Notifications API
const NotificationsAPI = {
    getAll: async () => {
        return await apiCall('/notifications');
    },

    getUnreadCount: async () => {
        return await apiCall('/notifications/unread-count');
    },

    markAsRead: async (notifId) => {
        return await apiCall(`/notifications/${notifId}/read`, 'POST');
    },

    markAllAsRead: async () => {
        return await apiCall('/notifications/mark-all-read', 'POST');
    }
};

// Messages API
const MessagesAPI = {
    getAll: async () => {
        return await apiCall('/messages');
    },

    getUnreadCount: async () => {
        return await apiCall('/messages/unread-count');
    },

    markAsRead: async (msgId) => {
        return await apiCall(`/messages/${msgId}/read`, 'POST');
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

// Override existing functions to use API

// Override login function
async function handleLogin(email, password) {
    try {
        const result = await AuthAPI.login(email, password);
        if (typeof showToast === 'function') {
            showToast('Welcome!', `Logged in as ${result.user.role.toUpperCase()}`, 'success');
        }
        setTimeout(() => {
            window.location.href = 'index.html';
        }, 1500);
        return result;
    } catch (error) {
        if (typeof showToast === 'function') {
            showToast('Login Failed', error.message, 'danger');
        }
        throw error;
    }
}

// Override logout function
async function handleLogout() {
    try {
        await AuthAPI.logout();
        if (typeof showToast === 'function') {
            showToast('Logged Out', 'You have been successfully logged out.', 'info');
        }
        setTimeout(() => {
            window.location.href = 'login.html';
        }, 1000);
    } catch (error) {
        console.error('Logout error:', error);
        safeStorage.removeItem('currentUser');
        window.location.href = 'login.html';
    }
}

// Update the existing logout function if it exists
if (typeof logout !== 'undefined') {
    logout = handleLogout;
}

// Load dashboard data from API
async function loadDashboardDataFromAPI() {
    try {
        const stats = await StatsAPI.get();

        const totalFilesEl = document.getElementById('totalFiles');
        const totalUsersEl = document.getElementById('totalUsers');
        const totalStorageEl = document.getElementById('totalStorage');
        const recentActivityEl = document.getElementById('recentActivity');

        if (totalFilesEl && typeof animateNumber === 'function') animateNumber(totalFilesEl, 0, stats.total_files, 1000);
        if (totalUsersEl && typeof animateNumber === 'function') animateNumber(totalUsersEl, 0, stats.total_users, 1000);
        if (totalStorageEl) totalStorageEl.textContent = stats.storage_used;
        if (recentActivityEl && typeof animateNumber === 'function') animateNumber(recentActivityEl, 0, stats.recent_activity, 1000);

        const files = await FilesAPI.getAll();
        if (typeof filesData !== 'undefined') {
            filesData.length = 0;
            filesData.push(...files);
        }
        if (typeof loadFilesGrid === 'function') loadFilesGrid();

    } catch (error) {
        console.error('Failed to load dashboard data:', error);
    }
}

// Load accounts from API
async function loadAccountsFromAPI() {
    try {
        const accounts = await AccountsAPI.getAll();
        if (typeof accountsData !== 'undefined') {
            accountsData.length = 0;
            accountsData.push(...accounts.map(a => ({
                id: a.id,
                name: a.name,
                email: a.email,
                role: a.role,
                status: a.status,
                avatar: a.avatar
            })));
        }
        if (typeof loadAccounts === 'function') loadAccounts();
    } catch (error) {
        console.error('Failed to load accounts:', error);
    }
}

// Load audit trail from API
async function loadAuditTrailFromAPI() {
    try {
        const trails = await AuditAPI.getAll();
        if (typeof auditTrailData !== 'undefined') {
            auditTrailData.length = 0;
            auditTrailData.push(...trails.map(t => ({
                id: t.id,
                action: t.action,
                description: t.description,
                user: t.user,
                time: t.time,
                type: t.type
            })));
        }
        if (typeof loadAuditTrail === 'function') loadAuditTrail();
    } catch (error) {
        console.error('Failed to load audit trail:', error);
    }
}

// Load notifications from API
async function loadNotificationsFromAPI() {
    try {
        const notifications = await NotificationsAPI.getAll();
        if (typeof notificationsData !== 'undefined') {
            notificationsData.length = 0;
            notificationsData.push(...notifications.map(n => ({
                id: n.id,
                title: n.title,
                message: n.message,
                time: n.time,
                type: n.type,
                read: n.read
            })));
        }
        if (typeof renderNotifications === 'function') renderNotifications();
        if (typeof updateNotificationBadges === 'function') updateNotificationBadges();
    } catch (error) {
        console.error('Failed to load notifications:', error);
    }
}

// Load messages from API
async function loadMessagesFromAPI() {
    try {
        const messages = await MessagesAPI.getAll();
        if (typeof messagesData !== 'undefined') {
            messagesData.length = 0;
            messagesData.push(...messages.map(m => ({
                id: m.id,
                sender: m.sender,
                message: m.message,
                time: m.time,
                avatar: m.sender_avatar,
                read: m.read
            })));
        }
        if (typeof renderMessages === 'function') renderMessages();
        if (typeof updateNotificationBadges === 'function') updateNotificationBadges();
    } catch (error) {
        console.error('Failed to load messages:', error);
    }
}

// Update notification badges from API
async function updateBadgesFromAPI() {
    try {
        const [notifCount, msgCount] = await Promise.all([
            NotificationsAPI.getUnreadCount(),
            MessagesAPI.getUnreadCount()
        ]);

        const notificationBadge = document.getElementById('notificationBadge');
        const messageBadge = document.getElementById('messageBadge');

        if (notificationBadge) {
            notificationBadge.textContent = notifCount.count;
            notificationBadge.style.display = notifCount.count > 0 ? 'block' : 'none';
        }

        if (messageBadge) {
            messageBadge.textContent = msgCount.count;
            messageBadge.style.display = msgCount.count > 0 ? 'block' : 'none';
        }
    } catch (error) {
        console.error('Failed to update badges:', error);
    }
}

// Override file upload
async function handleFileUploadAPI(files) {
    if (typeof isViewer === 'function' && isViewer()) {
        if (typeof showToast === 'function') showToast('Access Denied', 'Viewers cannot upload files.', 'danger');
        return;
    }

    for (let file of files) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            const result = await FilesAPI.upload(formData);
            if (typeof filesData !== 'undefined') filesData.unshift(result);
            if (typeof showToast === 'function') showToast('File Uploaded', `${file.name} has been uploaded successfully.`, 'success');
        } catch (error) {
            if (typeof showToast === 'function') showToast('Upload Failed', `Failed to upload ${file.name}`, 'danger');
        }
    }

    if (typeof loadFilesGrid === 'function') loadFilesGrid();
}

// Override delete file
async function deleteFileAPI(id) {
    if (typeof isViewer === 'function' && isViewer()) {
        if (typeof showToast === 'function') showToast('Access Denied', 'Viewers cannot delete files.', 'danger');
        return;
    }

    if (typeof filesData === 'undefined') return;
    const file = filesData.find(f => f.id === id);
    if (!file) return;

    if (confirm(`Are you sure you want to delete ${file.name}?`)) {
        try {
            await FilesAPI.delete(id);
            const index = filesData.findIndex(f => f.id === id);
            if (index > -1) {
                filesData.splice(index, 1);
                if (typeof loadFilesGrid === 'function') loadFilesGrid();
            }
            if (typeof showToast === 'function') showToast('File Deleted', `${file.name} has been deleted.`, 'danger');
        } catch (error) {
            if (typeof showToast === 'function') showToast('Delete Failed', error.message, 'danger');
        }
    }
}

// Override delete account
async function deleteAccountAPI(id) {
    if (typeof accountsData === 'undefined') return;
    const account = accountsData.find(a => a.id === id);
    if (!account) return;

    if (confirm(`Are you sure you want to delete ${account.name}'s account?`)) {
        try {
            await AccountsAPI.delete(id);
            const index = accountsData.findIndex(a => a.id === id);
            if (index > -1) {
                accountsData.splice(index, 1);
                if (typeof loadAccounts === 'function') loadAccounts();
            }
            if (typeof showToast === 'function') showToast('Account Deleted', `${account.name}'s account has been deleted.`, 'danger');
        } catch (error) {
            if (typeof showToast === 'function') showToast('Delete Failed', error.message, 'danger');
        }
    }
}

// Initialize API integration
document.addEventListener('DOMContentLoaded', async function() {
    const publicPages = ['login.html', 'register.html', ''];
    const currentPage = window.location.pathname.split('/').pop();

    if (!publicPages.includes(currentPage)) {
        try {
            const user = await AuthAPI.getCurrentUser();
            safeStorage.setItem('currentUser', JSON.stringify(user));
        } catch (error) {
            window.location.href = 'login.html';
            return;
        }
    }

    if (document.getElementById('filesGrid')) {
        loadDashboardDataFromAPI();
    }

    if (document.getElementById('accountsGrid')) {
        loadAccountsFromAPI();
    }

    if (document.getElementById('auditTimeline')) {
        loadAuditTrailFromAPI();
    }

    loadNotificationsFromAPI();
    loadMessagesFromAPI();
    updateBadgesFromAPI();

    setInterval(updateBadgesFromAPI, 30000);
});