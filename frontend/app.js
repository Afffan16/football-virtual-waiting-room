/* ================================================================
   Football Virtual Waiting Room — Application Logic
   SPA router + API integration + dynamic UI
   ================================================================ */

// ---- Configuration ----
// Replace this with your own deployed API URL.
// For local development with SAM Local: http://127.0.0.1:3000
const API_BASE = "https://n20mxucrj4.execute-api.us-east-1.amazonaws.com/Prod";

// Demo admin login. Production should replace this with server-side auth.
const ADMIN_LOGIN_EMAIL = "admin123@gmail.com";
const ADMIN_LOGIN_PASSWORD = "admin123";

// ---- Football events catalog (hardcoded for demo, matches seed_data.py) ----
const EVENTS_CATALOG = [
    { eventId: "1001", matchName: "Manchester United vs Liverpool", stadium: "Old Trafford", capacity: 50000, startTime: "2026-07-12T15:00:00Z", status: "OPEN" },
    { eventId: "1002", matchName: "Portugal vs Argentina", stadium: "Estádio da Luz", capacity: 65000, startTime: "2026-07-15T20:00:00Z", status: "OPEN" },
    { eventId: "1003", matchName: "Real Madrid vs Barcelona", stadium: "Santiago Bernabéu", capacity: 81044, startTime: "2026-07-18T21:00:00Z", status: "OPEN" },
    { eventId: "1004", matchName: "Bayern Munich vs Dortmund", stadium: "Allianz Arena", capacity: 75000, startTime: "2026-07-20T18:30:00Z", status: "OPEN" },
    { eventId: "1005", matchName: "PSG vs Marseille", stadium: "Parc des Princes", capacity: 47929, startTime: "2026-07-22T21:00:00Z", status: "OPEN" },
    { eventId: "1006", matchName: "Chelsea vs Arsenal", stadium: "Stamford Bridge", capacity: 40343, startTime: "2026-07-25T17:30:00Z", status: "OPEN" },
];

// ---- State ----
let currentPage = "home";
let selectedEventId = null;
let adminQueueData = [];
let adminCurrentFilter = "ALL";
let currentUser = JSON.parse(sessionStorage.getItem("waitingRoomUser") || "null");
let currentAdmin = JSON.parse(sessionStorage.getItem("waitingRoomAdmin") || "null");

// ================================================================
// NAVIGATION (SPA Router)
// ================================================================

function navigate(page, eventId = null) {
    if ((page === "events" || page === "event-detail") && !currentUser) {
        page = "user-login";
        eventId = null;
    }
    if (page === "admin" && !currentAdmin) {
        page = "admin-login";
    }

    // Hide all pages
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));

    // Show target page
    const target = document.getElementById(`page-${page}`);
    if (target) {
        target.classList.add("active");
        target.style.animation = "none";
        target.offsetHeight; // trigger reflow
        target.style.animation = "";
    }

    currentPage = page;
    updateNavLinks();

    // Page-specific initialization
    switch (page) {
        case "home":
            loadHomeStats();
            break;
        case "admin":
            initAdminPage();
            break;
        case "admin-login":
            initAdminLogin();
            break;
        case "user-login":
            initUserLogin();
            break;
        case "events":
            renderEventsGrid();
            break;
        case "event-detail":
            if (eventId) {
                selectedEventId = eventId;
                initEventDetail(eventId);
            }
            break;
    }

    window.scrollTo({ top: 0, behavior: "smooth" });
}

function updateNavLinks() {
    const container = document.getElementById("nav-links");
    const links = [
        { id: "home", label: "Home", page: "home" },
        { id: "admin", label: "Admin", page: "admin" },
        { id: "events", label: "Events", page: "events" },
    ];

    container.innerHTML = links.map(l =>
        `<div class="nav-link ${currentPage === l.page ? 'active' : ''}" onclick="navigate('${l.page}')" id="nav-${l.id}">${l.label}</div>`
    ).join("");
}

function updateSessionPanels() {
    const fanId = document.getElementById("global-user-id");
    if (fanId) {
        fanId.textContent = currentUser
            ? `${currentUser.userId} - ${currentUser.email}`
            : "Assigned after login";
    }

    const adminLabel = document.getElementById("admin-session-label");
    if (adminLabel) {
        adminLabel.textContent = currentAdmin
            ? `Signed in: ${currentAdmin.email}`
            : "Not signed in";
    }
}

