/**
 * SH-CICD Main JavaScript
 * Shared utilities, toast manager, modal handler
 */

// Toast notification helper
function showToast(message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  
  let icon = 'info-circle';
  if (type === 'success') icon = 'check-circle';
  if (type === 'danger') icon = 'exclamation-triangle';

  toast.innerHTML = `
    <i class="fas fa-${icon}"></i>
    <span>${message}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Modal open/close helpers
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.style.display = 'flex';
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.style.display = 'none';
  }
}

// Close modal when clicking outside content
window.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.style.display = 'none';
  }
});

// Mobile sidebar toggle
function toggleSidebar() {
  const sidebar = document.querySelector('.sidebar');
  if (sidebar) {
    sidebar.classList.toggle('open');
  }
}

// ==========================================
// CONNECT GITHUB REPOSITORY MODAL HELPERS
// ==========================================
function showConnectTab(tabNum) {
  // Update buttons
  for (let i = 1; i <= 4; i++) {
    const btn = document.getElementById(`tab-btn-${i}`);
    const content = document.getElementById(`connect-tab-${i}`);
    if (btn) {
      if (i === tabNum) {
        btn.classList.remove('btn-secondary');
        btn.classList.add('btn-primary');
      } else {
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-secondary');
      }
    }
    if (content) {
      content.style.display = i === tabNum ? 'block' : 'none';
    }
  }

  if (tabNum === 3) {
    loadModalWorkflowYaml();
  } else if (tabNum === 4) {
    const whUrl = document.getElementById('modal_webhook_url')?.value || 'https://your-tunnel.ngrok-free.app/webhook/github';
    const preview = document.getElementById('secretValuePreview');
    if (preview) preview.textContent = whUrl;
  }
}

async function verifyRepoModalAccess() {
  const token = document.getElementById('modal_gh_token')?.value.trim();
  const repo = document.getElementById('modal_gh_repo')?.value.trim();
  const resultSpan = document.getElementById('repoVerifyResult');
  if (resultSpan) {
    resultSpan.innerHTML = '<span style="color: var(--cyan);"><i class="fas fa-spinner fa-spin"></i> Validating access...</span>';
  }

  try {
    const res = await fetch('/api/connect-repo/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: token, repo_name: repo })
    });
    const data = await res.json();
    if (data.valid) {
      if (resultSpan) {
        resultSpan.innerHTML = `<span style="color: var(--success);"><i class="fas fa-check-circle"></i> Connected to ${data.repo || repo}! (${data.mode.toUpperCase()} mode)</span>`;
      }
      showToast(`Repository ${repo || 'access'} verified successfully!`, 'success');
    } else {
      if (resultSpan) {
        resultSpan.innerHTML = `<span style="color: var(--danger);"><i class="fas fa-times-circle"></i> ${data.error || 'Access failed'}</span>`;
      }
      showToast(`Verification failed: ${data.error || 'Check token'}`, 'danger');
    }
  } catch (err) {
    if (resultSpan) {
      resultSpan.innerHTML = `<span style="color: var(--danger);"><i class="fas fa-exclamation-triangle"></i> Network error</span>`;
    }
    showToast('Failed to contact server verification endpoint.', 'danger');
  }
}

async function autoRegisterWebhookFromModal() {
  const token = document.getElementById('modal_gh_token')?.value.trim();
  const repo = document.getElementById('modal_gh_repo')?.value.trim();
  const webhookUrl = document.getElementById('modal_webhook_url')?.value.trim();
  const secret = document.getElementById('modal_webhook_secret')?.value.trim();
  const resultSpan = document.getElementById('webhookRegResult');

  if (!webhookUrl) {
    showToast('Please specify a webhook URL.', 'danger');
    return;
  }

  if (resultSpan) {
    resultSpan.innerHTML = '<span style="color: var(--cyan);"><i class="fas fa-spinner fa-spin"></i> Registering on GitHub...</span>';
  }

  try {
    const res = await fetch('/api/connect-repo/setup-webhook', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        token: token,
        repo_name: repo,
        webhook_url: webhookUrl,
        webhook_secret: secret
      })
    });
    const data = await res.json();
    if (data.success) {
      if (resultSpan) {
        resultSpan.innerHTML = `<span style="color: var(--success);"><i class="fas fa-check-circle"></i> Webhook created on GitHub!</span>`;
      }
      showToast('Webhook registered successfully on your repository!', 'success');
    } else {
      if (resultSpan) {
        resultSpan.innerHTML = `<span style="color: var(--warning);"><i class="fas fa-info-circle"></i> ${data.error || 'Notice'}</span>`;
      }
      showToast(data.error || 'Could not auto-register webhook. Configure manually.', 'info');
    }
  } catch (err) {
    if (resultSpan) {
      resultSpan.innerHTML = `<span style="color: var(--danger);">Registration error</span>`;
    }
    showToast('Error registering webhook.', 'danger');
  }
}

async function loadModalWorkflowYaml() {
  const codeBlock = document.getElementById('modalWorkflowYamlCode');
  if (!codeBlock) return;
  const webhookUrl = document.getElementById('modal_webhook_url')?.value.trim() || 'https://your-tunnel.ngrok-free.app/webhook/github';

  try {
    const res = await fetch(`/api/connect-repo/workflow-yaml?webhook_url=${encodeURIComponent(webhookUrl)}`);
    const data = await res.json();
    codeBlock.textContent = data.yaml;
  } catch (e) {
    codeBlock.textContent = '# Failed to load workflow YAML';
  }
}

function copyModalWorkflowYaml() {
  const codeBlock = document.getElementById('modalWorkflowYamlCode');
  if (codeBlock && codeBlock.textContent) {
    navigator.clipboard.writeText(codeBlock.textContent).then(() => {
      showToast('Workflow YAML copied to clipboard!', 'success');
    }).catch(() => {
      showToast('Could not copy to clipboard.', 'danger');
    });
  }
}

function copyModalField(fieldId) {
  const input = document.getElementById(fieldId);
  if (input && input.value) {
    navigator.clipboard.writeText(input.value).then(() => {
      showToast('Copied to clipboard!', 'success');
    });
  }
}

