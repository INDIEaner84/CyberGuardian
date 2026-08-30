/* CyberGuardian cockpit — intentionally plain browser JavaScript, no third-party runtime. */
(() => {
  'use strict';

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const motionPreferred = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let state = null;
  let currentView = 'command';
  let planFilter = 'all';
  let offlineMode = false;
  let toastTimer;
  let backgroundFrame;
  let driftFrame;

  const fallbackState = {
    schema: 'cyberguardian-control-plane-v1',
    version: '0.3.0',
    updated_at: new Date().toISOString(),
    settings: { safe_mode: true, simulation_mode: true },
    agents: [
      { id: 'agent-orbit', name: 'ORBIT', role: 'Triage & correlation', focus: 'cross-agent context', status: 'online', signal: 92, last_seen: new Date().toISOString() },
      { id: 'agent-sentinel', name: 'SENTINEL', role: 'Exposure watch', focus: 'approved lab perimeter', status: 'online', signal: 87, last_seen: new Date().toISOString() },
      { id: 'agent-kai', name: 'KAI', role: 'Deception lab', focus: 'virtual honeypot telemetry', status: 'online', signal: 78, last_seen: new Date().toISOString() },
      { id: 'agent-mika', name: 'MIKA', role: 'Evidence keeper', focus: 'chain of custody', status: 'standby', signal: 64, last_seen: new Date().toISOString() }
    ],
    plans: [
      { id: 'PLN-001', title: 'Edge-Layer Baseline', objective: 'Inventar der exponierten Dienste in der genehmigten Laborzone festhalten.', owner: 'SENTINEL', status: 'active', priority: 'high', progress: 68, broadcast: true, updated_at: new Date().toISOString() },
      { id: 'PLN-002', title: 'Honeypot Relay v2', objective: 'Virtuelle Signale für die Verteidigungsübung sauber korrelieren.', owner: 'KAI', status: 'queued', priority: 'normal', progress: 36, broadcast: true, updated_at: new Date().toISOString() },
      { id: 'PLN-003', title: 'Evidence Chain', objective: 'Erkenntnisse lokal, nachvollziehbar und ohne Gegenmaßnahmen ablegen.', owner: 'ORBIT', status: 'done', priority: 'low', progress: 100, broadcast: true, updated_at: new Date().toISOString() }
    ],
    honeypots: [
      { id: 'HP-001', name: 'KASA-API', service: 'SSH decoy', port: 2222, profile: 'Neo-Tokyo edge', status: 'active', mode: 'simulation', signals: 14, last_signal: new Date().toISOString() },
      { id: 'HP-002', name: 'MIRAI-VAULT', service: 'HTTP decoy', port: 8088, profile: 'quiet archive', status: 'standby', mode: 'simulation', signals: 0, last_signal: null }
    ],
    incidents: [{ id: 'INC-014', honeypot_id: 'HP-001', source: '203.0.113.42', tactic: 'credential probe', severity: 'high', status: 'open', simulated: true, created_at: new Date().toISOString() }],
    honeypot_logs: [{ id: 'SIG-014', honeypot_id: 'HP-001', source: '203.0.113.42', destination: 'KASA-API:2222', tactic: 'credential probe', severity: 'high', action: 'captured / no response', simulated: true, created_at: new Date().toISOString() }],
    messages: [{ id: 'MSG-001', from: 'ORBIT', to: 'ALL AGENTS', kind: 'broadcast', text: 'SOT synchronisiert: Alle defensiven Agenten sehen denselben Kontext.', created_at: new Date().toISOString() }],
    activity: [{ id: 'EVT-001', kind: 'policy', tone: 'green', text: 'Safe mode bestätigt: Nur lokale Simulation und defensive Beobachtung.', created_at: new Date().toISOString() }],
    stats: { online_agents: 3, total_agents: 4, active_plans: 1, open_incidents: 1, active_honeypots: 1, signals_today: 1 }
  };

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function escapeHTML(value) {
    return String(value ?? '').replace(/[&<>'"]/g, (character) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    }[character]));
  }

  function initials(name) {
    return String(name || 'AG').replace(/[^A-Za-z0-9]/g, '').slice(0, 2).toUpperCase() || 'AG';
  }

  function formatTime(value, withSeconds = false) {
    if (!value) return '--:--';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '--:--';
    return date.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', ...(withSeconds ? { second: '2-digit' } : {}) });
  }

  function relativeTime(value) {
    if (!value) return 'NO SIGNAL';
    const time = new Date(value).getTime();
    if (Number.isNaN(time)) return 'UNKNOWN';
    const seconds = Math.max(0, Math.floor((Date.now() - time) / 1000));
    if (seconds < 10) return 'JUST NOW';
    if (seconds < 60) return `${seconds}s AGO`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m AGO`;
    return `${Math.floor(minutes / 60)}h AGO`;
  }

  function displayStatus(status) {
    return ({ active: 'ACTIVE', queued: 'QUEUED', blocked: 'BLOCKED', done: 'DONE' }[status] || String(status || 'UNKNOWN').toUpperCase());
  }

  function displayKind(kind) {
    return String(kind || 'event').replaceAll('.', ' ').toUpperCase();
  }

  const tabGuides = {
    command: {
      symbol: '◈', kicker: 'YOU ARE HERE / STARTPUNKT', title: 'COMMAND DECK',
      text: 'Hier liest du zuerst die Lage und entscheidest, welcher defensive Schritt als Nächstes gemeinsam verfolgt wird.',
      next: 'PLAN ANLEGEN', output: 'wird an alle Agenten broadcastet', action: 'plan', actionLabel: 'PLAN STARTEN'
    },
    mesh: {
      symbol: '✣', kicker: 'YOU ARE HERE / KOORDINATION', title: 'AGENT MESH',
      text: 'Hier siehst du, wer welchen Kontext trägt. Jeder Plan bleibt sichtbar, bis er abgeschlossen oder bewusst blockiert ist.',
      next: 'PLAN BROADCASTEN', output: 'gemeinsamer Status statt Einzelchat', action: 'plan', actionLabel: 'PLAN ANLEGEN'
    },
    lab: {
      symbol: '⌁', kicker: 'YOU ARE HERE / DEFENSE LAB', title: 'HONEYPOT LAB',
      text: 'Hier baust du virtuelle Decoys für sichere Übungen. Erst anlegen, dann aktivieren, dann ein synthetisches Signal testen.',
      next: 'DECOY ERSTELLEN', output: 'kein Port · keine Antwort · kein Angriff', action: 'honeypot', actionLabel: 'DECOY ANLEGEN'
    },
    drift: {
      symbol: '⟡', kicker: 'YOU ARE HERE / VISUAL READOUT', title: 'SIGNAL DRIFT',
      text: 'Diese Ansicht zeigt Systemaktivität als Muster. Sie ist Orientierung, nicht die Detailanalyse eines Incidents.',
      next: 'SIGNAL DETAILS', output: 'für Quelle und Taktik ins Honeypot Lab', action: 'lab', actionLabel: 'LAB ÖFFNEN'
    },
    about: {
      symbol: '?', kicker: 'YOU ARE HERE / ORIENTATION', title: 'PROJECT BRIEF',
      text: 'Hier erfährst du, warum CyberGuardian existiert, wie die Control Plane arbeitet und wo die Sicherheitsgrenzen liegen.',
      next: 'ERSTEN SCHRITT', output: 'zurück zum Lagebild', action: 'command', actionLabel: 'COCKPIT ÖFFNEN'
    }
  };

  function renderTabGuide(view) {
    const guide = tabGuides[view] || tabGuides.command;
    $('#tabGuideSymbol').textContent = guide.symbol;
    $('#tabGuideKicker').textContent = guide.kicker;
    $('#tabGuideTitle').textContent = guide.title;
    $('#tabGuideText').textContent = guide.text;
    $('#tabGuideNext').textContent = guide.next;
    $('#tabGuideOutput').textContent = guide.output;
    const action = $('#tabGuideAction');
    action.textContent = `${guide.actionLabel} ↗`;
    action.dataset.guideAction = guide.action;
  }

  async function request(path, options = {}) {
    const response = await fetch(path, {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options
    });
    let payload = {};
    try { payload = await response.json(); } catch (_) { /* empty response */ }
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    return payload;
  }

  async function loadState(showError = false) {
    try {
      const next = await request('/api/state');
      state = next;
      offlineMode = false;
      if ($('#syncState')) $('#syncState').textContent = 'LIVE';
      renderAll();
      return true;
    } catch (error) {
      if (!state) state = clone(fallbackState);
      offlineMode = true;
      if ($('#syncState')) $('#syncState').textContent = 'LOCAL DEMO';
      renderAll();
      if (showError) toast('Control Plane nicht erreichbar — lokale Demo aktiv.', 'error');
      return false;
    }
  }

  async function mutate(path, method, body, successMessage) {
    if (offlineMode) {
      toast('Server nicht verbunden. Starte python3 server.py für persistente Änderungen.', 'error');
      return false;
    }
    try {
      await request(path, { method, body: JSON.stringify(body || {}) });
      await loadState();
      if (successMessage) toast(successMessage, 'success');
      return true;
    } catch (error) {
      toast(error.message || 'Aktion konnte nicht gespeichert werden.', 'error');
      return false;
    }
  }

  function toast(message, tone = 'normal') {
    const stack = $('#toastStack');
    if (!stack) return;
    const item = document.createElement('div');
    item.className = `toast ${tone === 'error' ? 'toast--error' : tone === 'success' ? 'toast--success' : ''}`;
    item.textContent = message;
    stack.appendChild(item);
    $('#confirmToast').textContent = message;
    window.setTimeout(() => item.remove(), 4300);
  }

  function renderAll() {
    if (!state) return;
    renderMetrics();
    renderPlans();
    renderAgents();
    renderHoneypots();
    renderActivity();
    renderMesh();
    renderLab();
    renderDriftReadouts();
    $('#lastSync').textContent = formatTime(state.updated_at, true);
  }

  function renderMetrics() {
    const stats = state.stats || {};
    const metrics = [
      { label: 'AGENTS ONLINE', value: `${stats.online_agents || 0}`, unit: `/ ${stats.total_agents || 0}`, icon: '✣', color: '#70f3f2', rail: Math.round(((stats.online_agents || 0) / Math.max(stats.total_agents || 1, 1)) * 100) },
      { label: 'ACTIVE PLANS', value: `${stats.active_plans || 0}`, unit: 'IN MOTION', icon: '◈', color: '#ff9b52', rail: Math.min(100, ((stats.active_plans || 0) / Math.max(state.plans.length, 1)) * 100) },
      { label: 'OPEN INCIDENTS', value: `${stats.open_incidents || 0}`, unit: 'TO TRIAGE', icon: '◆', color: '#ff4c3a', rail: Math.min(100, ((stats.open_incidents || 0) / Math.max(state.incidents.length || 1, 1)) * 100) },
      { label: 'SIGNALS CAPTURED', value: `${stats.signals_today || 0}`, unit: 'SYNTHETIC', icon: '⌁', color: '#f168d4', rail: Math.min(100, ((stats.signals_today || 0) / 25) * 100) }
    ];
    $('#commandMetrics').innerHTML = metrics.map((metric) => `
      <article class="metric-card" style="--metric-color:${metric.color}">
        <div class="metric-card-top"><span>${metric.label}</span><span class="metric-card-icon">${metric.icon}</span></div>
        <strong class="metric-value">${escapeHTML(metric.value)} <small>${escapeHTML(metric.unit)}</small></strong>
        <div class="metric-rail"><i style="width:${Math.max(4, Math.min(100, metric.rail))}%"></i></div>
      </article>`).join('');
    $('#planCountAll').textContent = state.plans.length;
    $('#planCountActive').textContent = state.plans.filter((plan) => plan.status === 'active').length;
    $('#planCountQueued').textContent = state.plans.filter((plan) => plan.status === 'queued').length;
    $('#messageCount').textContent = `${state.messages.length} MESSAGES`;
    $('#meshMessageCount').textContent = String(state.messages.length).padStart(2, '0');
  }

  function planRow(plan) {
    const status = String(plan.status || 'queued').toLowerCase();
    return `<article class="plan-row" data-status="${escapeHTML(status)}">
      <span class="plan-id">${escapeHTML(plan.id)}</span>
      <div class="plan-main"><div class="plan-title-line"><strong class="plan-title">${escapeHTML(plan.title)}</strong><span class="status-pill status-pill--${escapeHTML(status)}">${displayStatus(status)}</span></div><p class="plan-objective">${escapeHTML(plan.objective)}</p><span class="plan-owner">↳ ${escapeHTML(plan.owner)} / BROADCASTED</span></div>
      <button class="plan-progress" data-cycle-plan="${escapeHTML(plan.id)}" title="Planstatus weiterführen"><span class="progress-value"><span>${escapeHTML(displayStatus(status))}</span><strong>${Math.round(plan.progress || 0)}%</strong></span><span class="progress-rail"><i style="width:${Math.max(0, Math.min(100, plan.progress || 0))}%"></i></span></button>
    </article>`;
  }

  function renderPlans() {
    const filtered = state.plans.filter((plan) => planFilter === 'all' || plan.status === planFilter);
    $('#planList').innerHTML = filtered.length ? filtered.slice(0, 6).map(planRow).join('') : '<div class="empty-state">NO PLANS IN THIS CHANNEL</div>';
    $$('.filter-tab').forEach((tab) => tab.classList.toggle('filter-tab--active', tab.dataset.planFilter === planFilter));
  }

  function renderAgents() {
    const sorted = [...state.agents].sort((a, b) => (a.status === 'online' ? 0 : 1) - (b.status === 'online' ? 0 : 1));
    $('#agentList').innerHTML = sorted.slice(0, 5).map((agent) => {
      const online = agent.status === 'online';
      return `<article class="agent-row"><span class="agent-avatar">${escapeHTML(initials(agent.name))}</span><div class="agent-info"><strong class="agent-name">${escapeHTML(agent.name)}</strong><span class="agent-role">${escapeHTML(agent.role)} · ${escapeHTML(agent.focus)}</span></div><span class="agent-status ${online ? '' : 'agent-status--standby'}"><i class="status-dot ${online ? 'status-dot--green' : ''}"></i>${online ? 'ONLINE' : 'STANDBY'}</span></article>`;
    }).join('');
  }

  function honeypotCard(pot, lab = false) {
    const active = pot.status === 'active';
    return `<article class="honeypot-card" data-pot-id="${escapeHTML(pot.id)}">
      <div class="honeypot-top"><strong>${escapeHTML(pot.name)}</strong><span class="pot-state ${active ? '' : 'pot-state--standby'}"><i class="status-dot ${active ? 'status-dot--green' : ''}"></i> ${active ? 'ACTIVE' : 'STANDBY'}</span></div>
      <p class="honeypot-service">${escapeHTML(pot.service)} <span>· :${escapeHTML(pot.port)}</span></p>
      <div class="honeypot-meta"><span>${escapeHTML(pot.profile)}</span><b>${escapeHTML(pot.signals)} SIGNALS</b></div>
      ${lab ? `<div class="pot-actions"><button class="pot-action" data-toggle-pot="${escapeHTML(pot.id)}">${active ? 'DEACTIVATE' : 'ACTIVATE'}</button><button class="pot-action" data-simulate-pot="${escapeHTML(pot.id)}">＋ TEST SIGNAL</button></div>` : ''}
    </article>`;
  }

  function renderHoneypots() {
    $('#honeypotRail').innerHTML = state.honeypots.slice(0, 4).map((pot) => honeypotCard(pot)).join('') || '<div class="empty-state">NO VIRTUAL DECOYS CONFIGURED</div>';
  }

  function renderActivity() {
    const items = state.activity.slice(0, 5);
    $('#activityList').innerHTML = items.length ? items.map((event) => `<article class="activity-item"><i class="activity-dot activity-dot--${escapeHTML(event.tone || 'cyan')}"></i><div><p class="activity-text">${escapeHTML(event.text)}</p><span class="activity-time">${escapeHTML(displayKind(event.kind))} · ${formatTime(event.created_at, true)}</span></div></article>`).join('') : '<div class="empty-state">ACTIVITY RIVER CLEAR</div>';
  }

  function renderMesh() {
    const positions = [[20, 25], [80, 24], [18, 77], [81, 76], [50, 50]];
    const nodes = state.agents.slice(0, 4).map((agent, index) => `<div class="mesh-node" style="left:${positions[index][0]}%;top:${positions[index][1]}%"><strong>${escapeHTML(agent.name)}</strong><small>${agent.status === 'online' ? 'ONLINE' : 'STANDBY'}</small></div>`).join('');
    const lineCoordinates = [[20, 25, 50, 50], [80, 24, 50, 50], [18, 77, 50, 50], [81, 76, 50, 50]];
    const lines = lineCoordinates.map(([x1, y1, x2, y2]) => {
      const dx = x2 - x1; const dy = y2 - y1; const length = Math.sqrt((dx * dx) + (dy * dy));
      const angle = Math.atan2(dy, dx) * (180 / Math.PI);
      return `<i class="mesh-map-line" style="left:${x1}%;top:${y1}%;width:${length}%;transform:rotate(${angle}deg)"></i>`;
    }).join('');
    $('#meshMap').innerHTML = `${lines}<div class="mesh-map-core"><strong>SOT</strong><small>ONE DO</small></div>${nodes}`;
    $('#messageList').innerHTML = state.messages.slice(0, 8).map((message) => `<article class="message-item"><div class="message-route"><strong>${escapeHTML(message.from)}</strong><span>→</span><strong>${escapeHTML(message.to)}</strong><small class="message-kind">${escapeHTML(message.kind)}</small></div><p class="message-text">${escapeHTML(message.text)}</p><time class="message-time">${formatTime(message.created_at, true)} UTC</time></article>`).join('') || '<div class="empty-state">NO HANDOFFS YET</div>';
    const columns = [
      ['active', 'IN MOTION', 'board-column'],
      ['queued', 'QUEUED', 'board-column board-column--queued'],
      ['blocked', 'BLOCKED', 'board-column board-column--blocked'],
      ['done', 'DONE', 'board-column board-column--done']
    ];
    $('#meshPlanBoard').innerHTML = columns.map(([status, label, className]) => {
      const plans = state.plans.filter((plan) => plan.status === status);
      return `<div class="${className}"><div class="board-column-heading"><span>${label}</span><b>${String(plans.length).padStart(2, '0')}</b></div>${plans.length ? plans.map((plan) => `<button class="board-plan" data-cycle-plan="${escapeHTML(plan.id)}"><small>${escapeHTML(plan.id)} · ${escapeHTML(plan.owner)}</small><strong>${escapeHTML(plan.title)}</strong><small>${Math.round(plan.progress || 0)}% / TAP TO ADVANCE</small></button>`).join('') : '<div class="empty-state">CLEAR</div>'}</div>`;
    }).join('');
  }

  function renderLab() {
    $('#labPotGrid').innerHTML = state.honeypots.map((pot) => honeypotCard(pot, true)).join('') || '<div class="empty-state">NO DECOYS — CREATE A VIRTUAL NODE</div>';
    const logItems = state.honeypot_logs.slice(0, 18);
    $('#signalLogCount').textContent = `${state.honeypot_logs.length} EVENTS`;
    const head = '<div class="signal-row signal-row--head"><span>ID</span><span>SOURCE</span><span>DESTINATION</span><span>TACTIC</span><span>SEVERITY</span><span>ACTION</span></div>';
    const rows = logItems.map((signal) => {
      const incident = state.incidents.find((item) => item.honeypot_id === signal.honeypot_id && item.source === signal.source && item.tactic === signal.tactic && new Date(item.created_at).getTime() === new Date(signal.created_at).getTime());
      const hp = state.honeypots.find((pot) => pot.id === signal.honeypot_id);
      const acknowledged = incident && incident.status !== 'open';
      return `<div class="signal-row"><span class="signal-cell signal-cell--id">${escapeHTML(signal.id)}</span><span class="signal-cell"><strong>${escapeHTML(signal.source)}</strong><small class="signal-simulated"> SYNTHETIC</small></span><span class="signal-cell">${escapeHTML(signal.destination || hp?.name || 'VIRTUAL DECOY')}</span><span class="signal-cell">${escapeHTML(signal.tactic)}</span><span class="severity severity--${escapeHTML(signal.severity)}">${escapeHTML(String(signal.severity).toUpperCase())}</span><span class="signal-cell">${acknowledged ? '<span class="signal-simulated">ACKNOWLEDGED</span>' : incident ? `<button class="ack-button" data-ack-incident="${escapeHTML(incident.id)}">ACKNOWLEDGE</button>` : '<span class="signal-simulated">CAPTURED</span>'}</span></div>`;
    }).join('');
    $('#signalTable').innerHTML = logItems.length ? head + rows : '<div class="empty-state">NO SIGNALS — LAB IS QUIET</div>';
  }

  function renderDriftReadouts() {
    const stats = state.stats || {};
    $('#driftSignalCount').textContent = String(stats.signals_today || 0).padStart(3, '0');
    $('#driftIncidentCount').textContent = String(stats.open_incidents || 0).padStart(2, '0');
    $('#driftMeshCount').textContent = `${Math.round(((stats.online_agents || 0) / Math.max(stats.total_agents || 1, 1)) * 100)}%`;
    $('#driftHoneypotCount').textContent = String(stats.active_honeypots || 0).padStart(2, '0');
  }

  function cyclePlan(planId) {
    const plan = state.plans.find((item) => item.id === planId);
    if (!plan) return;
    const next = ({ queued: 'active', active: 'done', done: 'queued', blocked: 'active' })[plan.status] || 'active';
    const nextProgress = next === 'done' ? 100 : next === 'active' ? Math.max(plan.progress || 0, 50) : 0;
    mutate(`/api/plans/${encodeURIComponent(planId)}`, 'PATCH', { status: next, progress: nextProgress }, `${planId} an den Mesh broadcastet: ${displayStatus(next)}.`);
  }

  function setView(view) {
    const allowed = ['command', 'mesh', 'lab', 'drift', 'about'];
    currentView = allowed.includes(view) ? view : 'command';
    $$('.view-panel').forEach((panel) => panel.classList.toggle('view-panel--active', panel.dataset.viewPanel === currentView));
    $$('.nav-item').forEach((button) => button.classList.toggle('nav-item--active', button.dataset.view === currentView));
    $('#viewCrumb').textContent = ({ command: 'COMMAND DECK', mesh: 'AGENT MESH', lab: 'HONEYPOT LAB', drift: 'SIGNAL DRIFT', about: 'PROJECT BRIEF' })[currentView];
    renderTabGuide(currentView);
    if (currentView === 'drift') startDriftCanvas();
  }

  function enterCockpit(view = 'command') {
    $('#startScreen').classList.add('is-hidden');
    $('#appView').classList.remove('is-hidden');
    setView(view);
    window.scrollTo({ top: 0, behavior: motionPreferred ? 'smooth' : 'auto' });
  }

  function openModal(name) {
    const backdrop = $('#modalBackdrop');
    const modal = $(`#${name}Modal`);
    if (!modal) return;
    backdrop.classList.remove('is-hidden');
    $$('.modal', backdrop).forEach((item) => item.classList.add('is-hidden'));
    modal.classList.remove('is-hidden');
    const first = $('input, textarea, select', modal);
    if (first) window.setTimeout(() => first.focus(), 30);
  }

  function closeModal() {
    $('#modalBackdrop').classList.add('is-hidden');
    $$('.modal', $('#modalBackdrop')).forEach((modal) => modal.classList.add('is-hidden'));
  }

  function randomSignalPayload() {
    const sources = ['198.51.100.24', '203.0.113.42', '192.0.2.77', '198.51.100.19'];
    const tactics = ['banner check', 'credential probe', 'path discovery', 'unexpected handshake'];
    const severities = ['low', 'medium', 'medium', 'high'];
    return { source: sources[Math.floor(Math.random() * sources.length)], tactic: tactics[Math.floor(Math.random() * tactics.length)], severity: severities[Math.floor(Math.random() * severities.length)] };
  }

  function simulateSignal(honeypotId) {
    const pot = state.honeypots.find((item) => item.id === honeypotId);
    if (!pot) return;
    if (pot.status !== 'active') {
      toast('Decoy ist standby — zuerst ACTIVATE wählen.', 'error');
      return;
    }
    mutate(`/api/honeypots/${encodeURIComponent(honeypotId)}/simulate`, 'POST', randomSignalPayload(), 'Testsignal sicher eingefangen — keine Antwort gesendet.');
  }

  function toggleHoneypot(honeypotId) {
    const pot = state.honeypots.find((item) => item.id === honeypotId);
    if (!pot) return;
    mutate(`/api/honeypots/${encodeURIComponent(honeypotId)}/toggle`, 'POST', { active: pot.status !== 'active' }, `${pot.name} ist jetzt ${pot.status === 'active' ? 'standby' : 'active'} (Simulation).`);
  }

  function startBackgroundCanvas() {
    const canvas = $('#signalCanvas');
    if (!canvas || !motionPreferred) return;
    const context = canvas.getContext('2d');
    let width = 0; let height = 0; let particles = [];
    const resize = () => {
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      width = window.innerWidth; height = window.innerHeight;
      canvas.width = width * ratio; canvas.height = height * ratio;
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      particles = Array.from({ length: Math.min(55, Math.max(25, Math.round(width / 28))) }, () => ({ x: Math.random() * width, y: Math.random() * height, speed: .12 + Math.random() * .45, size: Math.random() * 1.4 + .3, alpha: Math.random() * .55 + .12 }));
    };
    const draw = (time) => {
      context.clearRect(0, 0, width, height);
      const pulseX = width * (.2 + ((Math.sin(time / 9000) + 1) * .28));
      particles.forEach((particle) => {
        particle.y -= particle.speed;
        if (particle.y < -5) { particle.y = height + 5; particle.x = Math.random() * width; }
        context.fillStyle = `rgba(112,243,242,${particle.alpha})`;
        context.fillRect(particle.x, particle.y, particle.size, particle.size);
      });
      context.beginPath();
      context.moveTo(pulseX, height * .12); context.lineTo(pulseX + 210, height * .88);
      context.strokeStyle = 'rgba(255,76,58,.05)'; context.lineWidth = 1; context.stroke();
      backgroundFrame = window.requestAnimationFrame(draw);
    };
    window.addEventListener('resize', resize, { passive: true });
    resize(); draw(0);
  }

  function startDriftCanvas() {
    const canvas = $('#driftCanvas');
    if (!canvas || !motionPreferred || driftFrame) return;
    const context = canvas.getContext('2d');
    const stage = canvas.parentElement;
    let width = 0; let height = 0;
    const resize = () => {
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      width = stage.clientWidth; height = Math.max(300, window.innerWidth < 560 ? 390 : 480);
      canvas.width = width * ratio; canvas.height = height * ratio;
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
    };
    const skyline = Array.from({ length: 52 }, (_, index) => ({ x: index / 52, w: .008 + Math.random() * .026, h: .05 + Math.random() * .23, hue: Math.random() > .72 ? 'red' : 'cyan' }));
    const stars = Array.from({ length: 50 }, () => ({ x: Math.random(), y: .08 + Math.random() * .53, a: .2 + Math.random() * .55, r: .3 + Math.random() * 1.1 }));
    const draw = (time) => {
      context.clearRect(0, 0, width, height);
      const gradient = context.createLinearGradient(0, 0, 0, height);
      gradient.addColorStop(0, '#090b12'); gradient.addColorStop(.7, '#100f16'); gradient.addColorStop(1, '#201318');
      context.fillStyle = gradient; context.fillRect(0, 0, width, height);
      const sunX = width * .68; const sunY = height * .39; const sunR = Math.min(width, height) * .18;
      const halo = context.createRadialGradient(sunX, sunY, sunR * .5, sunX, sunY, sunR * 1.8);
      halo.addColorStop(0, 'rgba(255,77,49,.45)'); halo.addColorStop(.42, 'rgba(218,47,38,.2)'); halo.addColorStop(1, 'rgba(218,47,38,0)');
      context.fillStyle = halo; context.fillRect(0, 0, width, height);
      context.fillStyle = '#e84635'; context.shadowColor = 'rgba(255,76,58,.65)'; context.shadowBlur = 22; context.beginPath(); context.arc(sunX, sunY, sunR, 0, Math.PI * 2); context.fill(); context.shadowBlur = 0;
      context.fillStyle = 'rgba(43,10,14,.38)'; for (let i = 0; i < 7; i += 1) context.fillRect(sunX - sunR, sunY - sunR + i * sunR * .28, sunR * 2, 4);
      stars.forEach((star) => { context.fillStyle = `rgba(112,243,242,${star.a * (.7 + .3 * Math.sin(time / 800 + star.x * 8))})`; context.beginPath(); context.arc(star.x * width, star.y * height, star.r, 0, Math.PI * 2); context.fill(); });
      context.fillStyle = '#080b10'; context.beginPath(); context.moveTo(0, height * .69); skyline.forEach((building) => { const x = building.x * width; const h = building.h * height; context.lineTo(x, height * .69); context.lineTo(x, height * (.69 - h)); context.lineTo(x + building.w * width, height * (.69 - h)); context.lineTo(x + building.w * width, height * .69); }); context.lineTo(width, height); context.lineTo(0, height); context.closePath(); context.fill();
      skyline.forEach((building) => { const x = building.x * width; const top = height * (.69 - building.h); const windows = Math.max(1, Math.floor(building.h * 26)); context.fillStyle = building.hue === 'red' ? 'rgba(255,76,58,.42)' : 'rgba(112,243,242,.28)'; for (let i = 0; i < windows; i += 1) { const y = top + 6 + i * 9; if (y < height * .68) context.fillRect(x + 3, y, Math.max(1, building.w * width * .18), 1); } });
      context.strokeStyle = 'rgba(255,76,58,.27)'; context.lineWidth = 1; context.beginPath(); context.moveTo(0, height * .69); context.lineTo(width, height * .69); context.stroke();
      const sweepX = ((time / 35) % (width + 200)) - 100; context.strokeStyle = 'rgba(112,243,242,.13)'; context.beginPath(); context.moveTo(sweepX, 0); context.lineTo(sweepX - 90, height); context.stroke();
      driftFrame = window.requestAnimationFrame(draw);
    };
    window.addEventListener('resize', resize, { passive: true }); resize(); draw(0);
  }

  function bindEvents() {
    $$('[data-enter]').forEach((element) => element.addEventListener('click', (event) => { event.preventDefault(); enterCockpit(element.dataset.enter); }));
    $('[data-scroll-prototypes]')?.addEventListener('click', () => $('#prototypes').scrollIntoView({ behavior: motionPreferred ? 'smooth' : 'auto' }));
    $('#backToStart')?.addEventListener('click', () => { $('#appView').classList.add('is-hidden'); $('#startScreen').classList.remove('is-hidden'); window.scrollTo({ top: 0, behavior: 'auto' }); });
    $$('.nav-item').forEach((button) => button.addEventListener('click', () => setView(button.dataset.view)));
    $$('[data-view-link]').forEach((button) => button.addEventListener('click', () => { enterCockpit(currentView); setView(button.dataset.viewLink); }));
    $$('.filter-tab').forEach((button) => button.addEventListener('click', () => { planFilter = button.dataset.planFilter; renderPlans(); }));
    $$('[data-open-modal]').forEach((button) => button.addEventListener('click', () => openModal(button.dataset.openModal)));
    $('#tabGuideAction')?.addEventListener('click', () => {
      const action = $('#tabGuideAction').dataset.guideAction;
      if (['plan', 'honeypot', 'message', 'agent'].includes(action)) openModal(action);
      else if (['command', 'mesh', 'lab', 'drift', 'about'].includes(action)) setView(action);
    });
    $$('[data-close-modal]').forEach((button) => button.addEventListener('click', closeModal));
    $('#modalBackdrop')?.addEventListener('click', (event) => { if (event.target === $('#modalBackdrop')) closeModal(); });
    document.addEventListener('keydown', (event) => { if (event.key === 'Escape') closeModal(); });
    document.addEventListener('click', (event) => {
      const planButton = event.target.closest('[data-cycle-plan]');
      if (planButton) { event.preventDefault(); cyclePlan(planButton.dataset.cyclePlan); return; }
      const toggle = event.target.closest('[data-toggle-pot]');
      if (toggle) { toggleHoneypot(toggle.dataset.togglePot); return; }
      const simulate = event.target.closest('[data-simulate-pot]');
      if (simulate) { simulateSignal(simulate.dataset.simulatePot); return; }
      const ack = event.target.closest('[data-ack-incident]');
      if (ack) mutate(`/api/incidents/${encodeURIComponent(ack.dataset.ackIncident)}/ack`, 'POST', {}, 'Incident bestätigt — Kontext an den Mesh verteilt.');
    });
    $('#simulateRandomSignal')?.addEventListener('click', () => {
      const pot = state?.honeypots.find((item) => item.status === 'active');
      if (pot) simulateSignal(pot.id); else toast('Kein aktiver Decoy. Erst einen Honeypot aktivieren.', 'error');
    });
    $('#driftPulse')?.addEventListener('click', () => {
      const pot = state?.honeypots.find((item) => item.status === 'active');
      if (pot) { simulateSignal(pot.id); setView('drift'); } else toast('Signal Pulse benötigt einen aktiven virtuellen Decoy.', 'error');
    });
    $('#motionToggle')?.addEventListener('click', () => { document.body.classList.toggle('reduce-motion'); toast(document.body.classList.contains('reduce-motion') ? 'Animationen pausiert.' : 'Animationen aktiviert.'); });
    $('#planForm')?.addEventListener('submit', async (event) => { event.preventDefault(); const data = new FormData(event.target); const okay = await mutate('/api/plans', 'POST', Object.fromEntries(data.entries()), 'Plan gebroadcastet — jeder Agent sieht jetzt denselben nächsten Schritt.'); if (okay) { event.target.reset(); closeModal(); setView('mesh'); } });
    $('#honeypotForm')?.addEventListener('submit', async (event) => { event.preventDefault(); const data = new FormData(event.target); const okay = await mutate('/api/honeypots', 'POST', Object.fromEntries(data.entries()), 'Virtueller Decoy angelegt — noch kein Listener aktiv.'); if (okay) { event.target.reset(); closeModal(); setView('lab'); } });
    $('#messageForm')?.addEventListener('submit', async (event) => { event.preventDefault(); const data = new FormData(event.target); const okay = await mutate('/api/messages', 'POST', Object.fromEntries(data.entries()), 'Kontext an den Agent Mesh verteilt.'); if (okay) { event.target.reset(); closeModal(); setView('mesh'); } });
    $('#agentForm')?.addEventListener('submit', async (event) => { event.preventDefault(); const data = new FormData(event.target); const okay = await mutate('/api/agents', 'POST', Object.fromEntries(data.entries()), 'Agent ist online und im gemeinsamen Kontext registriert.'); if (okay) { event.target.reset(); closeModal(); setView('mesh'); } });
  }

  function updateClock() {
    const now = new Date();
    $('#clockTime').textContent = now.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  async function boot() {
    bindEvents();
    updateClock(); window.setInterval(updateClock, 1000);
    startBackgroundCanvas();
    await loadState(true);
    window.setInterval(() => { if (!document.hidden) loadState(false); }, 8000);
  }

  boot();
})();