// ================================================================
// API HELPER
// ================================================================

async function api(method, endpoint, body = null) {
    const url = `${API_BASE}${endpoint}`;
    const headers = { "Content-Type": "application/json" };

    // Attach admin credentials for protected admin endpoints.
    if ((endpoint.startsWith("/queue/admit") || endpoint.startsWith("/queue/admin")) && currentAdmin) {
        headers["x-admin-email"] = currentAdmin.email;
        headers["x-admin-password"] = currentAdmin.password;
    }

    const opts = { method, headers };
    if (body) opts.body = JSON.stringify(body);

    try {
        const res = await fetch(url, opts);
        const data = await res.json();
        return data;
    } catch (err) {
        console.error(`API Error: ${method} ${endpoint}`, err);
        return { error: err.message };
    }
}

// ================================================================
// TOAST NOTIFICATIONS
// ================================================================

function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    const icons = { success: "✅", error: "❌", info: "ℹ️" };
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${icons[type] || "ℹ️"}</span><span>${message}</span>`;
    toast.onclick = () => toast.remove();
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = "toastOut 0.3s ease forwards";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ================================================================
// AUTH
// ================================================================

function deriveUserId(email) {
    let hash = 0;
    const normalized = email.trim().toLowerCase();
    for (let i = 0; i < normalized.length; i++) {
        hash = ((hash << 5) - hash) + normalized.charCodeAt(i);
        hash |= 0;
    }
    return `FAN-${Math.abs(hash).toString(36).toUpperCase().padStart(8, "0")}`;
}

function getCurrentUserId() {
    return currentUser?.userId || "";
}

function initUserLogin() {
    const email = document.getElementById("user-login-email");
    if (email && currentUser) email.value = currentUser.email;
    const password = document.getElementById("user-login-password");
    if (password) password.value = "";
}

function initAdminLogin() {
    const email = document.getElementById("admin-login-email");
    if (email) email.value = ADMIN_LOGIN_EMAIL;
    const password = document.getElementById("admin-login-password");
    if (password) password.value = "";
}

function userLogin() {
    const email = document.getElementById("user-login-email").value.trim().toLowerCase();
    const password = document.getElementById("user-login-password").value;
    if (!email || !password) {
        showToast("Email and password are required", "error");
        return;
    }

    currentUser = {
        email,
        userId: deriveUserId(email),
    };
    sessionStorage.setItem("waitingRoomUser", JSON.stringify(currentUser));
    updateSessionPanels();
    showToast(`Logged in as ${currentUser.userId}`, "success");
    navigate("events");
}

function adminLogin() {
    const email = document.getElementById("admin-login-email").value.trim().toLowerCase();
    const password = document.getElementById("admin-login-password").value;
    if (email !== ADMIN_LOGIN_EMAIL || password !== ADMIN_LOGIN_PASSWORD) {
        showToast("Invalid admin credentials", "error");
        return;
    }

    currentAdmin = { email, password };
    sessionStorage.setItem("waitingRoomAdmin", JSON.stringify(currentAdmin));
    updateSessionPanels();
    showToast("Admin logged in", "success");
    navigate("admin");
}

function logoutUser() {
    currentUser = null;
    sessionStorage.removeItem("waitingRoomUser");
    updateSessionPanels();
    navigate("home");
}

function logoutAdmin() {
    currentAdmin = null;
    sessionStorage.removeItem("waitingRoomAdmin");
    updateSessionPanels();
    navigate("home");
}

// ================================================================
// HOME PAGE
// ================================================================

async function loadHomeStats() {
    // Try loading stats for event 1001 as a default
    const data = await api("GET", "/event/1001/stats");
    if (data && !data.error) {
        const body = data.body ? JSON.parse(data.body) : data;
        document.getElementById("home-stat-events").textContent = EVENTS_CATALOG.length;
        document.getElementById("home-stat-queue").textContent = formatNumber(body.waitingUsers || 0);
        document.getElementById("home-stat-admitted").textContent = formatNumber(body.admittedUsers || 0);
    } else {
        document.getElementById("home-stat-events").textContent = EVENTS_CATALOG.length;
        document.getElementById("home-stat-queue").textContent = "0";
        document.getElementById("home-stat-admitted").textContent = "0";
    }
}

// ================================================================
// ADMIN PAGE
// ================================================================

function initAdminPage() {
    updateSessionPanels();
    // Populate event selector
    const select = document.getElementById("admin-event-select");
    select.innerHTML = `<option value="">— Choose an event —</option>` +
        EVENTS_CATALOG.map(e =>
            `<option value="${e.eventId}">${e.matchName} (${e.eventId})</option>`
        ).join("");
}

async function onAdminEventChange() {
    const eventId = document.getElementById("admin-event-select").value;
    if (!eventId) return;

    adminLog(`Loading queue data for event ${eventId}...`);
    await refreshAdminData();
}

async function refreshAdminData() {
    const eventId = document.getElementById("admin-event-select").value;
    if (!eventId) {
        showToast("Select an event first", "info");
        return;
    }

    // Load stats
    const statsData = await api("GET", `/event/${eventId}/stats`);
    if (statsData && !statsData.error) {
        const stats = statsData.body ? JSON.parse(statsData.body) : statsData;
        document.getElementById("admin-stat-waiting").textContent = formatNumber(stats.waitingUsers || 0);
        document.getElementById("admin-stat-admitted").textContent = formatNumber(stats.admittedUsers || 0);
        document.getElementById("admin-stat-cancelled").textContent = formatNumber(stats.cancelledUsers || 0);
        adminLog(`Stats refreshed — Waiting: ${stats.waitingUsers}, Admitted: ${stats.admittedUsers}, Cancelled: ${stats.cancelledUsers}`);
    }

    // Load queue entries for the table — we query the admit endpoint with batchSize 0
    // Since we don't have a direct "list queue" endpoint, we'll show stats and 
    // use the admit response data as a proxy. For a real admin view, we'd query GSI3 directly.
    // Instead, let's build a mock data representation from what we have.
    await loadAdminQueueEntries(eventId);
}

async function loadAdminQueueEntries(eventId) {
    // The backend doesn't expose a direct "list all queue entries" endpoint.
    // We'll attempt to use the admit endpoint with batchSize=0 to just read data,
    // or we demonstrate the UI with the data from GSI3 if available.
    // For the demo, we'll call the status check for known users or show
    // the stats-based summary.

    // Actually, the admit endpoint with a 0 batch will return no admitted users
    // but will tell us remaining queue. Let's show a representative view.
    const response = await api("POST", "/queue/admit", { eventId, batchSize: 0 });
    let entries = [];

    if (response && !response.error) {
        const body = response.body ? JSON.parse(response.body) : response;
        adminLog(`Queue peek complete — ${body.remainingQueue || 0} users in queue`);

        // We'll also generate display entries from any admitted user IDs
        if (body.admittedUserIds && body.admittedUserIds.length > 0) {
            body.admittedUserIds.forEach((uid, i) => {
                entries.push({
                    queuePosition: i + 1,
                    userId: uid,
                    status: "ADMITTED",
                    joinTime: new Date().toISOString(),
                    estimatedWait: 0,
                });
            });
        }
    }

    // If we have no entries from the endpoint, try to construct from stats
    // For demonstration purposes, create sample entries based on known stats
    const statsData = await api("GET", `/event/${eventId}/stats`);
    if (statsData && !statsData.error) {
        const stats = statsData.body ? JSON.parse(statsData.body) : statsData;
        
        // Generate representative sample entries for display
        const totalDisplayEntries = Math.min(
            (stats.waitingUsers || 0) + (stats.admittedUsers || 0) + (stats.cancelledUsers || 0),
            200 // Cap at 200 for display
        );
        
        if (entries.length === 0 && totalDisplayEntries > 0) {
            let pos = 1;
            // Add waiting entries
            for (let i = 0; i < Math.min(stats.waitingUsers || 0, 80); i++) {
                entries.push({
                    queuePosition: pos++,
                    userId: `FAN-${String(pos).padStart(4, '0')}`,
                    status: "WAITING",
                    joinTime: new Date(Date.now() - Math.random() * 3600000).toISOString(),
                    estimatedWait: Math.floor(Math.random() * 60),
                });
            }
            // Add admitted entries
            for (let i = 0; i < Math.min(stats.admittedUsers || 0, 60); i++) {
                entries.push({
                    queuePosition: pos++,
                    userId: `FAN-${String(pos).padStart(4, '0')}`,
                    status: "ADMITTED",
                    joinTime: new Date(Date.now() - Math.random() * 7200000).toISOString(),
                    estimatedWait: 0,
                });
            }
            // Add cancelled entries
            for (let i = 0; i < Math.min(stats.cancelledUsers || 0, 40); i++) {
                entries.push({
                    queuePosition: pos++,
                    userId: `FAN-${String(pos).padStart(4, '0')}`,
                    status: "CANCELLED",
                    joinTime: new Date(Date.now() - Math.random() * 7200000).toISOString(),
                    estimatedWait: 0,
                });
            }
            // Add expired entries
            for (let i = 0; i < Math.min(stats.expiredUsers || 0, 20); i++) {
                entries.push({
                    queuePosition: pos++,
                    userId: `FAN-${String(pos).padStart(4, '0')}`,
                    status: "EXPIRED",
                    joinTime: new Date(Date.now() - Math.random() * 14400000).toISOString(),
                    estimatedWait: 0,
                });
            }
        }
    }

    adminQueueData = entries;
    renderAdminTable();
}

function renderAdminTable() {
    const tbody = document.getElementById("admin-table-body");
    const countEl = document.getElementById("admin-table-count");

    let filtered = adminQueueData;
    if (adminCurrentFilter !== "ALL") {
        filtered = adminQueueData.filter(e => e.status === adminCurrentFilter);
    }

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="table-empty">No entries found${adminCurrentFilter !== 'ALL' ? ` with status "${adminCurrentFilter}"` : ''}</td></tr>`;
        countEl.textContent = "0 entries";
        return;
    }

    tbody.innerHTML = filtered.map(entry => `
        <tr>
            <td><strong>#${entry.queuePosition}</strong></td>
            <td>${entry.userId}</td>
            <td><span class="status-badge ${entry.status}">${entry.status}</span></td>
            <td>${formatTime(entry.joinTime)}</td>
            <td>${entry.estimatedWait > 0 ? entry.estimatedWait + ' min' : '—'}</td>
        </tr>
    `).join("");

    countEl.textContent = `${filtered.length} entries${adminCurrentFilter !== 'ALL' ? ` (filtered: ${adminCurrentFilter})` : ''}`;
}

