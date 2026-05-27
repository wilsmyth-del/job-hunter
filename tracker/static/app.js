let jobs = [];
let currentFilter = 'all';
let selectedJobId = null;
let currentView = 'tracker';
let scrapedJobs = [];
let sourcesSortField = 'scraped_at';
let sourcesSortDir = 'desc';
let pipelineSortField = 'date_updated';
let pipelineSortDir = 'desc';

const ACTIVE_STATUSES = ['applied', 'phone_screen', 'interview'];
const ARCHIVE_STATUSES = ['rejected', 'ghosted', 'not_relevant'];

const STATUS_LABELS = {
  watchlist: 'Watchlist',
  applied: 'Applied',
  phone_screen: 'Phone Screen',
  interview: 'Interview',
  offer: 'Offer',
  rejected: 'Rejected',
  ghosted: 'Ghosted',
  not_relevant: 'Not Relevant'
};

// ── Data ──────────────────────────────────────────────────────────────────────

async function loadJobs() {
  const res = await fetch(`/api/jobs?sort=${pipelineSortField}&dir=${pipelineSortDir}`);
  jobs = await res.json();
  updatePipelineSortHeaders();
  renderList();
  renderSummary();
}

function setSortPipeline(field) {
  if (pipelineSortField === field) {
    pipelineSortDir = pipelineSortDir === 'asc' ? 'desc' : 'asc';
  } else {
    pipelineSortField = field;
    pipelineSortDir = field === 'date_applied' || field === 'date_updated' || field === 'follow_up_date' ? 'desc' : 'asc';
  }
  loadJobs();
}

function updatePipelineSortHeaders() {
  const fields = { company: 'Company', role: 'Role', status: 'Status', date_applied: 'Applied', follow_up_date: 'Follow-up' };
  Object.entries(fields).forEach(([f, label]) => {
    const th = document.getElementById(`pth-${f}`);
    if (!th) return;
    if (f === pipelineSortField) {
      th.textContent = label + (pipelineSortDir === 'asc' ? ' ↑' : ' ↓');
    } else {
      th.textContent = label;
    }
  });
}

async function loadSummary() {
  const res = await fetch('/api/summary');
  return res.json();
}

// ── Render ────────────────────────────────────────────────────────────────────

function filterJobs() {
  const today = new Date().toISOString().split('T')[0];
  switch (currentFilter) {
    case 'active':    return jobs.filter(j => ACTIVE_STATUSES.includes(j.status));
    case 'watchlist': return jobs.filter(j => j.status === 'watchlist');
    case 'offer':     return jobs.filter(j => j.status === 'offer');
    case 'archive':   return jobs.filter(j => ARCHIVE_STATUSES.includes(j.status));
    default:          return jobs;
  }
}

function isOverdue(job) {
  if (!job.follow_up_date) return false;
  const today = new Date().toISOString().split('T')[0];
  return job.follow_up_date < today && !ARCHIVE_STATUSES.includes(job.status) && job.status !== 'offer';
}

