// Telegram Auto-Calendar Frontend JavaScript

let currentCategoryId = null;
let eventsData = [];
let allCities = [];
let allCountries = [];

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
    if (filters.city) params.append('city', filters.city);
    if (filters.country) params.append('country', filters.country);
    if (filters.max_price) params.append('max_price', filters.max_price);

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

    // Share button for card
    const shareBtn = document.createElement('button');
    shareBtn.className = 'event-card-share';
    shareBtn.innerHTML = '↗';
    shareBtn.title = 'Share event';
    shareBtn.onclick = (e) => shareEvent(event, e);
    card.appendChild(shareBtn);

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

    // Build location string with city/country
    let locationStr = '';
    if (event.city && event.country) {
        locationStr = `${event.city}, ${event.country}`;
    } else if (event.city) {
        locationStr = event.city;
    } else if (event.country) {
        locationStr = event.country;
    } else if (event.event_location) {
        locationStr = truncate(event.event_location, 40);
    }

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
                ${locationStr ? `
                <div class="event-card-meta-item">
                    <span class="event-card-meta-icon">📍</span>
                    <span>${escapeHtml(locationStr)}</span>
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
        window.location.href = `/event/${event.id}`;
        return;
    }

    // Build location string
    let locationStr = '';
    if (event.city && event.country) {
        locationStr = `${event.city}, ${event.country}`;
    } else if (event.city) {
        locationStr = event.city;
    } else if (event.country) {
        locationStr = event.country;
    }
    if (event.event_location) {
        locationStr = locationStr ? `${event.event_location} (${locationStr})` : event.event_location;
    }

    const imageHtml = event.image_path
        ? `<img src="${event.image_path}" alt="${escapeHtml(event.event_title)}" class="modal-image">`
        : '';

    body.innerHTML = `
        ${imageHtml}
        <div class="modal-header">
            ${event.category_name ? `<span class="category-badge">${escapeHtml(event.category_name)}</span>` : ''}
            <h2 style="margin:0.5rem 0 0;font-size:1.5rem;font-weight:700;">${escapeHtml(event.event_title)}</h2>
        </div>

        <div class="modal-meta">
            ${event.event_start ? `
            <div class="modal-meta-item">
                <span class="modal-meta-icon">📅</span>
                <span><strong>${formatDate(event.event_start)}</strong> at ${formatTime(event.event_start)}</span>
            </div>
            ` : ''}
            ${locationStr ? `
            <div class="modal-meta-item">
                <span class="modal-meta-icon">📍</span>
                <span>${escapeHtml(locationStr)}</span>
            </div>
            ` : ''}
            ${event.ticket_price ? `
            <div class="modal-meta-item">
                <span class="modal-meta-icon">🎟️</span>
                <span>${escapeHtml(event.ticket_price)}</span>
            </div>
            ` : ''}
            ${event.organizer ? `
            <div class="modal-meta-item">
                <span class="modal-meta-icon">👤</span>
                <span>${escapeHtml(event.organizer)}</span>
            </div>
            ` : ''}
            <div class="modal-meta-item">
                <span class="modal-meta-icon">💬</span>
                <span>From: ${escapeHtml(event.chat_name || 'Unknown Group')}</span>
            </div>
        </div>

        ${event.event_description ? `
        <div style="padding:0 1.5rem;">
            <p style="color:var(--text-secondary);line-height:1.6;">${escapeHtml(event.event_description)}</p>
        </div>
        ` : ''}

        ${event.event_link ? `
        <div class="modal-iframe-container">
            <div style="padding:0.75rem 1rem;background:var(--surface);border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;">
                <span style="font-size:0.875rem;color:var(--text-muted);">Event Page Preview</span>
                <a href="${escapeHtml(event.event_link)}" target="_blank" rel="noopener" style="font-size:0.75rem;color:var(--primary);">
                    Open in new tab ↗
                </a>
            </div>
            <iframe src="${escapeHtml(event.event_link)}" class="modal-iframe" sandbox="allow-scripts allow-same-origin"></iframe>
        </div>
        ` : ''}

        <div class="modal-actions">
            ${event.event_link ? `
            <a href="${escapeHtml(event.event_link)}" target="_blank" rel="noopener" class="btn btn-primary">
                Register / More Info →
            </a>
            ` : ''}
            <a href="/event/${event.id}" class="btn btn-secondary">View Full Details</a>
            <a href="https://t.me/c/${String(event.chat_id).replace('-100', '')}/${event.message_id}"
               target="_blank" rel="noopener" class="btn btn-outline" title="View original message in Telegram">
                <span>✈️</span> Telegram
            </a>
            <div class="share-container">
                <button class="share-btn" onclick="shareEvent(window._currentModalEvent, event)">
                    <span>↗</span> Share
                </button>
            </div>
        </div>
    `;

    // Store current event for share button
    window._currentModalEvent = event;

    // Animate modal open
    modal.style.display = 'flex';
    requestAnimationFrame(() => {
        modal.classList.add('active');
    });
}

function closeModal() {
    const modal = document.getElementById('event-modal');
    if (modal) {
        modal.classList.remove('active');
        setTimeout(() => {
            modal.style.display = 'none';
        }, 400);
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

// ============ Locations ============

async function loadLocations() {
    const data = await fetchAPI('/api/locations');
    if (!data) return;

    allCities = data.cities || [];
    allCountries = data.countries || [];

    // Populate country dropdown
    const countrySelect = document.getElementById('country-filter');
    if (countrySelect) {
        allCountries.forEach(country => {
            const option = document.createElement('option');
            option.value = country;
            option.textContent = country;
            countrySelect.appendChild(option);
        });
    }

    // Populate city dropdown with all cities initially
    populateCityDropdown(allCities);
}

function populateCityDropdown(cities) {
    const citySelect = document.getElementById('city-filter');
    if (!citySelect) return;

    // Clear existing options except the first one
    while (citySelect.options.length > 1) {
        citySelect.remove(1);
    }

    cities.forEach(city => {
        const option = document.createElement('option');
        option.value = city;
        option.textContent = city;
        citySelect.appendChild(option);
    });
}

function loadCitiesForCountry() {
    const countrySelect = document.getElementById('country-filter');
    const selectedCountry = countrySelect?.value;

    if (!selectedCountry) {
        // Show all cities if no country selected
        populateCityDropdown(allCities);
    } else {
        // For now, show all cities - we'd need backend support for filtering
        // In a full implementation, we'd filter cities by country
        populateCityDropdown(allCities);
    }
}

// ============ Filters ============

function applyFilters() {
    const filters = {
        category_id: currentCategoryId,
        date_from: document.getElementById('date-from')?.value || null,
        date_to: document.getElementById('date-to')?.value || null,
        chat_id: document.getElementById('group-filter')?.value || null,
        price_type: document.getElementById('price-filter')?.value || null,
        max_price: document.getElementById('max-price')?.value || null,
        city: document.getElementById('city-filter')?.value || null,
        country: document.getElementById('country-filter')?.value || null,
    };

    loadEvents(filters);
}

function clearFilters() {
    currentCategoryId = null;

    const dateFrom = document.getElementById('date-from');
    const dateTo = document.getElementById('date-to');
    const groupFilter = document.getElementById('group-filter');
    const priceFilter = document.getElementById('price-filter');
    const maxPrice = document.getElementById('max-price');
    const cityFilter = document.getElementById('city-filter');
    const countryFilter = document.getElementById('country-filter');

    if (dateFrom) dateFrom.value = '';
    if (dateTo) dateTo.value = '';
    if (groupFilter) groupFilter.value = '';
    if (priceFilter) priceFilter.value = '';
    if (maxPrice) maxPrice.value = '';
    if (cityFilter) cityFilter.value = '';
    if (countryFilter) countryFilter.value = '';

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

// ============ Share Functionality ============

function buildShareText(event) {
    let text = `${event.event_title}`;

    if (event.event_start) {
        text += `\n📅 ${formatDate(event.event_start)}`;
        const time = formatTime(event.event_start);
        if (time) text += ` at ${time}`;
    }

    if (event.city || event.event_location) {
        text += `\n📍 ${event.city || event.event_location}`;
    }

    if (event.ticket_price) {
        text += `\n🎟️ ${event.ticket_price}`;
    }

    return text;
}

function getShareUrl(event) {
    // Use event link if available, otherwise link to our event page
    if (event.event_link) {
        return event.event_link;
    }
    return `${window.location.origin}/event/${event.id}`;
}

async function shareEvent(event, e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }

    const shareText = buildShareText(event);
    const shareUrl = getShareUrl(event);

    // Try native Web Share API first (works great on mobile)
    if (navigator.share) {
        try {
            await navigator.share({
                title: event.event_title,
                text: shareText,
                url: shareUrl,
            });
            return;
        } catch (err) {
            // User cancelled or error, fall through to dropdown
            if (err.name === 'AbortError') return;
        }
    }

    // Show share dropdown
    showShareDropdown(event, e?.target);
}

function showShareDropdown(event, targetBtn) {
    // Remove any existing dropdowns
    document.querySelectorAll('.share-dropdown').forEach(d => d.remove());

    const shareText = buildShareText(event);
    const shareUrl = getShareUrl(event);
    const encodedText = encodeURIComponent(shareText);
    const encodedUrl = encodeURIComponent(shareUrl);
    const encodedTitle = encodeURIComponent(event.event_title);
    const fullText = encodeURIComponent(`${shareText}\n\n${shareUrl}`);

    const dropdown = document.createElement('div');
    dropdown.className = 'share-dropdown';
    dropdown.innerHTML = `
        <div class="share-dropdown-title">Share via</div>
        <div class="share-grid">
            <a href="https://wa.me/?text=${fullText}" target="_blank" rel="noopener" class="share-option" onclick="event.stopPropagation()">
                <span class="share-icon whatsapp">💬</span>
                <span class="share-label">WhatsApp</span>
            </a>
            <a href="https://t.me/share/url?url=${encodedUrl}&text=${encodedText}" target="_blank" rel="noopener" class="share-option" onclick="event.stopPropagation()">
                <span class="share-icon telegram">✈️</span>
                <span class="share-label">Telegram</span>
            </a>
            <a href="https://signal.me/#p/?text=${fullText}" target="_blank" rel="noopener" class="share-option" onclick="event.stopPropagation()">
                <span class="share-icon signal">💙</span>
                <span class="share-label">Signal</span>
            </a>
            <a href="sms:?body=${fullText}" class="share-option" onclick="event.stopPropagation()">
                <span class="share-icon sms">📱</span>
                <span class="share-label">SMS</span>
            </a>
            <a href="mailto:?subject=${encodedTitle}&body=${fullText}" class="share-option" onclick="event.stopPropagation()">
                <span class="share-icon email">📧</span>
                <span class="share-label">Email</span>
            </a>
            <a href="https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}&quote=${encodedText}" target="_blank" rel="noopener" class="share-option" onclick="event.stopPropagation()">
                <span class="share-icon facebook">📘</span>
                <span class="share-label">Facebook</span>
            </a>
            <a href="https://twitter.com/intent/tweet?text=${encodedText}&url=${encodedUrl}" target="_blank" rel="noopener" class="share-option" onclick="event.stopPropagation()">
                <span class="share-icon twitter">🐦</span>
                <span class="share-label">Twitter</span>
            </a>
            <button class="share-option" onclick="copyShareLink('${shareUrl}', '${shareText.replace(/'/g, "\\'")}', this); event.stopPropagation()">
                <span class="share-icon copy">📋</span>
                <span class="share-label">Copy Link</span>
            </button>
        </div>
    `;

    // Position dropdown
    if (targetBtn) {
        const container = targetBtn.closest('.share-container') || targetBtn.parentElement;
        container.style.position = 'relative';
        container.appendChild(dropdown);
    } else {
        // Append to body and position in center
        dropdown.style.position = 'fixed';
        dropdown.style.top = '50%';
        dropdown.style.left = '50%';
        dropdown.style.transform = 'translate(-50%, -50%) scale(0.9)';
        dropdown.style.bottom = 'auto';
        document.body.appendChild(dropdown);
    }

    // Animate in
    requestAnimationFrame(() => {
        dropdown.classList.add('active');
    });

    // Close on outside click
    const closeDropdown = (e) => {
        if (!dropdown.contains(e.target)) {
            dropdown.classList.remove('active');
            setTimeout(() => dropdown.remove(), 250);
            document.removeEventListener('click', closeDropdown);
        }
    };

    setTimeout(() => {
        document.addEventListener('click', closeDropdown);
    }, 100);
}

async function copyShareLink(url, text, btn) {
    const fullText = `${text}\n\n${url}`;

    try {
        await navigator.clipboard.writeText(fullText);

        // Visual feedback
        btn.classList.add('copied');
        btn.querySelector('.share-label').textContent = 'Copied!';

        setTimeout(() => {
            btn.classList.remove('copied');
            btn.querySelector('.share-label').textContent = 'Copy Link';
        }, 2000);
    } catch (err) {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = fullText;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);

        btn.classList.add('copied');
        btn.querySelector('.share-label').textContent = 'Copied!';
        setTimeout(() => {
            btn.classList.remove('copied');
            btn.querySelector('.share-label').textContent = 'Copy Link';
        }, 2000);
    }
}