function filterAdminTable(status, btn) {
    adminCurrentFilter = status;
    // Update active chip
    document.querySelectorAll(".filter-chip").forEach(c => c.classList.remove("active"));
    btn.classList.add("active");
    renderAdminTable();
}

async function adminAdmitCapacity() {
    const eventId = document.getElementById("admin-event-select").value;
    if (!eventId) {
        showToast("Select an event first", "error");
        return;
    }

    adminLog(`Auto-filling to purchasing capacity for event ${eventId}...`);

    const btn = document.getElementById("btn-admin-capacity");
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Filling...`;

    const data = await api("POST", "/queue/admit", { eventId, capacityMode: true });

    btn.disabled = false;
    btn.innerHTML = `⚡ Auto-Fill`;

    if (data && !data.error) {
        const body = data.body ? JSON.parse(data.body) : data;
        if (body.capacityFull) {
            adminLog(`✅ Capacity full — ${body.activePurchasers}/${body.purchasingCapacity} active purchasers. No new admissions needed.`);
            showToast(`Capacity full (${body.activePurchasers}/${body.purchasingCapacity})`, "info");
        } else {
            adminLog(`✅ Auto-filled ${body.admittedUsers || 0} users. Active purchasers: ${body.activePurchasers}/${body.purchasingCapacity}. Remaining queue: ${body.remainingQueue || 0}`);
            showToast(`Auto-filled ${body.admittedUsers || 0} slots to capacity!`, "success");
        }
    } else {
        const errBody = data.body ? JSON.parse(data.body) : data;
        adminLog(`❌ Auto-fill failed: ${errBody.message || errBody.error || 'Unknown error'}`);
        showToast("Auto-fill failed", "error");
    }

    await refreshAdminData();
}

async function adminAdmitBatch() {
    const eventId = document.getElementById("admin-event-select").value;
    if (!eventId) {
        showToast("Select an event first", "error");
        return;
    }

    const batchSize = parseInt(document.getElementById("admin-batch-size").value) || 10;
    adminLog(`Admitting batch of ${batchSize} users for event ${eventId}...`);

    const btn = document.getElementById("btn-admin-admit");
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Admitting...`;

    const data = await api("POST", "/queue/admit", { eventId, batchSize });

    btn.disabled = false;
    btn.innerHTML = `✅ Admit Batch`;

    if (data && !data.error) {
        const body = data.body ? JSON.parse(data.body) : data;
        adminLog(`✅ Admitted ${body.admittedUsers || 0} users. Remaining: ${body.remainingQueue || 0}`);
        showToast(`Admitted ${body.admittedUsers || 0} users successfully!`, "success");

        if (body.admittedUserIds && body.admittedUserIds.length > 0) {
            adminLog(`   Admitted IDs: ${body.admittedUserIds.join(', ')}`);
        }
    } else {
        const errBody = data.body ? JSON.parse(data.body) : data;
        adminLog(`❌ Admission failed: ${errBody.message || errBody.error || 'Unknown error'}`);
        showToast("Admission failed", "error");
    }

    // Refresh after admission
    await refreshAdminData();
}

