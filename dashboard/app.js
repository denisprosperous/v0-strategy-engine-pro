/**
 * Trading Dashboard Application
 * 
 * Handles:
 * - Authentication
 * - API communication
 * - Real-time WebSocket updates
 * - UI interactions
 * - Data visualization
 */

// ========== CONFIGURATION ==========
const API_URL = window.location.origin.includes('localhost') 
    ? 'http://localhost:8000'
    : window.location.origin;
const WS_URL = API_URL.replace('http', 'ws');

let authToken = localStorage.getItem('authToken');
let ws = null;
let equityChart = null;

// ========== AUTHENTICATION ==========

function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');
}

function showLoading(show = true) {
    const loading = document.getElementById('loading');
    if (show) {
        loading.classList.remove('hidden');
    } else {
        loading.classList.add('hidden');
    }
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px;">
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            <span>${message}</span>
        </div>
    `;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

async function login(username, password) {
    try {
        showLoading(true);
        
        const response = await fetch(`${API_URL}/api/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        if (!response.ok) {
            throw new Error('Invalid credentials');
        }
        
        const data = await response.json();
        authToken = data.access_token;
        localStorage.setItem('authToken', authToken);
        
        showScreen('dashboard-screen');
        initDashboard();
        showToast('Login successful!', 'success');
        
    } catch (error) {
        showToast(error.message || 'Login failed', 'error');
    } finally {
        showLoading(false);
    }
}

function logout() {
    authToken = null;
    localStorage.removeItem('authToken');
    if (ws) ws.close();
    showScreen('login-screen');
    showToast('Logged out successfully', 'info');
}

// ========== API CALLS ==========

async function apiRequest(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...(authToken && { 'Authorization': `Bearer ${authToken}` })
    };
    
    const response = await fetch(`${API_URL}${endpoint}`, {
        ...options,
        headers: { ...headers, ...options.headers }
    });
    
    if (response.status === 401) {
        logout();
        throw new Error('Session expired');
    }
    
    if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
    }
    
    return await response.json();
}

async function getBotStatus() {
    return await apiRequest('/api/status');
}

async function getPortfolioBalances() {
    return await apiRequest('/api/portfolio/balances');
}

async function getRecentSignals(limit = 10) {
    return await apiRequest(`/api/signals/recent?limit=${limit}`);
}

async function getPerformanceMetrics() {
    return await apiRequest('/api/performance/metrics');
}

async function getTradeHistory(limit = 50) {
    return await apiRequest(`/api/trades/history?limit=${limit}`);
}

async function startBot() {
    return await apiRequest('/api/bot/start', { method: 'POST' });
}

async function stopBot() {
    return await apiRequest('/api/bot/stop', { method: 'POST' });
}

async function setBotMode(mode) {
    return await apiRequest(`/api/bot/mode?mode=${mode}`, { method: 'POST' });
}

// ========== WEBSOCKET ==========

function connectWebSocket() {
    if (ws) return;
    
    ws = new WebSocket(`${WS_URL}/ws`);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
    
    ws.onclose = () => {
        console.log('WebSocket disconnected');
        ws = null;
        // Reconnect after 5 seconds
        setTimeout(() => {
            if (authToken) connectWebSocket();
        }, 5000);
    };
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'bot_status':
            updateBotStatus(data.data);
            break;
        case 'new_signal':
            showToast(`New signal: ${data.data.symbol}`, 'info');
            loadRecentSignals();
            break;
        case 'trade_completed':
            showToast(`Trade completed: ${data.data.symbol}`, 'success');
            loadOverviewData();
            break;
        case 'mode_change':
            showToast(`Trading mode: ${data.data.mode}`, 'info');
            break;
    }
}

// ========== DATA LOADING ==========

async function loadOverviewData() {
    try {
        const [metrics, signals] = await Promise.all([
            getPerformanceMetrics(),
            getRecentSignals(5)
        ]);
        
        // Update stats
        document.getElementById('total-pnl').textContent = `$${metrics.total_pnl.toFixed(2)}`;
        document.getElementById('daily-pnl').textContent = `$${metrics.daily_pnl.toFixed(2)}`;
        document.getElementById('win-rate').textContent = `${metrics.win_rate.toFixed(1)}%`;
        
        // Update signals
        displayRecentSignals(signals);
        
        // Update equity chart
        updateEquityChart();
        
    } catch (error) {
        console.error('Error loading overview:', error);
        showToast('Failed to load data', 'error');
    }
}

