/**
 * Jarvis Mission Control Dashboard
 * Real-time metrics and system monitoring
 */

class DashboardApp {
    constructor() {
        this.wsConnected = false;
        this.ws = null;
        this.charts = {};
        this.updateInterval = null;
        this.chartData = {
            successRate: [],
            latency: [],
            throughput: [],
            cachePerformance: []
        };

        // Initialize the dashboard
        this.init();
    }

    async init() {
        console.log('Initializing dashboard...');

        // Setup event listeners
        this.setupEventListeners();

        // Initial data fetch
        await this.fetchMetrics();
        await this.fetchChartData();

        // Setup charts
        this.setupCharts();

        // Connect to WebSocket
        this.connectWebSocket();

        // Start polling for updates
        this.startPolling();

        console.log('Dashboard initialized');
    }

    setupEventListeners() {
        // Update time display every second
        setInterval(() => this.updateTimeDisplay(), 1000);
    }

    updateTimeDisplay() {
        const now = new Date();
        document.getElementById('current-time').textContent = now.toLocaleTimeString();
        document.getElementById('last-update').textContent = now.toLocaleString();
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/ws`;

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.setConnectionStatus(true);
                // Send ping to keep connection alive
                setInterval(() => {
                    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                        this.ws.send('ping');
                    }
                }, 30000);
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'metrics_update') {
                        this.updateDashboard(data);
                    }
                } catch (e) {
                    console.error('Error parsing WebSocket message:', e);
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.setConnectionStatus(false);
            };

            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.setConnectionStatus(false);
                // Attempt to reconnect after 3 seconds
                setTimeout(() => this.connectWebSocket(), 3000);
            };
        } catch (e) {
            console.error('Failed to connect WebSocket:', e);
            this.setConnectionStatus(false);
        }
    }

    setConnectionStatus(connected) {
        this.wsConnected = connected;
        const statusElement = document.getElementById('connection-status');
        if (connected) {
            statusElement.textContent = 'Connected';
            statusElement.classList.remove('disconnected');
            statusElement.classList.add('connected');
        } else {
            statusElement.textContent = 'Disconnected';
            statusElement.classList.remove('connected');
            statusElement.classList.add('disconnected');
        }
    }

    startPolling() {
        // Poll for metrics and chart data every 5 seconds
        this.updateInterval = setInterval(async () => {
            if (!this.wsConnected) {
                await this.fetchMetrics();
            }
            await this.fetchChartData();
        }, 5000);
    }

    async fetchMetrics() {
        try {
            const response = await fetch('/api/metrics');
            const data = await response.json();
            this.updateDashboard(data);
        } catch (e) {
            console.error('Error fetching metrics:', e);
        }
    }

    async fetchChartData() {
        try {
            const response = await fetch('/api/chart-data');
            const data = await response.json();
            this.updateCharts(data);
        } catch (e) {
            console.error('Error fetching chart data:', e);
        }
    }

    updateDashboard(data) {
        const stats = data.stats;
        const health = data.health;

        // Update key metrics
        if (stats) {
            document.getElementById('success-rate').textContent =
                stats.success_rate_pct.toFixed(1);
            document.getElementById('avg-latency').textContent =
                stats.avg_duration_seconds.toFixed(2);
            document.getElementById('total-executions').textContent =
                stats.total_executions;
            document.getElementById('throughput').textContent =
                stats.throughput_per_minute.toFixed(2);
            document.getElementById('cache-hit-rate').textContent =
                stats.cache_hit_rate_pct.toFixed(1);
            document.getElementById('failure-count').textContent =
                stats.failure_count;

            // Update execution log
            this.updateExecutionLog(stats);
        }

        // Update health status
        if (health) {
            this.updateHealthStatus(health);
        }

        // Update last update timestamp
        this.updateTimeDisplay();
    }

    updateHealthStatus(health) {
        const healthElement = document.getElementById('health-indicator');
        const healthText = document.getElementById('health-text');
        const componentsContainer = document.getElementById('health-components');

        // Update health circle color
        healthElement.className = 'health-circle ' + health.status;
        healthText.textContent = health.status.charAt(0).toUpperCase() + health.status.slice(1);

        // Update components
        let componentsHtml = '';
        for (const [component, isHealthy] of Object.entries(health.components)) {
            const status = isHealthy ? 'OK' : 'ERROR';
            const statusClass = isHealthy ? 'ok' : 'error';
            componentsHtml += `<p class="component-status ${statusClass}">[${status}] ${this.formatComponentName(component)}</p>`;
        }
        componentsContainer.innerHTML = componentsHtml;
    }

    formatComponentName(component) {
        return component
            .replace(/_/g, ' ')
            .split(' ')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }

    updateExecutionLog(stats) {
        const logContainer = document.getElementById('execution-log');

        // Clear and update with latest data
        let logHtml = '';

        // Add summary line
        logHtml += `<p class="log-entry log-summary">Total: ${stats.total_executions} | Success: ${stats.success_count} | Failure: ${stats.failure_count} | Throughput: ${stats.throughput_per_minute}/min</p>`;

        // Add top actions
        if (stats.top_actions && stats.top_actions.length > 0) {
            logHtml += '<p class="log-entry log-section">Top Actions:</p>';
            stats.top_actions.forEach(action => {
                logHtml += `<p class="log-entry log-action">  → ${action.action}: ${action.count} calls</p>`;
            });
        }

        // Add top errors if any
        if (stats.top_errors && stats.top_errors.length > 0) {
            logHtml += '<p class="log-entry log-section">Recent Errors:</p>';
            stats.top_errors.forEach(error => {
                logHtml += `<p class="log-entry log-error">  ✗ ${error[0]}: ${error[1]} occurrences</p>`;
            });
        }

        // Fallback if no data
        if (!stats.top_actions || stats.top_actions.length === 0) {
            logHtml += '<p class="log-entry">No execution data yet...</p>';
        }

        logContainer.innerHTML = logHtml;
    }

    setupCharts() {
        const chartConfigs = {
            'success-rate-chart': {
                type: 'line',
                label: 'Success Rate (%)',
                borderColor: '#4CAF50',
                backgroundColor: 'rgba(76, 175, 80, 0.1)',
                key: 'successRate'
            },
            'latency-chart': {
                type: 'line',
                label: 'Latency (s)',
                borderColor: '#FF9800',
                backgroundColor: 'rgba(255, 152, 0, 0.1)',
                key: 'latency'
            },
            'throughput-chart': {
                type: 'bar',
                label: 'Throughput (calls)',
                borderColor: '#2196F3',
                backgroundColor: 'rgba(33, 150, 243, 0.6)',
                key: 'throughput'
            },
            'cache-chart': {
                type: 'line',
                label: 'Cache Hit Rate (%)',
                borderColor: '#9C27B0',
                backgroundColor: 'rgba(156, 39, 176, 0.1)',
                key: 'cachePerformance'
            }
        };

        for (const [chartId, config] of Object.entries(chartConfigs)) {
            const ctx = document.getElementById(chartId).getContext('2d');
            this.charts[config.key] = new Chart(ctx, {
                type: config.type,
                data: {
                    labels: [],
                    datasets: [{
                        label: config.label,
                        data: [],
                        borderColor: config.borderColor,
                        backgroundColor: config.backgroundColor,
                        borderWidth: 2,
                        fill: true,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: config.key === 'successRate' || config.key === 'cachePerformance' ? 100 : undefined
                        }
                    },
                    plugins: {
                        legend: {
                            display: true
                        }
                    }
                }
            });
        }
    }

    updateCharts(data) {
        if (!data) return;

        // Update success rate chart
        if (data.success_rate_trend && data.success_rate_trend.length > 0) {
            const labels = data.success_rate_trend.map(d => this.formatTime(d.time));
            const values = data.success_rate_trend.map(d => d.rate);
            this.updateChart('successRate', labels, values);
        }

        // Update latency chart
        if (data.latency_trend && data.latency_trend.length > 0) {
            const labels = data.latency_trend.map(d => this.formatTime(d.time));
            const values = data.latency_trend.map(d => d.avg);
            this.updateChart('latency', labels, values);
        }

        // Update throughput chart
        if (data.throughput_trend && data.throughput_trend.length > 0) {
            const labels = data.throughput_trend.map(d => this.formatTime(d.time));
            const values = data.throughput_trend.map(d => d.count);
            this.updateChart('throughput', labels, values);
        }

        // Update cache chart
        if (data.cache_performance && data.cache_performance.length > 0) {
            const labels = data.cache_performance.map(d => this.formatTime(d.time));
            const values = data.cache_performance.map(d => d.hit_rate);
            this.updateChart('cachePerformance', labels, values);
        }
    }

    updateChart(key, labels, values) {
        const chart = this.charts[key];
        if (chart) {
            chart.data.labels = labels;
            chart.data.datasets[0].data = values;
            chart.update();
        }
    }

    formatTime(isoString) {
        try {
            const date = new Date(isoString);
            return date.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        } catch {
            return isoString;
        }
    }

    destroy() {
        if (this.ws) {
            this.ws.close();
        }
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardApp = new DashboardApp();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.dashboardApp) {
        window.dashboardApp.destroy();
    }
});
