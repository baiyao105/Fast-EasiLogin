const API_BASE = '';

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    const mergedOptions = { ...defaultOptions, ...options };
    if (mergedOptions.body && typeof mergedOptions.body === 'object') {
        mergedOptions.body = JSON.stringify(mergedOptions.body);
    }
    try {
        const response = await fetch(url, mergedOptions);
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail?.message || data.message || '请求失败');
        }
        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

function renderUserCard(user) {
    const initial = (user.user_nickname || user.user_id || 'U').charAt(0).toUpperCase();
    const statusClass = user.active ? 'active' : 'inactive';
    const statusText = user.active ? '已启用' : '已禁用';
    const cardClass = user.active ? '' : 'disabled';

    return `
        <div class="user-card ${cardClass}" data-user-id="${user.user_id}">
            <div class="user-header">
                <div class="user-avatar">
                    ${user.head_img ? `<img src="${user.head_img}" alt="${user.user_nickname}" onerror="this.style.display='none';this.parentElement.textContent='${initial}'">` : initial}
                </div>
                <div class="user-info">
                    <div class="user-name">${user.user_nickname || user.user_id}</div>
                    <div class="user-phone">${user.phone || '未设置手机号'}</div>
                </div>
                <span class="user-status ${statusClass}">${statusText}</span>
            </div>
            <div class="user-actions">
                <button class="btn btn-secondary btn-sm" onclick="editUser('${user.user_id}')">编辑</button>
                <button class="btn btn-danger btn-sm" onclick="deleteUser('${user.user_id}')">删除</button>
            </div>
        </div>
    `;
}

async function loadUsers() {
    const userList = document.getElementById('user-list');
    userList.innerHTML = '<div class="loading">加载中...</div>';

    try {
        const response = await apiRequest('/webui/users');
        const users = response.data || [];

        if (users.length === 0) {
            userList.innerHTML = `
                <div class="empty-state">
                    <p>暂无用户数据</p>
                    <button class="btn btn-primary" onclick="openAddUserModal()">添加第一个用户</button>
                </div>
            `;
        } else {
            userList.innerHTML = users.map(renderUserCard).join('');
        }

        document.getElementById('user-count').textContent = users.length;
    } catch (error) {
        userList.innerHTML = `<div class="empty-state"><p>加载失败: ${error.message}</p></div>`;
        showToast('加载用户列表失败: ' + error.message, 'error');
    }
}

async function loadSettings() {
    try {
        const response = await apiRequest('/webui/settings');
        const settings = response.data || {};

        document.getElementById('port').value = settings.Global?.port || 24300;
        document.getElementById('webui_port').value = settings.Global?.webui_port || 24301;
        document.getElementById('token_check_interval').value = settings.Global?.token_check_interval || 300;
        document.getElementById('token_ttl').value = settings.Global?.token_ttl || 60;
        document.getElementById('cache_max_entries').value = settings.Global?.cache_max_entries || 512;
        document.getElementById('enable_eventlog').checked = settings.Global?.enable_eventlog !== false;
        document.getElementById('auto_restart_on_crash').checked = settings.Global?.auto_restart_on_crash !== false;
        document.getElementById('restart_delay_seconds').value = settings.Global?.restart_delay_seconds || 3;
        document.getElementById('enable_password_error_disable').checked = settings.Global?.enable_password_error_disable || false;

        const port = settings.Global?.port || 24300;
        document.getElementById('service-url').textContent = `http://127.0.0.1:${port}`;
    } catch (error) {
        showToast('加载设置失败: ' + error.message, 'error');
    }
}

function openAddUserModal() {
    document.getElementById('modal-title').textContent = '添加用户';
    document.getElementById('user-form').reset();
    document.getElementById('user-id').value = '';
    document.getElementById('active').checked = true;
    document.getElementById('user-modal').classList.add('show');
}

