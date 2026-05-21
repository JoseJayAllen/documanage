// api.js - FIXED API Integration Layer
// This file connects the frontend to the Flask backend

// ====================== CONFIGURATION ======================
const API_BASE_URL = window.location.origin + '/api';

// ====================== UTILITY FUNCTIONS ======================
function showToast(title, message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const id = 'toast-' + Date.now();
    const bgClass = {
        success: 'bg-success',
        danger: 'bg-danger',
        warning: 'bg-warning',
        info: 'bg-info'
    }[type] || 'bg-info';

    const toastHtml = `
        <div id="${id}" class="toast align-items-center text-white ${bgClass} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    <strong>${title}</strong><br>${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', toastHtml);
    const toastElement = document.getElementById(id);
    const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
    toast.show();

    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

// Helper function for API calls
async function apiCall(endpoint, method = 'GET', data = null, isFormData = false) {
    const options = {
        method: method,
        credentials: 'include'
    };

    if (!isFormData) {
        options.headers = {
            'Content-Type': 'application/json',
        };
    }

    if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
        options.body = isFormData ? data : JSON.stringify(data);
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
        throw error;
    }
}

// ====================== AUTHENTICATION API ======================
const AuthAPI = {
    login: async (email, password) => {
        const result = await apiCall('/auth/login', 'POST', { email, password });
        if (result.success) {
            localStorage.setItem('currentUser', JSON.stringify(result.user));
        }
        return result;
    },

    register: async (userData) => {
        const result = await apiCall('/auth/register', 'POST', userData);
        // Note: Registration no longer auto-logs in
        return result;
    },

    logout: async () => {
        try {
            const result = await apiCall('/auth/logout', 'POST');
            localStorage.removeItem('currentUser');
            return result;
        } catch (error) {
            localStorage.removeItem('currentUser');
            throw error;
        }
    },

    getCurrentUser: async () => {
        return await apiCall('/auth/me');
    }
};

// ====================== PROFILE API ======================
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
        return await apiCall('/profile/avatar', 'POST', formData, true);
    }
};

// ====================== FILES API ======================
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
        // Download in same tab
        window.location.href = `${API_BASE_URL}/files/${fileId}/download`;
    },

    delete: async (fileId) => {
        return await apiCall(`/files/${fileId}`, 'DELETE');
    }
};

// ====================== ACCOUNTS API ======================
const AccountsAPI = {
    getAll: async () => {
        return await apiCall('/accounts');
    },

    getStats: async () => {
        return await apiCall('/accounts/stats');
    },

    create: async (accountData) => {
        return await apiCall('/accounts', 'POST', accountData);
    },

    update: async (userId, accountData) => {
        return await apiCall(`/accounts/${userId}`, 'PUT', accountData);
    },

    delete: async (userId) => {
        return await apiCall(`/accounts/${userId}`, 'DELETE');
    },

    activate: async (userId) => {
        return await apiCall(`/accounts/${userId}/activate`, 'POST');
    },

    deactivate: async (userId) => {
        return await apiCall(`/accounts/${userId}/deactivate`, 'POST');
    }
};

// ====================== AUDIT TRAIL API ======================
const AuditAPI = {
    getAll: async (filters = {}) => {
        const params = new URLSearchParams(filters).toString();
        return await apiCall(`/audit-trail?${params}`);
    },

    getStats: async () => {
        return await apiCall('/audit-trail/stats');
    },

    getRecentLogins: async () => {
        return await apiCall('/audit-trail/recent-logins');
    }
};

// ====================== STATS API ======================
const StatsAPI = {
    get: async () => {
        return await apiCall('/stats');
    }
};

// ====================== NOTIFICATIONS API ======================
const NotificationsAPI = {
    getAll: async () => {
        return await apiCall('/notifications');
    },

    getUnreadCount: async () => {
        return await apiCall('/notifications/unread-count');
    }
};

const MessagesAPI = {
    getAll: async () => {
        return await apiCall('/messages');
    },

    getUnreadCount: async () => {
        return await apiCall('/messages/unread-count');
    }
};

// ====================== CURRENT USER MANAGEMENT ======================
let currentUser = null;

async function loadCurrentUser() {
    try {
        // Try to get from API first
        const user = await AuthAPI.getCurrentUser();
        currentUser = user;
        localStorage.setItem('currentUser', JSON.stringify(user));
        updateUIWithUser(user);
        return user;
    } catch (error) {
        // Try localStorage as fallback
        const stored = localStorage.getItem('currentUser');
        if (stored) {
            currentUser = JSON.parse(stored);
            updateUIWithUser(currentUser);
            return currentUser;
        }
        throw error;
    }
}

function updateUIWithUser(user) {
    if (!user) return;

    // Update avatar images
    document.querySelectorAll('.user-avatar').forEach(img => {
        img.src = user.avatar || `https://ui-avatars.com/api/?name=${user.first_name}+${user.last_name}&background=4e73df&color=fff`;
    });

    // Update user names
    document.querySelectorAll('.user-name').forEach(el => {
        el.textContent = user.name || `${user.first_name} ${user.last_name}`;
    });

    // Show/hide admin-only elements
    if (user.role === 'admin') {
        document.querySelectorAll('.admin-only').forEach(el => {
            el.style.display = 'block';
        });
        document.querySelectorAll('.admin-only-action').forEach(el => {
            el.style.display = 'block';
        });
    } else {
        document.querySelectorAll('.admin-only').forEach(el => {
            el.style.display = 'none';
        });
        document.querySelectorAll('.admin-only-action').forEach(el => {
            el.style.display = 'none';
        });
    }

    // Hide elements for viewers
    if (user.role === 'viewer') {
        document.querySelectorAll('.editor-only, .admin-only').forEach(el => {
            el.style.display = 'none';
        });
    }
}

