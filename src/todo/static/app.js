const API_BASE = '/api';
const DEMO_USER = {
    username: 'demo_user',
    password: 'demo_password_123'
};

// State
let state = {
    tasks: [],
    filter: 'all',
    token: localStorage.getItem('auth_token')
};

// DOM Elements
const taskInput = document.getElementById('task-input');
const addBtn = document.getElementById('add-btn');
const aiProcessBtn = document.getElementById('ai-process-btn');
const tasksList = document.getElementById('tasks-list');
const filterBtns = document.querySelectorAll('.filter-btn');

// Initialization
document.addEventListener('DOMContentLoaded', async () => {
    await ensureAuth();
    setupEventListeners();
    fetchTasks();
});

// Authentication
async function ensureAuth() {
    if (!state.token) {
        await performDemoLogin();
    } else {
        // Verify token is still valid
        try {
            const response = await fetch(`${API_BASE}/auth/me`, {
                headers: { 'Authorization': `Bearer ${state.token}` }
            });
            if (!response.ok) {
                await performDemoLogin();
            }
        } catch (error) {
            await performDemoLogin();
        }
    }
}

async function performDemoLogin() {
    try {
        // Try login first
        let response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(DEMO_USER)
        });

        if (response.status === 401) {
            // User might not exist, try registering
            const regResponse = await fetch(`${API_BASE}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(DEMO_USER)
            });
            
            if (!regResponse.ok && regResponse.status !== 400) {
                throw new Error('Registration failed');
            }

            // Retry login
            response = await fetch(`${API_BASE}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(DEMO_USER)
            });
        }

        if (!response.ok) throw new Error('Login failed');

        const data = await response.json();
        state.token = data.access_token;
        localStorage.setItem('auth_token', state.token);
    } catch (error) {
        console.error('Auth error:', error);
        showError('Authentication failed. Please refresh.');
    }
}

// Event Listeners
function setupEventListeners() {
    addBtn.addEventListener('click', handleAddTask);
    taskInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleAddTask();
    });
    
    aiProcessBtn.addEventListener('click', handleAIProcess);

    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.filter = btn.dataset.filter;
            renderTasks();
        });
    });
}

// API Interactions
async function fetchTasks() {
    try {
        const response = await fetch(`${API_BASE}/tasks`, {
            headers: { 'Authorization': `Bearer ${state.token}` }
        });
        if (!response.ok) throw new Error('Failed to fetch tasks');
        
        const data = await response.json();
        state.tasks = data.data; // Assuming response structure { data: [...] }
        renderTasks();
    } catch (error) {
        console.error('Fetch error:', error);
        showError('Failed to load tasks');
    }
}

async function handleAddTask() {
    const title = taskInput.value.trim();
    if (!title) return;

    try {
        const response = await fetch(`${API_BASE}/tasks`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${state.token}`
            },
            body: JSON.stringify({
                title: title,
                status: 'todo',
                urgency: 1 // Default urgency
            })
        });

        if (!response.ok) throw new Error('Failed to create task');

        taskInput.value = '';
        await fetchTasks();
    } catch (error) {
        console.error('Create error:', error);
        showError('Failed to create task');
    }
}

async function handleAIProcess() {
    const text = taskInput.value.trim();
    if (!text) {
        alert('Please enter a request for the AI (e.g., "Plan a party for Friday")');
        return;
    }

    const originalBtnText = aiProcessBtn.innerHTML;
    aiProcessBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';
    aiProcessBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/tasks/process`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${state.token}`
            },
            body: JSON.stringify({ text: text })
        });

        if (!response.ok) throw new Error('AI processing failed');

        const data = await response.json();
        // Show result message
        if (data.message) {
            alert(data.message);
        }
        
        taskInput.value = '';
        await fetchTasks();
    } catch (error) {
        console.error('AI error:', error);
        showError('AI processing failed');
    } finally {
        aiProcessBtn.innerHTML = originalBtnText;
        aiProcessBtn.disabled = false;
    }
}

async function toggleTask(id, completed) {
    try {
        if (completed) {
            await fetch(`${API_BASE}/tasks/${id}/complete`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${state.token}` }
            });
        } else {
            // Re-open task (if API supports it, otherwise just update status)
            await fetch(`${API_BASE}/tasks/${id}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${state.token}`
                },
                body: JSON.stringify({ status: 'todo' })
            });
        }
        await fetchTasks();
    } catch (error) {
        console.error('Toggle error:', error);
        showError('Failed to update task');
    }
}

async function deleteTask(id) {
    if (!confirm('Are you sure you want to delete this task?')) return;

    try {
        await fetch(`${API_BASE}/tasks/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${state.token}` }
        });
        await fetchTasks();
    } catch (error) {
        console.error('Delete error:', error);
        showError('Failed to delete task');
    }
}

// Rendering
function renderTasks() {
    tasksList.innerHTML = '';
    
    const filteredTasks = state.tasks.filter(task => {
        if (state.filter === 'completed') return task.status === 'completed';
        if (state.filter === 'pending') return task.status !== 'completed';
        return true;
    });

    if (filteredTasks.length === 0) {
        tasksList.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-clipboard-list"></i>
                <p>No tasks found</p>
            </div>
        `;
        return;
    }

    filteredTasks.forEach(task => {
        const isCompleted = task.status === 'completed';
        const taskEl = document.createElement('div');
        taskEl.className = `task-item ${isCompleted ? 'completed' : ''}`;
        
        taskEl.innerHTML = `
            <input type="checkbox" class="task-checkbox" 
                ${isCompleted ? 'checked' : ''} 
                onchange="toggleTask(${task.id}, this.checked)">
            
            <div class="task-content">
                <div class="task-title">${escapeHtml(task.title)}</div>
                ${task.description ? `<div class="task-meta">${escapeHtml(task.description)}</div>` : ''}
                <div class="task-meta">
                    ${task.due_date ? `<span><i class="fa-regular fa-calendar"></i> ${new Date(task.due_date).toLocaleDateString()}</span>` : ''}
                    ${task.urgency > 1 ? `<span style="color: var(--danger-color)"><i class="fa-solid fa-fire"></i> High Priority</span>` : ''}
                </div>
            </div>

            <div class="task-actions">
                <button class="action-btn delete" onclick="deleteTask(${task.id})">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
        `;
        
        tasksList.appendChild(taskEl);
    });
}

// Utilities
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showError(message) {
    // Simple toast or alert could go here
    console.error(message);
}

// Expose functions to window for inline handlers
window.toggleTask = toggleTask;
window.deleteTask = deleteTask;