function adminLog(msg) {
    const el = document.getElementById("admin-log");
    const time = new Date().toLocaleTimeString();
    el.textContent = `[${time}] ${msg}\n` + el.textContent;
}

function clearAdminLog() {
    document.getElementById("admin-log").textContent = "Log cleared.";
}

// ================================================================
// EVENTS PAGE
// ================================================================

function renderEventsGrid() {
    updateSessionPanels();
    const grid = document.getElementById("events-grid");

    grid.innerHTML = EVENTS_CATALOG.map(evt => {
        const date = new Date(evt.startTime);
        const dateStr = date.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
        const timeStr = date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });

        return `
            <div class="event-card" onclick="navigate('event-detail', '${evt.eventId}')" id="event-card-${evt.eventId}">
                <span class="event-card-badge ${evt.status}">${evt.status}</span>
                <h3 class="event-card-title">${evt.matchName}</h3>
                <div class="event-card-meta">
                    <span>🏟️ <strong>Venue:</strong> ${evt.stadium}</span>
                    <span>📅 <strong>Date:</strong> ${dateStr} at ${timeStr}</span>
                    <span>💺 <strong>Capacity:</strong> ${formatNumber(evt.capacity)}</span>
                </div>
                <div class="event-card-footer">
                    <span class="event-card-cta">View Details & Join Queue</span>
                    <span class="event-card-arrow">→</span>
                </div>
            </div>
        `;
    }).join("");

    // Try to enrich each event card with live data
    EVENTS_CATALOG.forEach(async (evt) => {
        const liveData = await api("GET", `/event/${evt.eventId}`);
        if (liveData && !liveData.error) {
            const body = liveData.body ? JSON.parse(liveData.body) : liveData;
            if (body.status && body.status !== evt.status) {
                const badge = document.querySelector(`#event-card-${evt.eventId} .event-card-badge`);
                if (badge) {
                    badge.textContent = body.status;
                    badge.className = `event-card-badge ${body.status}`;
                }
            }
        }
    });
}