async function editUser(userId) {
    try {
        const response = await apiRequest(`/webui/users/${userId}`);
        const user = response.data;

        document.getElementById('modal-title').textContent = '编辑用户';
        document.getElementById('user-id').value = user.user_id;
        document.getElementById('phone').value = user.phone || '';
        document.getElementById('password').value = user.password || '';
        document.getElementById('user_nickname').value = user.user_nickname || '';
        document.getElementById('user_realname').value = user.user_realname || '';
        document.getElementById('active').checked = user.active !== false;
        document.getElementById('user-modal').classList.add('show');
    } catch (error) {
        showToast('加载用户信息失败: ' + error.message, 'error');
    }
}

function closeModal() {
    document.getElementById('user-modal').classList.remove('show');
}

async function saveUser(event) {
    event.preventDefault();

    const userId = document.getElementById('user-id').value;
    const userData = {
        phone: document.getElementById('phone').value,
        password: document.getElementById('password').value,
        user_nickname: document.getElementById('user_nickname').value,
        user_realname: document.getElementById('user_realname').value,
        active: document.getElementById('active').checked,
    };

    try {
        if (userId) {
            await apiRequest(`/webui/users/${userId}`, {
                method: 'PUT',
                body: userData,
            });
            showToast('用户已更新');
        } else {
            await apiRequest('/webui/users', {
                method: 'POST',
                body: userData,
            });
            showToast('用户已创建');
        }
        closeModal();
        loadUsers();
    } catch (error) {
        showToast('保存失败: ' + error.message, 'error');
    }
}

async function deleteUser(userId) {
    if (!confirm('确定要删除此用户吗？')) {
        return;
    }

    try {
        await apiRequest(`/webui/users/${userId}`, {
            method: 'DELETE',
        });
        showToast('用户已删除');
        loadUsers();
    } catch (error) {
        showToast('删除失败: ' + error.message, 'error');
    }
}

async function saveSettings(event) {
    event.preventDefault();

    const settings = {
        Global: {
            port: parseInt(document.getElementById('port').value) || 24300,
            webui_port: parseInt(document.getElementById('webui_port').value) || 24301,
            token_check_interval: parseInt(document.getElementById('token_check_interval').value) || 300,
            token_ttl: parseInt(document.getElementById('token_ttl').value) || 60,
            cache_max_entries: parseInt(document.getElementById('cache_max_entries').value) || 512,
            enable_eventlog: document.getElementById('enable_eventlog').checked,
            auto_restart_on_crash: document.getElementById('auto_restart_on_crash').checked,
            restart_delay_seconds: parseInt(document.getElementById('restart_delay_seconds').value) || 3,
            enable_password_error_disable: document.getElementById('enable_password_error_disable').checked,
        },
    };

    try {
        await apiRequest('/webui/settings', {
            method: 'PUT',
            body: settings,
        });
        showToast('设置保存成功，部分设置需要重启服务生效');
    } catch (error) {
        showToast('保存设置失败: ' + error.message, 'error');
    }
}

async function clearCache() {
    if (!confirm('确定要清除所有缓存吗？')) {
        return;
    }

    try {
        await apiRequest('/webui/cache', {
            method: 'DELETE',
        });
        showToast('缓存已清除');
    } catch (error) {
        showToast('清除缓存失败: ' + error.message, 'error');
    }
}

function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    document.getElementById(`${tabName}-tab`).classList.add('active');
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            switchTab(btn.dataset.tab);
        });
    });

    document.getElementById('add-user-btn').addEventListener('click', openAddUserModal);
    document.getElementById('user-form').addEventListener('submit', saveUser);
    document.getElementById('settings-form').addEventListener('submit', saveSettings);
    document.getElementById('modal-close').addEventListener('click', closeModal);
    document.getElementById('modal-cancel').addEventListener('click', closeModal);
    document.getElementById('refresh-status-btn').addEventListener('click', loadUsers);
    document.getElementById('clear-cache-btn').addEventListener('click', clearCache);

    document.getElementById('user-modal').addEventListener('click', (e) => {
        if (e.target.id === 'user-modal') {
            closeModal();
        }
    });

    loadUsers();
    loadSettings();
});