async function loadPortfolioData() {
    try {
        const balances = await getPortfolioBalances();
        displayPortfolio(balances);
    } catch (error) {
        console.error('Error loading portfolio:', error);
        showToast('Failed to load portfolio', 'error');
    }
}

async function loadSignalsData() {
    try {
        const signals = await getRecentSignals(20);
        displaySignalsList(signals);
    } catch (error) {
        console.error('Error loading signals:', error);
        showToast('Failed to load signals', 'error');
    }
}

async function loadTradesData() {
    try {
        const data = await getTradeHistory();
        displayTrades(data.trades);
    } catch (error) {
        console.error('Error loading trades:', error);
        showToast('Failed to load trades', 'error');
    }
}

async function loadPerformanceData() {
    try {
        const metrics = await getPerformanceMetrics();
        displayPerformanceMetrics(metrics);
    } catch (error) {
        console.error('Error loading performance:', error);
        showToast('Failed to load performance', 'error');
    }
}

// ========== UI UPDATES ==========

function updateBotStatus(status) {
    const statusEl = document.getElementById('bot-status');
    const indicator = statusEl.querySelector('.status-indicator');
    const text = statusEl.querySelector('.status-text');
    
    if (status.is_running) {
        indicator.className = 'status-indicator status-running';
        text.textContent = 'Running';
    } else {
        indicator.className = 'status-indicator status-stopped';
        text.textContent = 'Stopped';
    }
}

function displayRecentSignals(signals) {
    const container = document.querySelector('#overview-page .signal-list');
    container.innerHTML = '';
    
    signals.forEach(signal => {
        const signalEl = document.createElement('div');
        signalEl.className = 'signal-item';
        signalEl.innerHTML = `
            <div class="signal-header">
                <div class="signal-symbol">${signal.symbol}</div>
                <span class="signal-tier tier-${signal.tier}">Tier ${signal.tier}</span>
            </div>
            <div class="signal-details">
                <div>${signal.direction.toUpperCase()} @ $${signal.entry_price.toFixed(2)}</div>
                <div>Confidence: ${(signal.confidence * 100).toFixed(0)}%</div>
                <div>Status: ${signal.status}</div>
            </div>
        `;
        container.appendChild(signalEl);
    });
}