function logout() {
    AuthAPI.logout().then(() => {
        localStorage.removeItem('currentUser');
        window.location.href = 'login.html';
    }).catch(() => {
        localStorage.removeItem('currentUser');
        window.location.href = 'login.html';
    });
}

// ====================== DASHBOARD FUNCTIONS ======================
async function loadDashboardStats() {
    try {
        const data = await StatsAPI.get();

        const totalFilesEl = document.getElementById('totalFiles');
        const totalUsersEl = document.getElementById('totalUsers');
        const totalStorageEl = document.getElementById('totalStorage');
        const recentActivityEl = document.getElementById('recentActivity');

        if (totalFilesEl) totalFilesEl.textContent = data.total_files || 0;
        if (totalUsersEl) totalUsersEl.textContent = data.total_users || 0;
        if (totalStorageEl) totalStorageEl.textContent = data.storage_used || '0 MB';
        if (recentActivityEl) recentActivityEl.textContent = data.recent_activity || 0;
    } catch (error) {
        console.error('Failed to load dashboard stats:', error);
    }
}

// ====================== FILES FUNCTIONS ======================
let filesData = [];

async function loadFiles() {
    try {
        filesData = await FilesAPI.getAll();
        renderFilesGrid();
        renderFilesList();
    } catch (error) {
        console.error('Failed to load files:', error);
    }
}

function renderFilesGrid() {
  const grid = document.getElementById('filesGrid');
  if (!grid) return;

  if (filesData.length === 0) {
    grid.innerHTML = `<div class="col-12 text-center py-5">No files uploaded yet</div>`;
    return;
  }

  grid.innerHTML = filesData.map(file => `
    <div class="col-md-6 col-lg-4 col-xl-3 mb-4 file-item" data-type="${file.type}">
      <div class="file-card">
        <div class="file-icon ${file.type}"><i class="fas fa-${getFileIcon(file.type)}"></i></div>
        <div class="file-name">${file.name}</div>
        <div class="file-meta">${file.size} • ${file.date}</div>
        <div class="file-actions mt-3">
          <button class="btn btn-sm btn-outline-success" onclick="previewFile(${file.id})" title="Preview">
            <i class="fas fa-eye"></i>
          </button>
          <button class="btn btn-sm btn-outline-primary" onclick="downloadFile(${file.id})" title="Download">
            <i class="fas fa-download"></i>
          </button>
          <button class="btn btn-sm btn-outline-danger ${currentUser?.role === 'viewer' ? 'disabled' : ''}" 
                  onclick="deleteFile(${file.id})" ${currentUser?.role === 'viewer' ? 'disabled' : ''} title="Delete">
            <i class="fas fa-trash"></i>
          </button>
        </div>
      </div>
    </div>
  `).join('');
}

