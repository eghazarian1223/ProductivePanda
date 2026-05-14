let currentFilter = 'all';

document.addEventListener('DOMContentLoaded', () => {
    loadTasks();

    document.getElementById('addTaskForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const title = document.getElementById('taskTitle').value.trim();
        const priority = parseInt(document.getElementById('taskPriority').value);
        if (!title) return;
        await addTask(title, priority);
        document.getElementById('taskTitle').value = '';
    });

    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            renderTasks(window._tasks || []);
        });
    });
});

async function loadTasks() {
    const res = await fetch('/tasks/');
    const tasks = await res.json();
    window._tasks = tasks;
    renderTasks(tasks);
}

function renderTasks(tasks) {
    const list = document.getElementById('taskList');
    list.innerHTML = '';
    const filtered = tasks.filter(t => {
        if (currentFilter === 'pending') return !t.completed;
        if (currentFilter === 'done') return t.completed;
        return true;
    });
    if (filtered.length === 0) {
        list.innerHTML = '<li class="empty-msg">No tasks here.</li>';
        return;
    }
    filtered.forEach(task => list.appendChild(createTaskEl(task)));
}

function createTaskEl(task) {
    const li = document.createElement('li');
    li.className = `todo-task-item${task.completed ? ' completed' : ''}`;
    li.dataset.id = task.id;

    const priorityLabel = task.priority >= 4 ? 'High' : task.priority === 3 ? 'Medium' : 'Low';
    const priorityClass = task.priority >= 4 ? 'high' : task.priority === 3 ? 'medium' : 'low';

    li.innerHTML = `
        <button class="check-btn" title="Toggle complete">
            <i class="fas ${task.completed ? 'fa-check-circle' : 'fa-circle'}"></i>
        </button>
        <span class="task-text">${escapeHtml(task.title)}</span>
        <span class="priority-tag priority-${priorityClass}">${priorityLabel}</span>
        <button class="delete-btn" title="Delete"><i class="fas fa-trash"></i></button>
    `;

    li.querySelector('.check-btn').addEventListener('click', () => toggleTask(task.id));
    li.querySelector('.delete-btn').addEventListener('click', () => deleteTask(task.id));
    return li;
}

async function addTask(title, priority) {
    const res = await fetch('/tasks/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
        body: JSON.stringify({ title, priority })
    });
    if (res.ok) {
        const task = await res.json();
        window._tasks = [task, ...(window._tasks || [])];
        renderTasks(window._tasks);
    }
}

async function toggleTask(id) {
    const res = await fetch(`/tasks/${id}/complete`, {
        method: 'POST',
        headers: { 'X-CSRFToken': CSRF_TOKEN }
    });
    if (res.ok) {
        const updated = await res.json();
        window._tasks = window._tasks.map(t => t.id === id ? updated : t);
        renderTasks(window._tasks);
    }
}

async function deleteTask(id) {
    const res = await fetch(`/tasks/${id}`, {
        method: 'DELETE',
        headers: { 'X-CSRFToken': CSRF_TOKEN }
    });
    if (res.ok) {
        window._tasks = window._tasks.filter(t => t.id !== id);
        renderTasks(window._tasks);
    }
}

function escapeHtml(text) {
    const d = document.createElement('div');
    d.appendChild(document.createTextNode(text));
    return d.innerHTML;
}
