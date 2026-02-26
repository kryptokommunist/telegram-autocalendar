// Telegram Auto-Calendar Frontend JavaScript

let currentCategoryId = null;
let eventsData = [];

// ============ API Functions ============

async function fetchAPI(endpoint, options = {}) {
    try {
        const response = await fetch(endpoint, options);
        return await response.json();
    } catch (error) {
        console.error(`API error (${endpoint}):`, error);
        return null;
    }
}

// ============ Events ============

async function loadEvents(filters = {}) {
    const loading = document.getElementById('loading');
    const grid = document.getElementById('events-grid');
    const noEvents = document.getElementById('no-events');

    if (!grid) return;

    loading.style.display = 'block';
    grid.innerHTML = '';
    noEvents.style.display = 'none';

    const params = new URLSearchParams();
    if (filters.category_id) params.append('category_id', filters.category_id);
    if (filters.date_from) params.append('date_from', filters.date_from);
    if (filters.date_to) params.append('date_to', filters.date_to);
    if (filters.chat_id) params.append('chat_id', filters.chat_id);
    if (filters.price_type) params.append('price_type', filters.price_type);

    const events = await fetchAPI(`/api/events?${params.toString()}`);
    loading.style.display = 'none';

    if (!events || events.length === 0) {
        noEvents.style.display = 'block';
        updateEventsCount(0);
        return;
    }

    eventsData = events;
    updateEventsCount(events.length);

    events.forEach(event => {
        grid.appendChild(createEventCard(event));
    });
}

function createEventCard(event) {
    const card = document.createElement('div');
    card.className = 'event-card';
    card.onclick = () => showEventModal(event);

    const imageHtml = event.image_path
        ? `<img src="${event.image_path}" alt="${escapeHtml(event.event_title)}" class="event-card-image">`
        : `<div class="event-card-placeholder">📅</div>`;

    const dateStr = event.event_start
        ? formatDate(event.event_start)
        : 'Date TBD';

    const timeStr = event.event_start
        ? formatTime(event.event_start)
        : '';

    const priceClass = event.ticket_price && !event.ticket_price.toLowerCase().includes('free')
        ? 'paid'
        : '';

    const priceText = event.ticket_price || 'Free';

    card.innerHTML = `
        ${imageHtml}
        <div class="event-card-content">
            ${event.category_name ? `<span class="event-card-category">${escapeHtml(event.category_name)}</span>` : ''}
            <h3 class="event-card-title">${escapeHtml(event.event_title)}</h3>
            <div class="event-card-meta">
                <div class="event-card-meta-item">
                    <span class="event-card-meta-icon">📅</span>
                    <span>${dateStr}</span>
                </div>
                ${timeStr ? `
                <div class="event-card-meta-item">
                    <span class="event-card-meta-icon">🕐</span>
                    <span>${timeStr}</span>
                </div>
                ` : ''}
                ${event.event_location ? `
                <div class="event-card-meta-item">
                    <span class="event-card-meta-icon">📍</span>
                    <span>${escapeHtml(truncate(event.event_location, 40))}</span>
                </div>
                ` : ''}
            </div>
            <div class="event-card-footer">
                <span class="event-card-source">${escapeHtml(event.chat_name || 'Unknown')}</span>
                <span class="event-card-price ${priceClass}">${escapeHtml(priceText)}</span>
            </div>
        </div>
    `;

    return card;
}

function showEventModal(event) {
    const modal = document.getElementById('event-modal');
    const body = document.getElementById('modal-body');

    if (!modal || !body) {
        // Fallback to event page
        window.location.href = `/event/${event.id}`;
        return;
    }

    const imageHtml = event.image_path
        ? `<img src="${event.image_path}" alt="${escapeHtml(event.event_title)}" style="width:100%;border-radius:8px;margin-bottom:1rem;">`
        : '';

    body.innerHTML = `
        ${imageHtml}
        ${event.category_name ? `<span class="category-badge">${escapeHtml(event.category_name)}</span>` : ''}
        <h2 style="margin:0.5rem 0 1rem;font-size:1.5rem;">${escapeHtml(event.event_title)}</h2>

        <div style="margin-bottom:1.5rem;">
            ${event.event_start ? `
            <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem;">
                <span>📅</span>
                <span>${formatDate(event.event_start)} ${formatTime(event.event_start)}</span>
            </div>
            ` : ''}
            ${event.event_location ? `
            <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem;">
                <span>📍</span>
                <span>${escapeHtml(event.event_location)}</span>
            </div>
            ` : ''}
            ${event.ticket_price ? `
            <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem;">
                <span>🎟️</span>
                <span>${escapeHtml(event.ticket_price)}</span>
            </div>
            ` : ''}
            ${event.organizer ? `
            <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem;">
                <span>👤</span>
                <span>${escapeHtml(event.organizer)}</span>
            </div>
            ` : ''}
        </div>

        ${event.event_description ? `
        <p style="color:var(--text-secondary);margin-bottom:1rem;">${escapeHtml(event.event_description)}</p>
        ` : ''}

        ${event.event_link ? `
        <a href="${escapeHtml(event.event_link)}" target="_blank" rel="noopener" class="btn btn-primary" style="margin-bottom:1rem;">
            Register / More Info →
        </a>
        ` : ''}

        <div style="margin-top:1.5rem;padding-top:1rem;border-top:1px solid var(--border);">
            <a href="/event/${event.id}" class="btn btn-secondary">View Full Details</a>
        </div>
    `;

    modal.style.display = 'flex';
}