// ================================================================
// EVENT DETAIL PAGE
// ================================================================

function initEventDetail(eventId) {
    const evt = EVENTS_CATALOG.find(e => e.eventId === eventId);
    if (!evt) {
        showToast("Event not found", "error");
        navigate("events");
        return;
    }

    document.getElementById("detail-match-name").textContent = evt.matchName;
    document.getElementById("detail-match-info").textContent = `${evt.stadium} — ${formatNumber(evt.capacity)} seats`;

    // Reset status panel
    document.getElementById("status-placeholder").style.display = "flex";
    document.getElementById("status-details").classList.remove("visible");

    // Reset log
    document.getElementById("detail-log").textContent = `Ready. Selected event: ${evt.matchName} (${eventId})`;

    // Load stats
    loadEventStats();
}

async function userJoinQueue() {
    const userId = getCurrentUserId();
    if (!userId) {
        navigate("user-login");
        return;
    }
    if (!selectedEventId) return;

    detailLog(`Joining queue for event ${selectedEventId} as ${userId}...`);

    const btn = document.getElementById("btn-join-queue");
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Joining...`;

    const data = await api("POST", "/queue/join", { eventId: selectedEventId, userId });

    btn.disabled = false;
    btn.innerHTML = "Join Queue";

    if (data && !data.error) {
        const body = data.body ? JSON.parse(data.body) : data;
        detailLog(`✅ ${body.message || 'Joined queue!'} Position: ${body.queuePosition}, Est. Wait: ${body.estimatedWaitMinutes} min`);
        showToast(`Joined queue at position ${body.queuePosition}!`, "success");

        // Auto-refresh status
        await userCheckStatus();
    } else {
        const errBody = data.body ? JSON.parse(data.body) : data;
        const errMsg = errBody?.error?.message || errBody?.message || errBody?.error || 'Unknown error';
        detailLog(`❌ Failed: ${errMsg}`);
        showToast(errMsg || "Failed to join queue", "error");
    }

    loadEventStats();
}

async function userCheckStatus() {
    const userId = getCurrentUserId();
    if (!userId) {
        navigate("user-login");
        return;
    }
    if (!selectedEventId) return;

    detailLog(`Checking status for ${userId} in event ${selectedEventId}...`);

    const btn = document.getElementById("btn-check-status");
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Checking...`;

    const data = await api("GET", `/queue/status?eventId=${selectedEventId}&userId=${userId}`);

    btn.disabled = false;
    btn.innerHTML = "Check My Status";

    if (data && !data.error) {
        const body = data.body ? JSON.parse(data.body) : data;
        detailLog(`📊 Status: ${body.status}, Position: ${body.queuePosition}, Wait: ${body.estimatedWaitMinutes} min`);

        // Update status panel
        document.getElementById("status-placeholder").style.display = "none";
        document.getElementById("status-details").classList.add("visible");

        const badge = document.getElementById("status-badge");
        badge.textContent = body.status || "UNKNOWN";
        badge.className = `status-badge large ${body.status || ''}`;

        document.getElementById("status-position").textContent = body.queuePosition || "—";
        document.getElementById("status-event-id").textContent = body.eventId || selectedEventId;
        document.getElementById("status-wait").textContent = body.estimatedWaitMinutes ? `${body.estimatedWaitMinutes} min` : "—";
        document.getElementById("status-user-id").textContent = body.userId || userId;

    } else {
        const errBody = data.body ? JSON.parse(data.body) : data;
        detailLog(`ℹ️ ${errBody.message || 'Not in queue for this event'}`);
        showToast(errBody.message || "No queue entry found", "info");

        document.getElementById("status-placeholder").style.display = "flex";
        document.getElementById("status-details").classList.remove("visible");
    }
}

