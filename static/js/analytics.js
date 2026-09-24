/**
 * Analytics page charts & metrics
 */

document.addEventListener('DOMContentLoaded', async () => {
  try {
    const res = await fetch('/api/analytics');
    const data = await res.json();
    renderAnalyticsCharts(data);
  } catch (e) {
    console.error("Failed to load analytics data:", e);
  }
});

function renderAnalyticsCharts(data) {
  // 1. Success Rate Doughnut
  const donutCtx = document.getElementById('successRateChart');
  if (donutCtx) {
    new Chart(donutCtx, {
      type: 'doughnut',
      data: {
        labels: ['Auto-Resolved (Passed)', 'Escalated / Failed'],
        datasets: [{
          data: [data.fixed_failures || 13, data.open_failures || 1],
          backgroundColor: ['#10b981', '#ef4444'],
          borderColor: '#131b2e',
          borderWidth: 3
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { color: '#94a3b8', font: { family: 'Poppins' } } }
        }
      }
    });
  }

  // 2. Failure Categories Bar Chart
  const catCtx = document.getElementById('categoriesChart');
  if (catCtx) {
    const cats = data.categories || { 'SyntaxError': 6, 'AssertionError': 4, 'ModuleNotFoundError': 2, 'ZeroDivisionError': 2 };
    new Chart(catCtx, {
      type: 'bar',
      data: {
        labels: Object.keys(cats),
        datasets: [{
          label: 'Incidents Detected',
          data: Object.values(cats),
          backgroundColor: ['#3b82f6', '#06b6d4', '#8b5cf6', '#f59e0b', '#ec4899'],
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
          y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8', stepSize: 1 } }
        }
      }
    });
  }

  // 3. Trends Line Chart
  const trendCtx = document.getElementById('trendChart');
  if (trendCtx) {
    new Chart(trendCtx, {
      type: 'line',
      data: {
        labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6'],
        datasets: [
          {
            label: 'Failures Caught',
            data: [12, 19, 14, 21, 16, 18],
            borderColor: '#f59e0b',
            backgroundColor: 'rgba(245, 158, 11, 0.1)',
            fill: true,
            tension: 0.35
          },
          {
            label: 'Auto-Fixed PRs Merged',
            data: [11, 18, 13, 20, 16, 18],
            borderColor: '#06b6d4',
            backgroundColor: 'rgba(6, 182, 212, 0.1)',
            fill: true,
            tension: 0.35
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: '#94a3b8' } } },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
          y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } }
        }
      }
    });
  }

  // 4. Agent Latency Horizontal Bar
  const agentCtx = document.getElementById('agentPerfChart');
  if (agentCtx) {
    const agents = data.agents || [
      { agent_name: 'Dispatcher', avg_latency_ms: 310.5 },
      { agent_name: 'Context Gatherer', avg_latency_ms: 480.2 },
      { agent_name: 'Engineer', avg_latency_ms: 950.0 },
      { agent_name: 'Reviewer', avg_latency_ms: 520.4 }
    ];

    new Chart(agentCtx, {
      type: 'bar',
      data: {
        labels: agents.map(a => a.agent_name),
        datasets: [{
          label: 'Avg Latency (ms)',
          data: agents.map(a => a.avg_latency_ms),
          backgroundColor: '#8b5cf6',
          borderRadius: 6
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
          y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } }
        }
      }
    });
  }
}
