const API = 'http://localhost:8000';
const MONITOR_KEY = ''; // Set your MONITOR_API_KEY here

let token = localStorage.getItem('chronos_token');

// --- Helpers ---

function authHeaders() {
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
  };
}

async function request(method, path, body = null, extraHeaders = {}) {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: { ...authHeaders(), ...extraHeaders },
    body: body ? JSON.stringify(body) : null,
  });
  const data = res.ok ? await res.json().catch(() => null) : null;
  return { ok: res.ok, status: res.status, data };
}

function badge(status) {
  return `<span class="badge badge-${status}">${status}</span>`;
}

function fmt(dt) {
  if (!dt) return '—';
  return new Date(dt).toLocaleString();
}

function show(id) { document.getElementById(id).classList.remove('hidden'); }
function hide(id) { document.getElementById(id).classList.add('hidden'); }
function setText(id, val) { document.getElementById(id).textContent = val; }

// --- Boot ---

if (token) showApp();
else showAuth();

function showAuth() {
  show('auth-screen');
  hide('app-screen');
}

function showApp() {
  hide('auth-screen');
  show('app-screen');
  loadJobs();
}

// --- Auth tabs ---

document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    if (tab.dataset.tab === 'login') {
      show('login-form'); hide('register-form');
    } else {
      hide('login-form'); show('register-form');
    }
  });
});

// --- Login ---

document.getElementById('login-form').addEventListener('submit', async e => {
  e.preventDefault();
  setText('login-error', '');
  const { ok, data } = await request('POST', '/auth/login', {
    username: document.getElementById('login-username').value,
    password: document.getElementById('login-password').value,
  });
  if (ok) {
    token = data.access_token;
    localStorage.setItem('chronos_token', token);
    showApp();
  } else {
    setText('login-error', 'Invalid credentials.');
  }
});

// --- Register ---

document.getElementById('register-form').addEventListener('submit', async e => {
  e.preventDefault();
  setText('register-error', '');
  const username = document.getElementById('reg-username').value;
  const password = document.getElementById('reg-password').value;
  const { ok, status } = await request('POST', '/auth/register', {
    username,
    email: document.getElementById('reg-email').value,
    password,
  });
  if (ok) {
    const loginRes = await request('POST', '/auth/login', { username, password });
    if (loginRes.ok) {
      token = loginRes.data.access_token;
      localStorage.setItem('chronos_token', token);
      showApp();
    }
  } else {
    setText('register-error', status === 400 ? 'Username or email already taken.' : 'Registration failed.');
  }
});

// --- Logout ---

document.getElementById('logout-btn').addEventListener('click', () => {
  token = null;
  localStorage.removeItem('chronos_token');
  showAuth();
});

// --- Nav ---

document.querySelectorAll('.nav-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
    show(`view-${tab.dataset.view}`);
    if (tab.dataset.view === 'jobs') loadJobs();
    if (tab.dataset.view === 'monitor') loadMonitor();
  });
});

// --- Jobs ---

async function loadJobs() {
  const { ok, data } = await request('GET', '/jobs');
  if (!ok) return;
  const tbody = document.getElementById('jobs-tbody');
  if (!data.length) {
    tbody.innerHTML = '';
    show('jobs-empty');
    return;
  }
  hide('jobs-empty');
  tbody.innerHTML = data.map(job => `
    <tr>
      <td>
        <strong>${esc(job.name)}</strong>
        ${job.description ? `<br><small class="hint">${esc(job.description)}</small>` : ''}
      </td>
      <td>${job.job_type}</td>
      <td>
        ${job.schedule_type}
        ${job.recurrence_pattern ? `<br><small class="hint">${esc(job.recurrence_pattern)}</small>` : ''}
      </td>
      <td>${badge(job.status)}</td>
      <td>${fmt(job.execution_time)}</td>
      <td>
        <button class="action-btn" onclick="loadExecutions('${job.id}')">History</button>
        ${['pending', 'scheduled'].includes(job.status)
          ? `<button class="action-btn danger" onclick="cancelJob('${job.id}')">Cancel</button>`
          : ''}
      </td>
    </tr>
  `).join('');
}

async function cancelJob(id) {
  if (!confirm('Cancel this job?')) return;
  const { ok } = await request('POST', `/jobs/${id}/cancel`);
  if (ok) loadJobs();
}