function renderFilesList() {
  const tbody = document.getElementById('filesListBody') || document.querySelector('#filesList tbody');
  if (!tbody) return;

  if (filesData.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="text-center py-4">No files uploaded yet</td></tr>';
    return;
  }

  tbody.innerHTML = filesData.map(file => `
    <tr class="file-item" data-type="${file.type}">
      <td><i class="fas fa-${getFileIcon(file.type)} me-2"></i>${file.name}</td>
      <td>${file.type.toUpperCase()}</td>
      <td>${file.size}</td>
      <td>${file.date}</td>
      <td>
        <button class="btn btn-sm btn-outline-success me-1" onclick="previewFile(${file.id})" title="Preview"><i class="fas fa-eye"></i></button>
        <button class="btn btn-sm btn-outline-primary me-1" onclick="downloadFile(${file.id})" title="Download"><i class="fas fa-download"></i></button>
        <button class="btn btn-sm btn-outline-danger ${currentUser?.role === 'viewer' ? 'disabled' : ''}" 
                onclick="deleteFile(${file.id})" ${currentUser?.role === 'viewer' ? 'disabled' : ''} title="Delete"><i class="fas fa-trash"></i></button>
      </td>
    </tr>
  `).join('');
}

function getFileIcon(type) {
    const icons = {
        pdf: 'file-pdf',
        doc: 'file-word',
        img: 'file-image',
        xls: 'file-excel'
    };
    return icons[type] || 'file';
}

function getFileColor(type) {
    const colors = {
        pdf: 'danger',
        doc: 'primary',
        img: 'success',
        xls: 'warning'
    };
    return colors[type] || 'secondary';
}

function downloadFile(fileId) {
    FilesAPI.download(fileId);
}

async function deleteFile(fileId) {
    if (currentUser?.role === 'viewer') {
        showToast('Access Denied', 'Viewers cannot delete files', 'danger');
        return;
    }

    const file = filesData.find(f => f.id === fileId);
    if (!file) return;

    if (!confirm(`Are you sure you want to delete "${file.name}"?`)) return;

    try {
        await FilesAPI.delete(fileId);
        filesData = filesData.filter(f => f.id !== fileId);
        renderFilesGrid();
        renderFilesList();
        showToast('Success', 'File deleted successfully', 'success');
        loadDashboardStats(); // Refresh stats
    } catch (error) {
        showToast('Error', error.message || 'Failed to delete file', 'danger');
    }
}

// ====================== FILE UPLOAD ======================
function initFileUpload() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');

    if (!uploadArea || !fileInput) return;

    // Click on upload area triggers file input
    uploadArea.addEventListener('click', (e) => {
        if (e.target.tagName !== 'BUTTON' && !e.target.closest('button')) {
            fileInput.click();
        }
    });

    // Button click also triggers file input
    const uploadBtn = uploadArea.querySelector('button');
    if (uploadBtn) {
        uploadBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.click();
        });
    }

    // Handle file selection
    fileInput.addEventListener('change', async (e) => {
        if (currentUser?.role === 'viewer') {
            showToast('Access Denied', 'Viewers cannot upload files', 'danger');
            fileInput.value = '';
            return;
        }

        const files = e.target.files;
        if (!files.length) return;

        for (const file of files) {
            const formData = new FormData();
            formData.append('file', file);

            try {
                const result = await FilesAPI.upload(formData);
                filesData.unshift(result);
                showToast('Success', `"${file.name}" uploaded successfully`, 'success');
            } catch (error) {
                showToast('Error', `Failed to upload "${file.name}"`, 'danger');
            }
        }

        renderFilesGrid();
        renderFilesList();
        loadDashboardStats(); // Refresh stats
        fileInput.value = '';
    });

    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', async (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');

        if (currentUser?.role === 'viewer') {
            showToast('Access Denied', 'Viewers cannot upload files', 'danger');
            return;
        }

        const files = e.dataTransfer.files;
        if (!files.length) return;

        for (const file of files) {
            const formData = new FormData();
            formData.append('file', file);

            try {
                const result = await FilesAPI.upload(formData);
                filesData.unshift(result);
                showToast('Success', `"${file.name}" uploaded successfully`, 'success');
            } catch (error) {
                showToast('Error', `Failed to upload "${file.name}"`, 'danger');
            }
        }

        renderFilesGrid();
        renderFilesList();
        loadDashboardStats();
    });
}