function closeModal() {
    const modal = document.getElementById('event-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});

function updateEventsCount(count) {
    const countEl = document.getElementById('events-count');
    if (countEl) {
        countEl.textContent = `${count} event${count !== 1 ? 's' : ''}`;
    }
}

// ============ Categories ============

async function loadCategories() {
    const container = document.getElementById('categories-list');
    if (!container) return;

    const categories = await fetchAPI('/api/categories');
    if (!categories) return;

    // Add "All" option
    const allItem = document.createElement('div');
    allItem.className = `category-item ${currentCategoryId === null ? 'active' : ''}`;
    allItem.onclick = () => selectCategory(null);
    allItem.innerHTML = `
        <span class="category-name">All Events</span>
        <span class="category-count">${categories.reduce((sum, c) => sum + (c.event_count || 0), 0)}</span>
    `;
    container.appendChild(allItem);

    categories.forEach(cat => {
        if (cat.event_count > 0) {
            const item = document.createElement('div');
            item.className = `category-item ${currentCategoryId === cat.id ? 'active' : ''}`;
            item.onclick = () => selectCategory(cat.id);
            item.innerHTML = `
                <span class="category-name">${escapeHtml(cat.name)}</span>
                <span class="category-count">${cat.event_count}</span>
            `;
            container.appendChild(item);
        }
    });
}

function selectCategory(categoryId) {
    currentCategoryId = categoryId;

    // Update active state
    document.querySelectorAll('.category-item').forEach((item, index) => {
        if ((categoryId === null && index === 0) ||
            (item.querySelector('.category-name')?.textContent === getSelectedCategoryName(categoryId))) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

    applyFilters();
}

function getSelectedCategoryName(categoryId) {
    // This is a simplified version - you might want to store categories globally
    return categoryId === null ? 'All Events' : '';
}

// ============ Groups ============

async function loadGroups() {
    const select = document.getElementById('group-filter');
    if (!select) return;

    const groups = await fetchAPI('/api/groups');
    if (!groups) return;

    groups.forEach(group => {
        const option = document.createElement('option');
        option.value = group.chat_id;
        option.textContent = group.chat_name || `Group ${group.chat_id}`;
        select.appendChild(option);
    });
}

// ============ Filters ============

function applyFilters() {
    const filters = {
        category_id: currentCategoryId,
        date_from: document.getElementById('date-from')?.value || null,
        date_to: document.getElementById('date-to')?.value || null,
        chat_id: document.getElementById('group-filter')?.value || null,
        price_type: document.getElementById('price-filter')?.value || null,
    };

    loadEvents(filters);
}

function clearFilters() {
    currentCategoryId = null;

    const dateFrom = document.getElementById('date-from');
    const dateTo = document.getElementById('date-to');
    const groupFilter = document.getElementById('group-filter');
    const priceFilter = document.getElementById('price-filter');

    if (dateFrom) dateFrom.value = '';
    if (dateTo) dateTo.value = '';
    if (groupFilter) groupFilter.value = '';
    if (priceFilter) priceFilter.value = '';

    // Update category active state
    document.querySelectorAll('.category-item').forEach((item, index) => {
        item.classList.toggle('active', index === 0);
    });

    loadEvents();
}

// ============ Sync ============

async function triggerSync() {
    const btn = document.getElementById('sync-btn');
    if (!btn) return;

    btn.disabled = true;
    btn.querySelector('.sync-text').textContent = 'Syncing...';

    const result = await fetchAPI('/api/sync', { method: 'POST' });

    if (result?.error) {
        alert(result.error);
        btn.disabled = false;
        btn.querySelector('.sync-text').textContent = 'Sync Now';
    } else {
        // Start polling for status
        pollSyncStatus();
    }
}

async function updateSyncStatus() {
    const btn = document.getElementById('sync-btn');
    const statusEl = document.getElementById('sync-status');

    if (!btn || !statusEl) return;

    const status = await fetchAPI('/api/sync/status');
    if (!status) return;

    if (status.status === 'running') {
        btn.disabled = true;
        btn.querySelector('.sync-text').textContent = 'Syncing...';
        statusEl.textContent = `${status.groups_scanned}/${status.groups_total} groups, ${status.events_found} events`;
    } else {
        btn.disabled = false;
        btn.querySelector('.sync-text').textContent = 'Sync Now';

        if (status.completed_at) {
            const lastSync = new Date(status.completed_at);
            statusEl.textContent = `Last sync: ${formatRelativeTime(lastSync)}`;
        } else {
            statusEl.textContent = '';
        }
    }
}

function pollSyncStatus() {
    const interval = setInterval(async () => {
        const status = await fetchAPI('/api/sync/status');

        updateSyncStatus();

        if (status?.status !== 'running') {
            clearInterval(interval);
            loadEvents(); // Reload events after sync completes
        }
    }, 2000);
}

// ============ Utilities ============

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function truncate(text, maxLength) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });
}

function formatTime(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    });
}

function formatRelativeTime(date) {
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
}