function displayPortfolio(balances) {
    const tbody = document.querySelector('#portfolio-table tbody');
    tbody.innerHTML = '';
    
    balances.forEach(balance => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${balance.asset}</strong></td>
            <td>${balance.free.toFixed(8)}</td>
            <td>${balance.locked.toFixed(8)}</td>
            <td>${balance.total.toFixed(8)}</td>
            <td class="positive">$${balance.usd_value.toFixed(2)}</td>
        `;
        tbody.appendChild(row);
    });
}

function displaySignalsList(signals) {
    const container = document.getElementById('signals-list');
    container.innerHTML = '';
    
    signals.forEach(signal => {
        const signalEl = document.createElement('div');
        signalEl.className = 'signal-item';
        signalEl.innerHTML = `
            <div class="signal-header">
                <div class="signal-symbol">${signal.symbol}</div>
                <span class="signal-tier tier-${signal.tier}">Tier ${signal.tier}</span>
            </div>
            <div class="signal-details">
                <div><strong>Direction:</strong> ${signal.direction.toUpperCase()}</div>
                <div><strong>Entry:</strong> $${signal.entry_price.toFixed(2)}</div>
                <div><strong>Stop Loss:</strong> $${signal.stop_loss.toFixed(2)}</div>
                <div><strong>Take Profit 1:</strong> $${signal.take_profit_1.toFixed(2)}</div>
                <div><strong>Take Profit 2:</strong> $${signal.take_profit_2.toFixed(2)}</div>
                <div><strong>Confidence:</strong> ${(signal.confidence * 100).toFixed(0)}%</div>
                <div><strong>Status:</strong> ${signal.status}</div>
                <div><strong>Time:</strong> ${new Date(signal.timestamp).toLocaleString()}</div>
            </div>
        `;
        container.appendChild(signalEl);
    });
}

function displayTrades(trades) {
    const tbody = document.querySelector('#trades-table tbody');
    tbody.innerHTML = '';
    
    trades.forEach(trade => {
        const row = document.createElement('tr');
        const pnlClass = trade.pnl > 0 ? 'positive' : 'negative';
        row.innerHTML = `
            <td><strong>${trade.symbol}</strong></td>
            <td>${trade.side.toUpperCase()}</td>
            <td>$${trade.entry_price.toFixed(2)}</td>
            <td>$${trade.exit_price.toFixed(2)}</td>
            <td class="${pnlClass}">$${trade.pnl.toFixed(2)}</td>
            <td class="${pnlClass}">${trade.pnl_pct > 0 ? '+' : ''}${trade.pnl_pct.toFixed(2)}%</td>
            <td>${new Date(trade.exit_time).toLocaleDateString()}</td>
        `;
        tbody.appendChild(row);
    });
}

function displayPerformanceMetrics(metrics) {
    document.getElementById('sharpe-ratio').textContent = metrics.sharpe_ratio.toFixed(2);
    document.getElementById('max-drawdown').textContent = `-${metrics.max_drawdown.toFixed(1)}%`;
    document.getElementById('total-trades').textContent = metrics.total_trades;
    // Calculate avg win from metrics
    const avgWin = metrics.total_trades > 0 ? (metrics.total_pnl / metrics.winning_trades) : 0;
    document.getElementById('avg-win').textContent = `+${(avgWin / 100).toFixed(1)}%`;
}

function updateEquityChart() {
    const ctx = document.getElementById('equity-chart');
    if (!ctx) return;
    
    // Generate sample data (replace with real data)
    const labels = [];
    const data = [];
    let equity = 10000;
    
    for (let i = 0; i < 30; i++) {
        labels.push(`Day ${i + 1}`);
        equity += (Math.random() - 0.4) * 200;
        data.push(equity);
    }
    
    if (equityChart) {
        equityChart.destroy();
    }
    
    equityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Portfolio Value',
                data: data,
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toFixed(0);
                        }
                    }
                }
            }
        }
    });
}

// ========== EVENT LISTENERS ==========

document.addEventListener('DOMContentLoaded', () => {
    // Check if already logged in
    if (authToken) {
        showScreen('dashboard-screen');
        initDashboard();
    }
    
    // Login form
    document.getElementById('login-form').addEventListener('submit', (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        login(username, password);
    });
    
    // Logout
    document.getElementById('logout-btn').addEventListener('click', logout);
    
    // Menu toggle (mobile)
    document.getElementById('menu-toggle').addEventListener('click', () => {
        document.getElementById('sidebar').classList.toggle('active');
    });
    
    // Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const page = item.dataset.page;
            switchPage(page);
            
            // Close sidebar on mobile
            if (window.innerWidth <= 768) {
                document.getElementById('sidebar').classList.remove('active');
            }
        });
    });
    
    // Bot controls
    document.getElementById('start-bot').addEventListener('click', async () => {
        try {
            await startBot();
            showToast('Bot started', 'success');
        } catch (error) {
            showToast('Failed to start bot', 'error');
        }
    });
    
    document.getElementById('stop-bot').addEventListener('click', async () => {
        try {
            await stopBot();
            showToast('Bot stopped', 'success');
        } catch (error) {
            showToast('Failed to stop bot', 'error');
        }
    });
    
    document.getElementById('trading-mode').addEventListener('change', async (e) => {
        try {
            await setBotMode(e.target.value);
            showToast(`Mode changed to ${e.target.value}`, 'success');
        } catch (error) {
            showToast('Failed to change mode', 'error');
        }
    });
    
    document.getElementById('refresh-portfolio').addEventListener('click', loadPortfolioData);
});

function switchPage(page) {
    // Update nav
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.page === page) {
            item.classList.add('active');
        }
    });
    
    // Update page
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(`${page}-page`).classList.add('active');
    
    // Load data for page
    switch (page) {
        case 'overview':
            loadOverviewData();
            break;
        case 'portfolio':
            loadPortfolioData();
            break;
        case 'signals':
            loadSignalsData();
            break;
        case 'trades':
            loadTradesData();
            break;
        case 'performance':
            loadPerformanceData();
            break;
    }
}

function initDashboard() {
    // Connect WebSocket
    connectWebSocket();
    
    // Load initial data
    loadOverviewData();
    getBotStatus().then(updateBotStatus).catch(console.error);
    
    // Auto-refresh every 30 seconds
    setInterval(() => {
        const activePage = document.querySelector('.page.active').id.replace('-page', '');
        switchPage(activePage);
    }, 30000);
}
