// script.js - Global UI utilities and shared functionality

// Toast notification system
function showToast(title, message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) return;

    const toastId = 'toast-' + Date.now();
    const bgClass = { success: 'bg-success', danger: 'bg-danger', warning: 'bg-warning', info: 'bg-info' }[type] || 'bg-info';

    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body"><strong>${title}</strong><br>${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;

    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
    toast.show();
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

// Logout handler
async function logout() {
    try {
        await AuthAPI.logout();
        showToast('Logged Out', 'You have been successfully logged out.', 'info');
        setTimeout(() => { window.location.href = 'login.html'; }, 800);
    } catch (error) {
        safeStorage.removeItem('currentUser');
        window.location.href = 'login.html';
    }
}

// Load current user and update UI
async function loadCurrentUser() {
    try {
        const user = await AuthAPI.getCurrentUser();
        safeStorage.setItem('currentUser', JSON.stringify(user));

        // Update all user-name elements
        document.querySelectorAll('.user-name').forEach(el => {
            el.textContent = user.name || user.email;
        });

        // Update all user-avatar elements
        document.querySelectorAll('.user-avatar').forEach(el => {
            el.src = user.avatar || `https://ui-avatars.com/api/?name=${encodeURIComponent(user.name || 'User')}&background=4e73df&color=fff`;
        });

        // Show admin-only elements
        if (user.role === 'admin') {
            document.querySelectorAll('.admin-only').forEach(el => {
                el.style.display = '';
            });
        }

        return user;
    } catch (error) {
        console.error('Failed to load user:', error);
        // Only redirect on protected pages, suppress error toast
        if (!window.location.pathname.includes('login.html') && !window.location.pathname.includes('register.html')) {
            // Check if this is a 401 unauthorized - normal for not logged in
            if (error.message && (error.message.includes('Please log in') || error.message.includes('Unauthorized'))) {
                window.location.href = 'login.html';
                return null;
            }
            // Only show toast for actual errors, not auth failures
            if (error.message && !error.message.includes('API call failed')) {
                if (typeof showToast === 'function') {
                    showToast('Error', error.message, 'danger');
                }
            }
            window.location.href = 'login.html';
        }
        return null;
    }
}

// Initialize sidebar toggle and dark mode
document.addEventListener('DOMContentLoaded', function() {
    const toggleBtn = document.getElementById('toggleSidebar');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function() {
            document.getElementById('sidebar').classList.toggle('collapsed');
            document.getElementById('mainContent').classList.toggle('expanded');
        });
    }

    // Dark mode toggle
    const darkModeBtn = document.getElementById('darkModeToggle');
    if (darkModeBtn) {
        darkModeBtn.addEventListener('click', function() {
            const html = document.documentElement;
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', newTheme);
            safeStorage.setItem('theme', newTheme);
            const icon = this.querySelector('i');
            if (icon) {
                if (newTheme === 'dark') {
                    icon.classList.remove('fa-moon');
                    icon.classList.add('fa-sun');
                } else {
                    icon.classList.remove('fa-sun');
                    icon.classList.add('fa-moon');
                }
            }
        });
    }

    // Load saved theme
    const savedTheme = safeStorage.getItem('theme');
    if (savedTheme) {
        document.documentElement.setAttribute('data-theme', savedTheme);
        const icon = document.querySelector('#darkModeToggle i');
        if (icon && savedTheme === 'dark') {
            icon.classList.remove('fa-moon');
            icon.classList.add('fa-sun');
        }
    }

    // Mobile overlay handling
    const overlay = document.getElementById('overlay');
    if (overlay) {
        overlay.addEventListener('click', function() {
            document.getElementById('sidebar').classList.remove('show');
            overlay.classList.remove('show');
        });
    }
});