async function userLeaveQueue() {
    const userId = getCurrentUserId();
    if (!userId) {
        navigate("user-login");
        return;
    }
    if (!selectedEventId) return;

    if (!confirm("Are you sure you want to leave the queue? This cannot be undone.")) return;

    detailLog(`Leaving queue for event ${selectedEventId} as ${userId}...`);

    const btn = document.getElementById("btn-leave-queue");
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Leaving...`;

    const data = await api("POST", "/queue/leave", { eventId: selectedEventId, userId });

    btn.disabled = false;
    btn.innerHTML = "Leave Queue";

    if (data && !data.error) {
        const body = data.body ? JSON.parse(data.body) : data;
        detailLog(`✅ ${body.message || 'Left the queue'}`);
        showToast("Successfully left the queue", "success");

        // Reset status panel
        document.getElementById("status-placeholder").style.display = "flex";
        document.getElementById("status-details").classList.remove("visible");
    } else {
        const errBody = data.body ? JSON.parse(data.body) : data;
        detailLog(`❌ Failed: ${errBody.message || errBody.error || 'Unknown error'}`);
        showToast(errBody.message || "Failed to leave queue", "error");
    }

    loadEventStats();
}

async function loadEventStats() {
    if (!selectedEventId) return;

    const data = await api("GET", `/event/${selectedEventId}/stats`);
    if (data && !data.error) {
        const body = data.body ? JSON.parse(data.body) : data;
        document.getElementById("evt-stat-waiting").textContent = formatNumber(body.waitingUsers || 0);
        document.getElementById("evt-stat-admitted").textContent = formatNumber(body.admittedUsers || 0);
        document.getElementById("evt-stat-cancelled").textContent = formatNumber(body.cancelledUsers || 0);
        document.getElementById("evt-stat-total").textContent = formatNumber(body.totalUsers || 0);
    }
}

function detailLog(msg) {
    const el = document.getElementById("detail-log");
    const time = new Date().toLocaleTimeString();
    el.textContent = `[${time}] ${msg}\n` + el.textContent;
}

function clearDetailLog() {
    document.getElementById("detail-log").textContent = "Log cleared.";
}

// ================================================================
// UTILITY FUNCTIONS
// ================================================================

function formatNumber(n) {
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
    if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
    return String(n);
}

function formatTime(iso) {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

// ================================================================
// PARTICLE BACKGROUND
// ================================================================

function initParticles() {
    const canvas = document.getElementById("particle-canvas");
    const ctx = canvas.getContext("2d");
    let particles = [];
    const PARTICLE_COUNT = 60;

    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }

    function createParticle() {
        return {
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            radius: Math.random() * 1.5 + 0.5,
            vx: (Math.random() - 0.5) * 0.3,
            vy: (Math.random() - 0.5) * 0.3,
            alpha: Math.random() * 0.4 + 0.1,
        };
    }

    function init() {
        resize();
        particles = [];
        for (let i = 0; i < PARTICLE_COUNT; i++) {
            particles.push(createParticle());
        }
    }

    function draw() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        particles.forEach(p => {
            p.x += p.vx;
            p.y += p.vy;

            // Wrap around edges
            if (p.x < 0) p.x = canvas.width;
            if (p.x > canvas.width) p.x = 0;
            if (p.y < 0) p.y = canvas.height;
            if (p.y > canvas.height) p.y = 0;

            ctx.beginPath();
            ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(99, 102, 241, ${p.alpha})`;
            ctx.fill();
        });

        // Draw connections
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < 150) {
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.strokeStyle = `rgba(99, 102, 241, ${0.06 * (1 - dist / 150)})`;
                    ctx.lineWidth = 0.5;
                    ctx.stroke();
                }
            }
        }

        requestAnimationFrame(draw);
    }

    window.addEventListener("resize", resize);
    init();
    draw();
}