// ====================== ACCOUNTS FUNCTIONS ======================
let accountsData = [];

async function loadAccounts() {
    try {
        // Load accounts
        accountsData = await AccountsAPI.getAll();
        renderAccountsGrid();
        renderAccountsTable();

        // Load stats
        const stats = await AccountsAPI.getStats();
        updateAccountsStats(stats);
    } catch (error) {
        console.error('Failed to load accounts:', error);
        showToast('Error', 'Failed to load accounts', 'danger');
    }
}

function updateAccountsStats(stats) {
    const totalEl = document.getElementById('statTotal');
    const activeEl = document.getElementById('statActive');
    const inactiveEl = document.getElementById('statInactive');
    const pendingEl = document.getElementById('statPending');

    if (totalEl) totalEl.textContent = stats.total_accounts || 0;
    if (activeEl) activeEl.textContent = stats.active_users || 0;
    if (inactiveEl) inactiveEl.textContent = stats.inactive_users || 0;
    if (pendingEl) pendingEl.textContent = stats.pending_accounts || 0;
}

function renderAccountsGrid() {
    const grid = document.getElementById('accountsGrid');
    if (!grid) return;

    if (accountsData.length === 0) {
        grid.innerHTML = `
            <div class="col-12 text-center py-5">
                <i class="fas fa-users fa-3x text-muted mb-3"></i>
                <p class="text-muted">No accounts found</p>
            </div>
        `;
        return;
    }

    grid.innerHTML = accountsData.map(account => {
        const statusColors = {
            active: 'success',
            inactive: 'danger',
            pending: 'warning'
        };

        return `
            <div class="col-md-6 col-lg-4 col-xl-3 mb-4">
                <div class="account-card card h-100">
                    <div class="card-body text-center">
                        <img src="${account.avatar}" alt="${account.name}" class="rounded-circle mb-3" width="80" height="80">
                        <h5 class="account-name mb-1">${account.name}</h5>
                        <p class="account-email text-muted mb-2">${account.email}</p>
                        <span class="badge bg-${account.role === 'admin' ? 'primary' : account.role === 'editor' ? 'success' : 'info'} mb-2">${account.role}</span>
                        <div class="mb-2">
                            <span class="badge bg-${statusColors[account.status] || 'secondary'}">${account.status}</span>
                        </div>
                        <p class="text-muted small mb-0">${account.department || 'No Department'}</p>
                        <div class="account-actions mt-3">
                            <button class="btn btn-sm btn-outline-primary me-1" onclick="openEditModal(${account.id})">
                                <i class="fas fa-edit"></i> Edit
                            </button>
                            ${account.status === 'pending' ? `
                                <button class="btn btn-sm btn-success me-1" onclick="quickActivate(${account.id})">
                                    <i class="fas fa-check"></i> Activate
                                </button>
                            ` : account.status === 'active' ? `
                                <button class="btn btn-sm btn-warning me-1" onclick="quickDeactivate(${account.id})">
                                    <i class="fas fa-ban"></i> Deactivate
                                </button>
                            ` : `
                                <button class="btn btn-sm btn-success me-1" onclick="quickActivate(${account.id})">
                                    <i class="fas fa-check"></i> Activate
                                </button>
                            `}
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteAccount(${account.id})" ${account.id === currentUser?.id ? 'disabled' : ''}>
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function renderAccountsTable() {
    const tbody = document.querySelector('#accountsTable tbody');
    if (!tbody) return;

    if (accountsData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4">No accounts found</td></tr>';
        return;
    }

    const statusColors = {
        active: 'success',
        inactive: 'danger',
        pending: 'warning'
    };

    tbody.innerHTML = accountsData.map(account => `
        <tr>
            <td>
                <div class="d-flex align-items-center">
                    <img src="${account.avatar}" alt="${account.name}" class="rounded-circle me-2" width="40" height="40">
                    <div>
                        <div class="fw-bold">${account.name}</div>
                        <small class="text-muted">${account.email}</small>
                    </div>
                </div>
            </td>
            <td><span class="badge bg-${account.role === 'admin' ? 'primary' : account.role === 'editor' ? 'success' : 'info'}">${account.role}</span></td>
            <td>${account.department || '-'}</td>
            <td><span class="badge bg-${statusColors[account.status] || 'secondary'}">${account.status}</span></td>
            <td>${account.last_login || 'Never'}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary me-1" onclick="openEditModal(${account.id})">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteAccount(${account.id})"
                        ${account.id === currentUser?.id ? 'disabled' : ''}>
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

async function deleteAccount(userId) {
    if (userId === currentUser?.id) {
        showToast('Error', 'Cannot delete your own account', 'danger');
        return;
    }

    const account = accountsData.find(a => a.id === userId);
    if (!account) return;

    if (!confirm(`Are you sure you want to delete ${account.name}'s account?`)) return;

    try {
        await AccountsAPI.delete(userId);
        accountsData = accountsData.filter(a => a.id !== userId);
        renderAccountsGrid();
        renderAccountsTable();
        showToast('Success', 'Account deleted successfully', 'success');
    } catch (error) {
        showToast('Error', error.message || 'Failed to delete account', 'danger');
    }
}

async function quickActivate(userId) {
    try {
        await AccountsAPI.activate(userId);
        showToast('Success', 'Account activated successfully', 'success');
        loadAccounts();
    } catch (error) {
        showToast('Error', error.message || 'Failed to activate account', 'danger');
    }
}

async function quickDeactivate(userId) {
    if (userId === currentUser?.id) {
        showToast('Error', 'You cannot deactivate your own account', 'danger');
        return;
    }
    try {
        await AccountsAPI.deactivate(userId);
        showToast('Success', 'Account deactivated successfully', 'success');
        loadAccounts();
    } catch (error) {
        showToast('Error', error.message || 'Failed to deactivate account', 'danger');
    }
}

function initAddAccountForm() {
    const form = document.getElementById('addAccountForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        // Validate passwords match
        if (data.password !== data.confirm_password) {
            showToast('Error', 'Passwords do not match', 'danger');
            return;
        }

        try {
            await AccountsAPI.create(data);
            showToast('Success', 'Account created successfully', 'success');

            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('addAccountModal'));
            if (modal) modal.hide();

            // Refresh accounts
            form.reset();
            loadAccounts();
        } catch (error) {
            showToast('Error', error.message || 'Failed to create account', 'danger');
        }
    });
}

// ====================== AUDIT TRAIL FUNCTIONS ======================
let auditData = [];

async function loadAuditTrail(filters = {}) {
    try {
        auditData = await AuditAPI.getAll(filters);
        renderAuditTimeline();
        renderAuditTable();

        // Load stats
        const stats = await AuditAPI.getStats();
        updateAuditStats(stats);
    } catch (error) {
        console.error('Failed to load audit trail:', error);
    }
}

function updateAuditStats(stats) {
    const totalEl = document.getElementById('totalActivities');
    const uploadsEl = document.getElementById('fileUploads');
    const downloadsEl = document.getElementById('fileDownloads');
    const loginsEl = document.getElementById('todayLogins');

    if (totalEl) totalEl.textContent = stats.total_activities.toLocaleString();
    if (uploadsEl) uploadsEl.textContent = stats.uploads.toLocaleString();
    if (downloadsEl) downloadsEl.textContent = stats.downloads.toLocaleString();
    if (loginsEl) loginsEl.textContent = stats.today_logins;
}

function renderAuditTimeline() {
    const timeline = document.getElementById('auditTimeline');
    if (!timeline) return;

    if (auditData.length === 0) {
        timeline.innerHTML = '<p class="text-muted text-center py-4">No activities found</p>';
        return;
    }

    timeline.innerHTML = auditData.map(item => `
        <div class="timeline-item">
            <div class="timeline-marker ${item.type}"></div>
            <div class="timeline-content">
                <div class="timeline-title">${item.action}</div>
                <div class="timeline-text">${item.description}</div>
                <div class="timeline-time">
                    <i class="fas fa-user me-1"></i>${item.user}
                    <i class="fas fa-clock ms-2 me-1"></i>${item.time}
                </div>
            </div>
        </div>
    `).join('');
}

function renderAuditTable() {
    const tbody = document.querySelector('#auditTable tbody');
    if (!tbody) return;

    if (auditData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center py-4">No activities found</td></tr>';
        return;
    }

    tbody.innerHTML = auditData.map(item => `
        <tr>
            <td>${item.time}</td>
            <td>
                <div class="d-flex align-items-center">
                    <img src="https://ui-avatars.com/api/?name=${encodeURIComponent(item.user)}&background=4e73df&color=fff" 
                         alt="${item.user}" class="rounded-circle me-2" width="30" height="30">
                    <span>${item.user}</span>
                </div>
            </td>
            <td><span class="badge bg-${item.type === 'success' ? 'success' : item.type === 'danger' ? 'danger' : item.type === 'warning' ? 'warning' : 'info'}">${item.action}</span></td>
            <td>${item.description}</td>
            <td><span class="badge bg-success">Success</span></td>
        </tr>
    `).join('');
}

function initAuditFilters() {
    const applyBtn = document.querySelector('button[onclick*="applyFilters"]');
    if (applyBtn) {
        applyBtn.onclick = async () => {
            const dateRange = document.getElementById('filterDateRange')?.value || 'all';
            const activityType = document.getElementById('filterActivityType')?.value || 'all';
            const user = document.getElementById('filterUser')?.value || 'all';

            await loadAuditTrail({ date_range: dateRange, activity_type: activityType, user: user });
            showToast('Success', 'Filters applied', 'success');
        };
    }
}

// ====================== PROFILE FUNCTIONS ======================
async function loadProfile() {
    try {
        const user = await ProfileAPI.get();

        // Update profile header
        const profileName = document.querySelector('.profile-name');
        const profileRole = document.querySelector('.profile-role');
        const profileAvatar = document.querySelector('.profile-avatar-large');

        if (profileName) profileName.textContent = user.name;
        if (profileRole) profileRole.innerHTML = `<i class="fas fa-briefcase me-2"></i>${user.department || 'No Department'}`;
        if (profileAvatar) profileAvatar.src = user.avatar;

        // Update form fields
        const firstNameInput = document.getElementById('firstName');
        const lastNameInput = document.getElementById('lastName');
        const emailInput = document.getElementById('email');
        const phoneInput = document.getElementById('phone');
        const idNumberInput = document.getElementById('idNumber');
        const departmentInput = document.getElementById('department');

        if (firstNameInput) firstNameInput.value = user.first_name;
        if (lastNameInput) lastNameInput.value = user.last_name;
        if (emailInput) emailInput.value = user.email;
        if (phoneInput) phoneInput.value = user.phone || '';
        if (idNumberInput) idNumberInput.value = user.id_number;
        if (departmentInput) departmentInput.value = user.department || '';

        // Update contact info
        const contactEmail = document.getElementById('contactEmail');
        const contactPhone = document.getElementById('contactPhone');
        const contactIdNumber = document.getElementById('contactIdNumber');
        const contactRole = document.getElementById('contactRole');

        if (contactEmail) contactEmail.textContent = user.email;
        if (contactPhone) contactPhone.textContent = user.phone || 'Not provided';
        if (contactIdNumber) contactIdNumber.textContent = user.id_number || '-';
        if (contactRole) contactRole.textContent = user.role?.toUpperCase() || 'User';

        // Update profile header info
        const profileEmail = document.getElementById('profileEmail');
        const profileDepartment = document.getElementById('profileDepartment');

        if (profileEmail) profileEmail.innerHTML = `<i class="fas fa-envelope me-2"></i>${user.email}`;
        if (profileDepartment) profileDepartment.innerHTML = `<i class="fas fa-briefcase me-2"></i>${user.department || 'No Department'}`;

    } catch (error) {
        console.error('Failed to load profile:', error);
    }
}

function initProfileForms() {
    // Profile form
    const profileForm = document.getElementById('profileForm');
    if (profileForm) {
        profileForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = new FormData(profileForm);
            const data = Object.fromEntries(formData.entries());

            try {
                await ProfileAPI.update(data);
                showToast('Success', 'Profile updated successfully', 'success');
            } catch (error) {
                showToast('Error', error.message || 'Failed to update profile', 'danger');
            }
        });
    }

    // Password form
    const passwordForm = document.getElementById('passwordForm');
    if (passwordForm) {
        passwordForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = new FormData(passwordForm);
            const data = Object.fromEntries(formData.entries());

            if (data.new_password !== data.confirm_password) {
                showToast('Error', 'New passwords do not match', 'danger');
                return;
            }

            try {
                await ProfileAPI.changePassword(data);
                showToast('Success', 'Password changed successfully', 'success');
                passwordForm.reset();
            } catch (error) {
                showToast('Error', error.message || 'Failed to change password', 'danger');
            }
        });
    }

    // Avatar upload
    const avatarInput = document.getElementById('avatarInput');
    if (avatarInput) {
        avatarInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const formData = new FormData();
            formData.append('avatar', file);

            try {
                const result = await ProfileAPI.uploadAvatar(formData);
                document.querySelectorAll('.user-avatar, .profile-avatar-large').forEach(img => {
                    img.src = result.avatar;
                });
                showToast('Success', 'Profile photo updated', 'success');
            } catch (error) {
                showToast('Error', error.message || 'Failed to upload photo', 'danger');
            }
        });
    }
}