function renderList() {
  const tbody = document.getElementById('job-tbody');
  const empty = document.getElementById('empty-state');
  const filtered = filterJobs();

  if (!filtered.length) {
    tbody.innerHTML = '';
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';

  tbody.innerHTML = filtered.map(job => {
    const overdue = isOverdue(job);
    const followUp = job.follow_up_date
      ? `<span class="date-text ${overdue ? 'follow-up-overdue' : ''}">${fmtDate(job.follow_up_date)}${overdue ? ' ⚠' : ''}</span>`
      : '<span class="date-text">—</span>';

    return `<tr data-id="${job.id}" class="${selectedJobId === job.id ? 'selected' : ''}" onclick="selectJob(${job.id})">
      <td><span class="company-name">${esc(job.company)}</span></td>
      <td><span class="role-name">${esc(job.role)}</span></td>
      <td><span class="badge badge-${job.status}">${STATUS_LABELS[job.status] || job.status}</span></td>
      <td><span class="date-text">${fmtDate(job.date_applied)}</span></td>
      <td>${followUp}</td>
    </tr>`;
  }).join('');
}

async function renderSummary() {
  const data = await loadSummary();
  const bar = document.getElementById('summary-bar');
  const counts = data.by_status;
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  const active = (counts.applied || 0) + (counts.phone_screen || 0) + (counts.interview || 0);
  const overdue = data.overdue_followups;

  bar.innerHTML = `
    <span>Total: <strong>${total}</strong></span>
    <span>Active: <strong>${active}</strong></span>
    ${counts.offer ? `<span>Offers: <strong>${counts.offer}</strong></span>` : ''}
    ${overdue ? `<span class="overdue">⚠ ${overdue} overdue follow-up${overdue > 1 ? 's' : ''}</span>` : ''}
  `;
}

// ── Detail Panel ──────────────────────────────────────────────────────────────

function selectJob(id) {
  selectedJobId = id;
  const job = jobs.find(j => j.id === id);
  if (!job) return;

  document.querySelectorAll('#job-tbody tr').forEach(tr => {
    tr.classList.toggle('selected', parseInt(tr.dataset.id) === id);
  });

  document.getElementById('detail-company').textContent = job.company;
  document.getElementById('detail-role').textContent = job.role;
  document.getElementById('detail-status').value = job.status;
  document.getElementById('detail-date-applied').value = job.date_applied || '';
  document.getElementById('detail-follow-up').value = job.follow_up_date || '';
  document.getElementById('detail-url').value = job.url || '';
  document.getElementById('detail-source').value = job.source || '';
  document.getElementById('detail-contact').value = job.contact || '';
  document.getElementById('detail-notes').value = job.notes || '';

  const link = document.getElementById('detail-link');
  link.href = job.url || '#';
  link.style.display = job.url ? 'inline-block' : 'none';

  document.getElementById('detail-panel').classList.remove('hidden');
}

function closeDetail() {
  selectedJobId = null;
  document.getElementById('detail-panel').classList.add('hidden');
  document.querySelectorAll('#job-tbody tr').forEach(tr => tr.classList.remove('selected'));
}

async function saveField(field, value) {
  if (!selectedJobId) return;
  const res = await fetch(`/api/jobs/${selectedJobId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ [field]: value })
  });
  const updated = await res.json();
  const idx = jobs.findIndex(j => j.id === selectedJobId);
  if (idx !== -1) jobs[idx] = updated;
  renderList();
  renderSummary();

  // Refresh detail header if company/role changed
  if (field === 'company') document.getElementById('detail-company').textContent = value;
  if (field === 'role') document.getElementById('detail-role').textContent = value;
  if (field === 'url') {
    const link = document.getElementById('detail-link');
    link.href = value || '#';
    link.style.display = value ? 'inline-block' : 'none';
  }
}

async function deleteJob() {
  if (!selectedJobId) return;
  const job = jobs.find(j => j.id === selectedJobId);
  if (!confirm(`Delete ${job.company} — ${job.role}?`)) return;
  await fetch(`/api/jobs/${selectedJobId}`, { method: 'DELETE' });
  jobs = jobs.filter(j => j.id !== selectedJobId);
  closeDetail();
  renderList();
  renderSummary();
}

async function blockDomain() {
  if (!selectedJobId) return;
  const job = jobs.find(j => j.id === selectedJobId);
  const url = job && job.url;
  if (!url) { alert('No URL on this job — nothing to block.'); return; }
  const res = await fetch('/api/block-domain', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url })
  });
  const data = await res.json();
  if (data.ok) {
    alert(`${data.domain} blocked — won't appear in future scrapes.`);
  } else {
    alert('Block failed: ' + (data.error || 'unknown error'));
  }
}

// ── Add Modal ─────────────────────────────────────────────────────────────────

function openAddModal() {
  document.getElementById('add-form').reset();
  document.getElementById('f-date-applied').value = today();
  document.getElementById('modal-overlay').classList.remove('hidden');
  document.getElementById('f-company').focus();
}

function closeModal(e) {
  if (e && e.target !== document.getElementById('modal-overlay')) return;
  document.getElementById('modal-overlay').classList.add('hidden');
}

async function submitAdd(e) {
  e.preventDefault();
  const data = {
    company: document.getElementById('f-company').value.trim(),
    role: document.getElementById('f-role').value.trim(),
    status: document.getElementById('f-status').value,
    date_applied: document.getElementById('f-date-applied').value,
    follow_up_date: document.getElementById('f-follow-up').value,
    url: document.getElementById('f-url').value.trim(),
    source: document.getElementById('f-source').value.trim(),
    contact: document.getElementById('f-contact').value.trim(),
    notes: document.getElementById('f-notes').value.trim()
  };
  const res = await fetch('/api/jobs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  const job = await res.json();
  jobs.unshift(job);
  document.getElementById('modal-overlay').classList.add('hidden');
  renderList();
  renderSummary();
  selectJob(job.id);
}

// ── Sources ───────────────────────────────────────────────────────────────────

async function loadSources() {
  const res = await fetch(`/api/scraped?sort=${sourcesSortField}&dir=${sourcesSortDir}`);
  scrapedJobs = await res.json();
  renderSources();
}

function setSortSources(field) {
  if (sourcesSortField === field) {
    sourcesSortDir = sourcesSortDir === 'asc' ? 'desc' : 'asc';
  } else {
    sourcesSortField = field;
    sourcesSortDir = field === 'scraped_at' ? 'desc' : 'asc';
  }
  loadSources();
}

function sortedSources() {
  return [...scrapedJobs];
}

function updateSortHeaders() {
  const fields = ['role', 'company', 'scraped_at'];
  fields.forEach(f => {
    const th = document.getElementById(`sort-th-${f}`);
    if (!th) return;
    const label = { role: 'Role', company: 'Company', scraped_at: 'Found' }[f];
    if (f === sourcesSortField) {
      th.textContent = label + (sourcesSortDir === 'asc' ? ' ↑' : ' ↓');
    } else {
      th.textContent = label;
    }
  });
}

function renderSources() {
  const tbody = document.getElementById('sources-tbody');
  const empty = document.getElementById('sources-empty');

  updateSortHeaders();

  if (!scrapedJobs.length) {
    tbody.innerHTML = '';
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';

  tbody.innerHTML = sortedSources().map(job => {
    const actionBtn = job.tracker_id
      ? `<span class="btn-added">Added</span>`
      : `<button class="btn-add" onclick="addToTracker('${esc(job.external_id)}')">+ Add</button>`;
    const dismissBtn = `<button class="btn-dismiss" onclick="dismissSource('${esc(job.external_id)}')" title="Dismiss">✕</button>`;
    const linkBtn = job.url
      ? `<a href="${esc(job.url)}" target="_blank" class="btn-secondary" style="padding:4px 10px;font-size:12px">↗</a>`
      : '';
    return `<tr>
      <td><span class="company-name">${esc(job.role)}</span></td>
      <td><span class="role-name">${esc(job.company || '—')}</span></td>
      <td><span class="date-text">${esc(job.location || '—')}</span></td>
      <td><span class="date-text">${esc(job.source || '—')}</span></td>
      <td><span class="date-text">${timeAgo(job.scraped_at)}</span></td>
      <td><div style="display:flex;gap:6px;align-items:center">${linkBtn}${actionBtn}${dismissBtn}</div></td>
    </tr>`;
  }).join('');
}

async function addToTracker(externalId) {
  const res = await fetch(`/api/scraped/${externalId}/add`, { method: 'POST' });
  if (res.ok) {
    await loadSources();
    renderSummary();
  }
}

async function dismissSource(externalId) {
  const res = await fetch(`/api/scraped/${externalId}/dismiss`, { method: 'POST' });
  if (res.ok) {
    scrapedJobs = scrapedJobs.filter(j => j.external_id !== externalId);
    renderSources();
  }
}

function exportTracker() {
  const a = document.createElement('a');
  a.href = '/api/export/tracker';
  a.download = 'job_tracker.csv';
  a.click();
}

function exportSources() {
  const a = document.createElement('a');
  a.href = '/api/export/sources';
  a.download = 'job_sources.csv';
  a.click();
}

function switchView(view) {
  currentView = view;
  const main = document.getElementById('main');
  const sourcesView = document.getElementById('sources-view');
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));

  if (view === 'sources') {
    main.classList.add('hidden');
    sourcesView.classList.remove('hidden');
    document.querySelector('[data-view="sources"]').classList.add('active');
    loadSources();
  } else {
    sourcesView.classList.add('hidden');
    main.classList.remove('hidden');
  }
}

// ── Filters ───────────────────────────────────────────────────────────────────

document.querySelectorAll('.filter-btn:not([data-view])').forEach(btn => {
  btn.addEventListener('click', () => {
    if (currentView !== 'tracker') switchView('tracker');
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentFilter = btn.dataset.filter;
    closeDetail();
    renderList();
  });
});

document.querySelector('[data-view="sources"]').addEventListener('click', () => {
  switchView('sources');
});

// ── Utils ─────────────────────────────────────────────────────────────────────

function esc(str) {
  return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function fmtDate(iso) {
  if (!iso) return '—';
  const [y, m, d] = iso.split('-');
  return `${m}/${d}/${y.slice(2)}`;
}

function today() {
  return new Date().toISOString().split('T')[0];
}

function timeAgo(isoStr) {
  if (!isoStr) return '—';
  const diff = Date.now() - new Date(isoStr + 'Z').getTime();
  const m = Math.floor(diff / 60000);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

// ── Keyboard ──────────────────────────────────────────────────────────────────

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    if (!document.getElementById('modal-overlay').classList.contains('hidden')) {
      document.getElementById('modal-overlay').classList.add('hidden');
    } else {
      closeDetail();
    }
  }
});

// ── Init ──────────────────────────────────────────────────────────────────────

loadJobs();