async function loadExecutions(jobId) {
  const { ok, data } = await request('GET', `/jobs/${jobId}/executions`);
  if (!ok) return;
  show('executions-panel');
  const tbody = document.getElementById('executions-tbody');
  if (!data.length) {
    tbody.innerHTML = '';
    show('executions-empty');
    return;
  }
  hide('executions-empty');
  tbody.innerHTML = data.map(ex => `
    <tr>
      <td>${fmt(ex.started_at)}</td>
      <td>${fmt(ex.completed_at)}</td>
      <td>${badge(ex.status)}</td>
      <td><span class="log-output" title="${esc(ex.log_output || '')}">${esc(ex.log_output || '—')}</span></td>
      <td><span class="log-output" title="${esc(ex.error_message || '')}">${esc(ex.error_message || '—')}</span></td>
    </tr>
  `).join('');
}

document.getElementById('close-executions').addEventListener('click', () => hide('executions-panel'));
document.getElementById('refresh-jobs').addEventListener('click', loadJobs);

// --- Submit ---

const jobTypeSelect = document.getElementById('job-type');
const scheduleTypeSelect = document.getElementById('schedule-type');

jobTypeSelect.addEventListener('change', () => {
  hide('payload-script'); hide('payload-api'); hide('payload-data');
  const map = { script: 'payload-script', api_call: 'payload-api', data_process: 'payload-data' };
  show(map[jobTypeSelect.value]);
});

scheduleTypeSelect.addEventListener('change', () => {
  if (scheduleTypeSelect.value === 'one_time') {
    show('schedule-one-time'); hide('schedule-recurring');
  } else {
    hide('schedule-one-time'); show('schedule-recurring');
  }
});

document.getElementById('submit-form').addEventListener('submit', async e => {
  e.preventDefault();
  hide('submit-success');
  setText('submit-error', '');

  const jobType = jobTypeSelect.value;
  const scheduleType = scheduleTypeSelect.value;

  let payload = {};
  if (jobType === 'script') {
    const args = document.getElementById('script-args').value.trim();
    payload = {
      script_path: document.getElementById('script-path').value,
      args: args ? args.split(/\s+/) : [],
      env: {},
    };
  } else if (jobType === 'api_call') {
    const bodyText = document.getElementById('api-body').value.trim();
    let parsedBody = null;
    if (bodyText) {
      try { parsedBody = JSON.parse(bodyText); }
      catch { setText('submit-error', 'Body is not valid JSON.'); return; }
    }
    payload = {
      url: document.getElementById('api-url').value,
      method: document.getElementById('api-method').value,
      headers: {},
      body: parsedBody,
    };
  }

  const body = {
    name: document.getElementById('job-name').value,
    job_type: jobType,
    payload,
    schedule_type: scheduleType,
  };

  if (scheduleType === 'one_time') {
    const dt = document.getElementById('execution-time').value;
    if (!dt) { setText('submit-error', 'Execution time is required.'); return; }
    body.execution_time = new Date(dt).toISOString();
  } else {
    const pattern = document.getElementById('recurrence-pattern').value.trim();
    if (!pattern) { setText('submit-error', 'Cron expression is required.'); return; }
    body.recurrence_pattern = pattern;
  }

  const { ok, status } = await request('POST', '/jobs', body);
  if (ok) {
    document.getElementById('submit-form').reset();
    hide('payload-api'); hide('payload-data'); show('payload-script');
    show('schedule-one-time'); hide('schedule-recurring');
    const msg = document.getElementById('submit-success');
    msg.textContent = 'Job submitted successfully.';
    show('submit-success');
  } else {
    setText('submit-error', status === 422 ? 'Invalid input — check all fields.' : 'Failed to submit job.');
  }
});

// --- Monitor ---

async function loadMonitor() {
  if (!MONITOR_KEY) {
    show('monitor-key-missing');
    return;
  }
  hide('monitor-key-missing');

  const extra = { 'X-Monitor-Key': MONITOR_KEY };

  const healthRes = await request('GET', '/monitor/health', null, extra);
  if (healthRes.ok) {
    document.getElementById('health-counts').innerHTML = Object.entries(healthRes.data)
      .map(([k, v]) => `
        <div class="count-card">
          <div class="count">${v}</div>
          <div class="label">${k}</div>
        </div>
      `).join('');
  }

  const failRes = await request('GET', '/monitor/failures', null, extra);
  if (failRes.ok) {
    const failures = failRes.data;
    const tbody = document.getElementById('failures-tbody');
    if (!failures.length) {
      tbody.innerHTML = '';
      show('failures-empty');
      return;
    }
    hide('failures-empty');
    tbody.innerHTML = failures.map(f => `
      <tr>
        <td>${esc(f.name)}</td>
        <td>${f.retry_count} / ${f.max_retries}</td>
        <td><span class="log-output" title="${esc(f.last_error || '')}">${esc(f.last_error || '—')}</span></td>
        <td>${fmt(f.updated_at)}</td>
      </tr>
    `).join('');
  }
}

document.getElementById('refresh-monitor').addEventListener('click', loadMonitor);

// --- XSS protection ---

function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