// ====================== EDIT MODAL FUNCTIONS ======================
let currentEditUser = null;

function openEditModal(userId) {
    currentEditUser = accountsData.find(a => a.id === userId);
    if (!currentEditUser) return;

    document.getElementById('editUserId').value = currentEditUser.id;
    document.getElementById('editAvatar').src = currentEditUser.avatar;
    document.getElementById('editFullName').textContent = currentEditUser.name;
    document.getElementById('editEmail').textContent = currentEditUser.email;
    document.getElementById('editRole').value = currentEditUser.role;
    document.getElementById('editDepartment').value = currentEditUser.department || '';
    document.getElementById('editStatus').value = currentEditUser.status;
    document.getElementById('currentStatus').textContent = currentEditUser.status.charAt(0).toUpperCase() + currentEditUser.status.slice(1);

    // Update status buttons
    updateStatusButtons(currentEditUser.status);

    const modal = new bootstrap.Modal(document.getElementById('editAccountModal'));
    modal.show();
}

function updateStatusButtons(status) {
    const btnActivate = document.getElementById('btnActivate');
    const btnPending = document.getElementById('btnPending');
    const btnDeactivate = document.getElementById('btnDeactivate');
    const statusInput = document.getElementById('editStatus');
    const statusInfo = document.getElementById('statusInfo');

    // Reset all buttons
    btnActivate.classList.remove('btn-success', 'active');
    btnActivate.classList.add('btn-outline-success');
    btnPending.classList.remove('btn-warning', 'active');
    btnPending.classList.add('btn-outline-warning');
    btnDeactivate.classList.remove('btn-danger', 'active');
    btnDeactivate.classList.add('btn-outline-danger');

    // Highlight current status
    if (status === 'active') {
        btnActivate.classList.remove('btn-outline-success');
        btnActivate.classList.add('btn-success', 'active');
    } else if (status === 'pending') {
        btnPending.classList.remove('btn-outline-warning');
        btnPending.classList.add('btn-warning', 'active');
    } else if (status === 'inactive') {
        btnDeactivate.classList.remove('btn-outline-danger');
        btnDeactivate.classList.add('btn-danger', 'active');
    }

    statusInput.value = status;
    statusInfo.innerHTML = `<i class="fas fa-info-circle me-2"></i>Current status: <strong>${status.charAt(0).toUpperCase() + status.slice(1)}</strong>`;
    statusInfo.className = `alert alert-${status === 'active' ? 'success' : status === 'pending' ? 'warning' : 'danger'}`;
}

