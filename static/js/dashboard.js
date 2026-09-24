/**
 * Dashboard interactivity & Multi-Agent pipeline simulation
 */

document.addEventListener('DOMContentLoaded', () => {
  // Mini chart on dashboard if canvas exists
  initMiniChart();
});

function initMiniChart() {
  const ctx = document.getElementById('miniTrendChart');
  if (!ctx) return;

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
      datasets: [
        {
          label: 'Failures Detected',
          data: [4, 2, 6, 3, 5, 2, 4],
          borderColor: '#ef4444',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          fill: true,
          tension: 0.4
        },
        {
          label: 'Auto-Healed PRs',
          data: [4, 2, 5, 3, 5, 2, 4],
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          fill: true,
          tension: 0.4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
          labels: { color: '#94a3b8', font: { family: 'Poppins' } }
        }
      },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#64748b' } },
        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#64748b', stepSize: 1 } }
      }
    }
  });
}

// Preset failure scenarios
const SCENARIOS = {
  syntax: {
    workflow_name: "Python CI Suite",
    error_type: "SyntaxError",
    error_message: "SyntaxError: expected ':' (calculator.py, line 4)",
    raw_logs: `Run python -m py_compile demo_repo/calculator.py
  File "demo_repo/calculator.py", line 4
    def add(a, b)
                 ^
SyntaxError: expected ':'
Error: Process completed with exit code 1.`
  },
  zerodiv: {
    workflow_name: "Integration Test Pipeline",
    error_type: "ZeroDivisionError",
    error_message: "ZeroDivisionError: division by zero in calculate_average",
    raw_logs: `FAILED demo_repo/test_calculator.py::TestCalculator::test_calculate_average - ZeroDivisionError: division by zero
File "demo_repo/calculator.py", line 28, in calculate_average
    return sum(numbers) / len(numbers)
ZeroDivisionError: division by zero
Error: Process completed with exit code 1.`
  },
  assertion: {
    workflow_name: "Unit Test Verification",
    error_type: "AssertionError",
    error_message: "AssertionError: 4.0 != 5.0 in divide test",
    raw_logs: `FAILED demo_repo/test_calculator.py::TestCalculator::test_divide
AssertionError: 4.0 != 5.0
File "demo_repo/test_calculator.py", line 25, in test_divide
    self.assertEqual(divide(10, 2), 5.0)
Error: Process completed with exit code 1.`
  }
};

function selectScenario(key) {
  const data = SCENARIOS[key];
  if (data) {
    document.getElementById('simWorkflow').value = data.workflow_name;
    document.getElementById('simErrorType').value = data.error_type;
    document.getElementById('simLogs').value = data.raw_logs;
  }
}

async function triggerLiveSimulation() {
  const workflow_name = document.getElementById('simWorkflow').value;
  const error_type = document.getElementById('simErrorType').value;
  const raw_logs = document.getElementById('simLogs').value;

  if (!raw_logs.trim()) {
    showToast("Please enter failure logs to simulate.", "danger");
    return;
  }

  closeModal('simulationModal');
  showToast("Pipeline failure detected! Initiating AI agents...", "info");

  // Reset Stepper
  const nodes = document.querySelectorAll('.stepper-node');
  const arrows = document.querySelectorAll('.stepper-arrow');
  nodes.forEach(n => n.className = 'stepper-node');
  arrows.forEach(a => a.className = 'stepper-arrow');

  // Step 1: Dispatcher
  nodes[0].classList.add('active');
  arrows[0].classList.add('active');

  try {
    const payload = {
      workflow_name,
      error_type,
      raw_logs,
      repo_name: "demo-user/sh-cicd-demo"
    };

    // Animate sequential flow for clear demonstration
    setTimeout(() => {
      nodes[0].classList.remove('active');
      nodes[0].classList.add('completed');
      nodes[1].classList.add('active');
      arrows[1].classList.add('active');
      showToast("Dispatcher categorized error. Context Gatherer inspecting repo...", "info");
    }, 1200);

    setTimeout(() => {
      nodes[1].classList.remove('active');
      nodes[1].classList.add('completed');
      nodes[2].classList.add('active');
      arrows[2].classList.add('active');
      showToast("Context loaded. Engineer Agent synthesizing patch...", "info");
    }, 2400);

    setTimeout(() => {
      nodes[2].classList.remove('active');
      nodes[2].classList.add('completed');
      nodes[3].classList.add('active');
      showToast("Patch generated and verified. Reviewer running security audit...", "info");
    }, 3600);

    const res = await fetch('/api/simulate-failure', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const result = await res.json();

    setTimeout(() => {
      nodes[3].classList.remove('active');
      nodes[3].classList.add('completed');

      if (result.success) {
        showToast(`Fix Approved! Created Auto-Fixed PR #${result.pull_request.pr_number}`, "success");
        // Reload after 1.5 seconds to refresh tables and stats
        setTimeout(() => window.location.reload(), 1500);
      } else {
        showToast(`Fix Rejected by Reviewer: ${result.verdict}`, "danger");
      }
    }, 4500);

  } catch (err) {
    showToast("Simulation error: " + err.message, "danger");
  }
}

// Inspect Failure details modal
async function viewFailureDetails(failureId) {
  try {
    const res = await fetch(`/api/failures/${failureId}`);
    const data = await res.json();
    if (!data.failure) return;

    const f = data.failure;
    const content = `
      <div style="display:flex; justify-content:space-between; margin-bottom:15px;">
        <h4>${f.workflow_name} <span style="font-size:0.8rem; color:#94a3b8;">(${f.repo_name})</span></h4>
        <span class="badge ${f.status === 'RESOLVED' ? 'badge-success' : 'badge-danger'}">${f.status}</span>
      </div>
      <p style="margin-bottom:10px;"><strong>Error Type:</strong> <span class="badge badge-warning">${f.error_type}</span></p>
      <p style="margin-bottom:10px;"><strong>Message:</strong> ${f.error_message}</p>
      <div style="margin-top:15px;">
        <strong>Raw CI/CD Logs:</strong>
        <pre class="diff-viewer" style="margin-top:8px; max-height:220px; overflow-y:auto;">${f.raw_logs || 'No logs recorded.'}</pre>
      </div>
      <div style="margin-top:20px;">
        <strong>Agent Remediation Trail:</strong>
        <div style="margin-top:8px; display:flex; flex-direction:column; gap:8px;">
          ${(data.logs || []).map(l => `
            <div style="background:#0b1120; padding:10px; border-radius:6px; border-left:3px solid #06b6d4;">
              <div style="display:flex; justify-content:space-between; font-size:0.78rem; color:#94a3b8;">
                <strong>${l.agent_name} - ${l.action}</strong>
                <span>${l.timestamp}</span>
              </div>
              <p style="font-size:0.82rem; margin-top:4px; color:#e2e8f0;">${l.output_summary}</p>
            </div>
          `).join('') || '<p style="color:#64748b; font-size:0.82rem;">No agent logs recorded yet.</p>'}
        </div>
      </div>
    `;

    document.getElementById('failureDetailBody').innerHTML = content;
    openModal('failureDetailModal');
  } catch (err) {
    showToast("Failed to fetch failure details: " + err.message, "danger");
  }
}