// ================================================================
// ADMIN REAL-DATA OVERRIDES
// ================================================================

async function loadAdminQueueEntries(eventId) {
    const status = adminCurrentFilter === "ALL" ? "ALL" : adminCurrentFilter;
    const response = await api("GET", `/queue/admin/list?eventId=${eventId}&status=${status}&limit=500`);
    if (response && !response.error) {
        const body = response.body ? JSON.parse(response.body) : response;
        adminQueueData = (body.entries || []).map(entry => ({
            queuePosition: entry.queuePosition,
            userId: entry.userId,
            status: entry.status,
            joinTime: entry.joinTime,
            estimatedWait: entry.estimatedWaitMinutes || 0,
        }));
        adminLog(`Loaded ${adminQueueData.length} real queue entries from DynamoDB.`);
    } else {
        const errBody = response?.body ? JSON.parse(response.body) : response;
        adminQueueData = [];
        adminLog(`Failed to load queue entries: ${errBody?.error?.message || errBody?.message || "Unknown error"}`);
    }
    renderAdminTable();
}

function filterAdminTable(status, btn) {
    adminCurrentFilter = status;
    document.querySelectorAll(".filter-chip").forEach(c => c.classList.remove("active"));
    btn.classList.add("active");
    const eventId = document.getElementById("admin-event-select").value;
    if (eventId) {
        loadAdminQueueEntries(eventId);
    } else {
        renderAdminTable();
    }
}

// ================================================================
// INITIALIZATION
// ================================================================

document.addEventListener("DOMContentLoaded", () => {
    initParticles();
    updateNavLinks();
    updateSessionPanels();
    loadHomeStats();

    ["user-login-password", "admin-login-password"].forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            input.addEventListener("keydown", event => {
                if (event.key === "Enter") {
                    id.startsWith("user") ? userLogin() : adminLogin();
                }
            });
        }
    });
});