function activateAccount() {
    updateStatusButtons('active');
}

function setPendingStatus() {
    updateStatusButtons('pending');
}

function deactivateAccount() {
    if (currentEditUser && currentEditUser.id === currentUser?.id) {
        showToast('Error', 'You cannot deactivate your own account', 'danger');
        return;
    }
    updateStatusButtons('inactive');
}

async function submitEditAccount() {
    const userId = document.getElementById('editUserId').value;
    const data = {
        role: document.getElementById('editRole').value,
        department: document.getElementById('editDepartment').value,
        status: document.getElementById('editStatus').value
    };

    try {
        await AccountsAPI.update(userId, data);
        showToast('Success', 'Account updated successfully', 'success');

        const modal = bootstrap.Modal.getInstance(document.getElementById('editAccountModal'));
        modal.hide();
        loadAccounts();
    } catch (error) {
        showToast('Error', error.message || 'Failed to update account', 'danger');
    }
}

// ====================== LOGOUT PROTECTION ======================
// Prevent back button access after logout
(function() {
    // Check if user was logged out
    if (window.location.pathname.includes('login.html')) {
        // Clear any cached page data
        if (window.history && window.history.pushState) {
            window.history.pushState(null, null, window.location.href);
            window.onpopstate = function() {
                window.history.pushState(null, null, window.location.href);
            };
        }
    }

    // For protected pages, check authentication on page show (back button)
    if (!window.location.pathname.includes('login.html') &&
        !window.location.pathname.includes('register.html')) {

        // Handle page visibility change (when user comes back to page)
        document.addEventListener('visibilitychange', async function() {
            if (document.visibilityState === 'visible') {
                try {
                    await AuthAPI.getCurrentUser();
                } catch (error) {
                    // User is not logged in, redirect to login
                    window.location.href = 'login.html';
                }
            }
        });

        // Handle pageshow event (back button)
        window.addEventListener('pageshow', async function(event) {
            if (event.persisted) {
                // Page was loaded from cache (back button)
                try {
                    await AuthAPI.getCurrentUser();
                } catch (error) {
                    // User is not logged in, redirect to login
                    window.location.href = 'login.html';
                }
            }
        });
    }
})();

// ====================== INITIALIZATION ======================
document.addEventListener('DOMContentLoaded', async () => {
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    const publicPages = ['login.html', 'register.html', ''];

    // Check authentication for protected pages
    if (!publicPages.includes(currentPage)) {
        try {
            await loadCurrentUser();
        } catch (error) {
            window.location.href = 'login.html';
            return;
        }
    }

    // Initialize page-specific functionality
    if (document.getElementById('filesGrid')) {
        loadDashboardStats();
        loadFiles();
        initFileUpload();
    }

    if (document.getElementById('accountsGrid')) {
        loadAccounts();
        initAddAccountForm();
    }

    if (document.getElementById('auditTimeline')) {
        loadAuditTrail();
        initAuditFilters();
    }

    if (document.querySelector('.profile-name')) {
        loadProfile();
        initProfileForms();
    }
});

// Expose functions globally
window.showToast = showToast;
window.logout = logout;
window.downloadFile = downloadFile;
window.deleteFile = deleteFile;
window.deleteAccount = deleteAccount;
window.quickActivate = quickActivate;
window.quickDeactivate = quickDeactivate;
window.openEditModal = openEditModal;
window.submitEditAccount = submitEditAccount;
window.activateAccount = activateAccount;
window.deactivateAccount = deactivateAccount;
window.setPendingStatus = setPendingStatus;
window.updateStatusButtons = updateStatusButtons;
window.loadAccounts = loadAccounts;
window.loadAuditTrail = loadAuditTrail;
window.filterAccounts = filterAccounts;
window.toggleAccountsView = toggleAccountsView;
window.submitAddAccount = submitAddAccount;
window.exportAccounts = exportAccounts;
window.deleteAccount = deleteAccount;
window.quickActivate = quickActivate;
window.quickDeactivate = quickDeactivate;
window.loadAccounts = loadAccounts;
window.loadAuditTrail = loadAuditTrail;