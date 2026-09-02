/* CyberGuardian cockpit — intentionally plain browser JavaScript, no third-party runtime. */
(() => {
  'use strict';

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const motionPreferred = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let state = null;
  let opsState = null;
  let toolsState = null;
  let currentView = 'command';
  let planFilter = 'all';
  let toolFilter = 'all';
  let toolSearch = '';
  let offlineMode = false;
  let toastTimer;
  let backgroundFrame;
  let driftFrame;
  let activePrototype = 'nightwatch';
  let selectedPrototype = null;

  const prototypeVariants = {
    nightwatch: {
      index: 'DESIGN STUDY / 01 · ATMOSPHERE', title: 'NIGHTWATCH', accent: 'HUD',
      description: 'Ein dichtes Neon-HUD für permanente Signalbeobachtung. Die Oberfläche lebt, ohne den Operator mit Aktionen zu überfahren.',
      mode: 'SIMULATION ONLY', traits: ['NEON SIGNAL LAYER', 'PERMANENT READOUT', 'MOTION READY'],
      context: 'ONE TRUTH. MANY GUARDIANS.', signal: 'SIGNAL 014 / OBSERVE', plan: 'EDGE-LAYER BASELINE',
      initial: 'ORBIT trägt den Kontext. Klicke Agenten oder eine Interaktion an.',
      agents: { ORBIT: 'ORBIT hält die Lage zusammen. Hover und Pulse machen Kontext sofort sichtbar.', SENTINEL: 'SENTINEL beobachtet die genehmigte Laborzone. Keine aktive Antwort.', KAI: 'KAI hält den virtuellen Decoy warm. Signale bleiben synthetisch.' },
      actions: { context: 'CONTEXT LAYER: Der gemeinsame Plan bleibt direkt neben dem Signal sichtbar.', signal: 'SIGNAL TRACE: Eine animierte Spur verbindet Quelle, Decoy und Audit-Eintrag.', safe: 'SAFE PREVIEW: Beobachten ist vorbereitet. Es wird keine Systemaktion ausgeführt.' },
      steps: { intent: 'INTENT: Ein defensives Ziel steht im Zentrum des Leitstands.', signal: 'SIGNAL: Ein synthetischer Hinweis erhält Quelle und Taktik.', audit: 'AUDIT: Ergebnis, Zeit und Verantwortlichkeit bleiben zurück.' }
    },
    orbit: {
      index: 'DESIGN STUDY / 02 · COORDINATION', title: 'AGENT', accent: 'ORBIT',
      description: 'Agenten kreisen um den gemeinsamen Control Plane. Zuständigkeit, Übergabe und Nähe zum Kontext werden räumlich lesbar.',
      mode: 'MESH / SYNCHRONIZED', traits: ['SPATIAL CONTEXT', 'AGENT HANDOFFS', 'FOCUS ON OWNER'],
      context: 'THE MESH SEES TOGETHER.', signal: 'HANDOFF 03 / SHARED', plan: 'EVIDENCE CHAIN',
      initial: 'Wähle einen Knoten. Die Konstellation zeigt, wer den nächsten Schritt trägt.',
      agents: { ORBIT: 'ORBIT ist der zentrale Kontextknoten. Er korreliert, statt allein zu handeln.', SENTINEL: 'SENTINEL liegt am äußeren Ring und markiert den Beobachtungsbereich.', KAI: 'KAI verbindet den Decoy mit dem Mesh. Seine Telemetrie bleibt im Labor.' },
      actions: { context: 'AGENT CONTEXT: Ein Knoten wird zum aktiven Owner und zeigt seine Übergabe.', signal: 'SIGNAL TRACE: Der Signalpfad wandert vom äußeren Knoten zum SOT.', safe: 'SAFE PREVIEW: Eine Übergabe wird vorbereitet, nicht automatisch ausgeführt.' },
      steps: { intent: 'INTENT: Der Owner setzt ein gemeinsames Ziel für das Mesh.', signal: 'SIGNAL: Der zuständige Agent meldet eine Beobachtung zurück.', audit: 'AUDIT: Handoff und Entscheidung werden gemeinsam gespeichert.' }
    },
    tactical: {
      index: 'DESIGN STUDY / 03 · CLARITY', title: 'TACTICAL', accent: 'CONSOLE',
      description: 'Ein ruhiger Operator-Look für Tagesbetrieb, Prioritäten und schnelle Entscheidungen — weniger Effekt, mehr Übersicht.',
      mode: 'OPERATOR / READ ONLY', traits: ['FAST SCANNING', 'LOW COGNITIVE LOAD', 'KEYBOARD READY'],
      context: 'CONTROL THE NEXT STEP.', signal: 'QUEUE 03 / TRIAGE', plan: 'EDGE-LAYER BASELINE',
      initial: 'Filter, Status und nächste Aktion stehen im Vordergrund. Klicke einen Modus an.',
      agents: { ORBIT: 'ORBIT: drei aktive Kontexte warten auf Korrelation.', SENTINEL: 'SENTINEL: genehmigte Zone ist im Beobachtungsfenster.', KAI: 'KAI: virtuelle Decoys liefern kontrollierte Testdaten.' },
      actions: { context: 'CONTEXT FILTER: Nur die für den nächsten Operator-Schritt relevanten Daten bleiben offen.', signal: 'SIGNAL TRACE: Metadaten werden als kompakte Zeile statt als Animation gezeigt.', safe: 'SAFE PREVIEW: Die erlaubte Aktion wird vor dem Run mit Boundary angezeigt.' },
      steps: { intent: 'INTENT: Priorität und Ziel sind als klare Queue sichtbar.', signal: 'SIGNAL: Beobachtung landet in einer filterbaren Zeile.', audit: 'AUDIT: Der Run erhält einen kompakten Nachweis.' }
    },
    theatre: {
      index: 'DESIGN STUDY / 04 · WORKFLOW', title: 'INCIDENT', accent: 'THEATRE',
      description: 'Der defensive Ablauf wird als Timeline erzählt: vom synthetischen Signal über die Korrelation bis zum Audit.',
      mode: 'STORY / SYNTHETIC EVENT', traits: ['TIMELINE FIRST', 'EXPLAINABLE FLOW', 'DRILL MODE'],
      context: 'FOLLOW THE EVIDENCE.', signal: 'SCENE 02 / CREDENTIAL PROBE', plan: 'HONEYPOT RELAY V2',
      initial: 'Die Timeline ist die Hauptfigur. Klicke eine Szene oder einen Schritt an.',
      agents: { ORBIT: 'Szene 01: ORBIT verbindet das Signal mit dem gemeinsamen Plan.', SENTINEL: 'Szene 02: SENTINEL ordnet die Beobachtung defensiv ein.', KAI: 'Szene 03: KAI bestätigt den virtuellen Decoy und seine Logs.' },
      actions: { context: 'CONTEXT SCENE: Die beteiligten Rollen erscheinen direkt an der Timeline.', signal: 'SIGNAL TRACE: Der synthetische Event wird Schritt für Schritt nachvollziehbar.', safe: 'SAFE PREVIEW: Die Szene zeigt eine Entscheidung ohne reale Gegenmaßnahme.' },
      steps: { intent: 'SZENE 01 / INTENT: Das Ziel und die erlaubte Grenze werden gesetzt.', signal: 'SZENE 02 / SIGNAL: Der virtuelle Decoy empfängt ein synthetisches Ereignis.', audit: 'SZENE 03 / AUDIT: Die Beweiskette schließt den defensiven Ablauf.' }
    }
  };

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

  const fallbackOps = {
    tools: { tshark: false, tcpdump: false, wireshark: false, proxychains: false, macchanger: false, ip: false },
    capture_engine: 'simulation',
    interfaces: ['lo'],
    safe_boundary: { packet_capture: 'metadata only / bounded', proxychains: 'profile inspection only', mac_changer: 'preview only / no mutation' },
    proxy: { available: false, binary: '', configs: [], configured: false, mode: 'inspection only' },
    mac: { lo: { interface: 'lo', current: 'unknown', macchanger_available: false, mode: 'read-only', mutated: false } }
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
    ops: {
      symbol: '⌘', kicker: 'YOU ARE HERE / LOCAL TOOLCHAIN', title: 'DEFENSE OPS',
      text: 'Hier werden nützliche lokale Tools sicher begrenzt: Capture-Header beobachten, Proxychains prüfen, MAC-Wechsel vorbereiten.',
      next: 'HEALTH SWEEP', output: 'allowlisted · bounded · read-only', action: 'ops-sweep', actionLabel: 'SWEEP STARTEN'
    },
    tools: {
      symbol: '▦', kicker: 'YOU ARE HERE / UNIFIED CONTROL', title: 'TOOL ATLAS',
      text: 'Alle CyberGuardian-Module liegen auf einer Oberfläche. Jede Aktion ist erklärt, allowlisted und mit Ergebnis im Audit Trail gespeichert.',
      next: 'SAFE AUDIT', output: 'alle Module nacheinander nachvollziehbar', action: 'tools-sweep', actionLabel: 'AUDIT STARTEN'
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

  async function loadOpsOverview(showError = false) {
    try {
      opsState = await request('/api/ops/overview');
      renderOps();
      return true;
    } catch (error) {
      opsState = clone(fallbackOps);
      renderOps();
      if (showError) toast('Defense Ops läuft im Demo-Modus — lokale Tools bleiben unberührt.', 'error');
      return false;
    }
  }

  async function loadTools(showError = false) {
    try {
      toolsState = await request('/api/tools');
      renderTools();
      return true;
    } catch (error) {
      toolsState = { tools: [], runs: [], safety: { mode: 'offline demo', browser_mutations: false } };
      renderTools();
      if (showError) toast('Tool Atlas ist im Demo-Modus — keine lokale Aktion ausgeführt.', 'error');
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

  function getStoredPrototype() {
    try {
      const value = window.localStorage.getItem('cyberguardian.prototypeDirection');
      return Object.prototype.hasOwnProperty.call(prototypeVariants, value) ? value : null;
    } catch (_) {
      return null;
    }
  }

  function renderPrototypeSelection() {
    $$('.design-variant').forEach((button) => button.classList.toggle('is-selected', button.dataset.designVariant === selectedPrototype));
    const status = $('#prototypeSelectionStatus');
    if (!status) return;
    status.classList.toggle('is-locked', Boolean(selectedPrototype));
    status.textContent = selectedPrototype ? `LOCKED / ${prototypeVariants[selectedPrototype].title} ${prototypeVariants[selectedPrototype].accent}` : 'NO DIRECTION LOCKED';
  }

  function announcePrototype(message) {
    const feedback = $('#previewFeedback');
    if (feedback) feedback.textContent = message;
    $('#confirmToast').textContent = message;
  }

  function resetPrototypeControls() {
    $$('.preview-agent').forEach((button, index) => button.classList.toggle('preview-agent--active', index === 0));
    $$('.preview-action').forEach((button, index) => button.classList.toggle('preview-action--active', index === 0));
    $$('.preview-step').forEach((button, index) => button.classList.toggle('preview-step--active', index === 0));
  }

  const previewPacketSample = [
    { time: '+0.00s', source: '192.0.2.10', source_port: '51834', destination: '192.0.2.1', destination_port: '443', protocol: 'TCP', synthetic: true },
    { time: '+0.42s', source: '198.51.100.7', source_port: '41201', destination: '203.0.113.5', destination_port: '53', protocol: 'DNS', synthetic: true },
    { time: '+0.84s', source: '203.0.113.5', source_port: '55422', destination: '198.51.100.7', destination_port: '443', protocol: 'HTTPS', synthetic: true }
  ];

  function renderPreviewPackets(packets = previewPacketSample, label = 'SAFE SAMPLE') {
    const target = $('#previewPacketFeed');
    if (!target) return;
    const rows = Array.isArray(packets) ? packets.slice(0, 6) : [];
    const header = '<div class="preview-packet-row preview-packet-row--head"><span>TIME</span><span>SOURCE</span><i></i><span>DESTINATION</span><b>PROTO</b></div>';
    const content = rows.map((packet) => `<div class="preview-packet-row"><span>${escapeHTML(packet.time || '—')}</span><span>${escapeHTML(packet.source || '—')}${packet.source_port ? `:${escapeHTML(packet.source_port)}` : ''}</span><i>→</i><span>${escapeHTML(packet.destination || '—')}${packet.destination_port ? `:${escapeHTML(packet.destination_port)}` : ''}</span><b>${escapeHTML(packet.protocol || 'UNKNOWN')}</b></div>`).join('');
    target.innerHTML = `<div class="preview-packet-label"><span>${escapeHTML(label)}</span><small>HEADER METADATA / NO PAYLOAD</small></div>${content ? header + content : '<div class="preview-packet-empty">NO METADATA ROWS / SAFE BOUNDARY HELD</div>'}`;
  }

  async function capturePreviewMetadata() {
    const button = $('#previewCaptureButton');
    if (!button) return;
    button.disabled = true;
    button.textContent = 'CAPTURING …';
    try {
      const result = await request('/api/ops/capture', {
        method: 'POST',
        body: JSON.stringify({ interface: 'lo', preset: 'metadata', duration: 3, limit: 6 })
      });
      const label = result.mode === 'simulation' ? 'SAFE DEMO / SYNTHETIC' : `${String(result.engine || 'LOCAL').toUpperCase()} / LIVE METADATA`;
      renderPreviewPackets(result.packets || [], label);
      const first = result.packets?.[0];
      if (first) $('#previewContextSignal').textContent = `${first.protocol || 'PACKET'} / ${result.mode === 'simulation' ? 'SYNTHETIC' : 'OBSERVE'}`;
      announcePrototype(result.notice || 'Packet-Metadaten gelesen. Kein Payload wurde angefordert.');
    } catch (error) {
      renderPreviewPackets(previewPacketSample, 'SAFE SAMPLE / OFFLINE');
      announcePrototype('Live Capture nicht erreichbar. Sichere Beispieldaten bleiben sichtbar — kein Request wurde weitergeleitet.');
    } finally {
      button.disabled = false;
      button.textContent = 'READ METADATA ↯';
    }
  }

  function renderPrototypePreview(name) {
    const config = prototypeVariants[name] || prototypeVariants.nightwatch;
    activePrototype = name;
    const stage = $('#prototypeStage');
    stage.dataset.variant = name;
    $('#prototypePreviewKicker').textContent = config.index;
    const title = $('#prototypePreviewTitle');
    title.childNodes[0].textContent = `${config.title} `;
    $('span', title).textContent = config.accent;
    $('#prototypePreviewDescription').textContent = config.description;
    $('#previewStageMode').textContent = config.mode;
    $('#previewContextTitle').textContent = config.context;
    $('#previewContextSignal').textContent = config.signal;
    $('#previewPlanTitle').textContent = config.plan;
    $('#prototypeTraitOne').textContent = config.traits[0];
    $('#prototypeTraitTwo').textContent = config.traits[1];
    $('#prototypeTraitThree').textContent = config.traits[2];
    $('#prototypeSelectButton').textContent = selectedPrototype === name ? 'DIRECTION LOCKED ✓' : 'USE THIS DIRECTION ↗';
    resetPrototypeControls();
    renderPreviewPackets();
    const now = new Date();
    $('#previewStageClock').textContent = now.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'UTC' });
    announcePrototype(config.initial);
  }

  function openPrototypePreview(name) {
    if (!prototypeVariants[name]) return;
    renderPrototypePreview(name);
    $('#prototypeBackdrop').classList.remove('is-hidden');
    document.body.classList.add('prototype-open');
    window.setTimeout(() => $('#prototypeSelectButton')?.focus(), 40);
  }

  function closePrototypePreview() {
    $('#prototypeBackdrop').classList.add('is-hidden');
    document.body.classList.remove('prototype-open');
  }

  function lockPrototypeDirection() {
    selectedPrototype = activePrototype;
    try { window.localStorage.setItem('cyberguardian.prototypeDirection', selectedPrototype); } catch (_) { /* optional preference */ }
    renderPrototypeSelection();
    $('#prototypeSelectButton').textContent = 'DIRECTION LOCKED ✓';
    announcePrototype(`${prototypeVariants[activePrototype].title} ${prototypeVariants[activePrototype].accent} ist als bevorzugte Richtung markiert. Produktionsdesign bleibt unverändert.`);
  }

  function clearPrototypeDirection() {
    selectedPrototype = null;
    try { window.localStorage.removeItem('cyberguardian.prototypeDirection'); } catch (_) { /* optional preference */ }
    renderPrototypeSelection();
    if ($('#prototypeSelectButton')) $('#prototypeSelectButton').textContent = 'USE THIS DIRECTION ↗';
    announcePrototype('Auswahl gelöscht. Keine Designrichtung ist festgelegt.');
  }

  function handlePrototypeAgent(agent) {
    const config = prototypeVariants[activePrototype];
    $$('.preview-agent').forEach((button) => button.classList.toggle('preview-agent--active', button.dataset.previewAgent === agent));
    $('#previewContextTitle').textContent = `${agent} / SHARED CONTEXT`;
    $('#previewContextSignal').textContent = `HANDOFF / ${agent}`;
    announcePrototype(config.agents[agent] || `${agent} ist im gemeinsamen Mesh sichtbar.`);
  }

  function handlePrototypeAction(action) {
    const config = prototypeVariants[activePrototype];
    $$('.preview-action').forEach((button) => button.classList.toggle('preview-action--active', button.dataset.previewAction === action));
    announcePrototype(config.actions[action] || 'Interaktion für diese Richtung ist bereit.');
  }

  function handlePrototypeStep(step) {
    const config = prototypeVariants[activePrototype];
    $$('.preview-step').forEach((button) => button.classList.toggle('preview-step--active', button.dataset.previewStep === step));
    announcePrototype(config.steps[step] || 'Workflow-Schritt ausgewählt.');
  }

  function renderLandingState() {
    if (!state) return;
    const stats = state.stats || {};
    $('#landingAgentCount').textContent = String(stats.online_agents || 0).padStart(2, '0');
    $('#landingPlanCount').textContent = String(state.plans?.length || 0).padStart(2, '0');
    $('#landingSignalCount').textContent = String(stats.signals_today || 0).padStart(2, '0');
    $('#landingMode').textContent = state.settings?.simulation_mode ? 'SIMULATION / LOCAL' : 'DEFENSE / LOCAL';
    $('#heroAgentReadout').textContent = `${String(stats.online_agents || 0).padStart(2, '0')} ONLINE`;
  }

  function renderAll() {
    if (!state) return;
    renderLandingState();
    renderMetrics();
    renderPlans();
    renderAgents();
    renderHoneypots();
    renderActivity();
    renderMesh();
    renderLab();
    if (opsState) renderOps();
    if (toolsState) renderTools();
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

  function setOpsSelectOptions(selector, values, includeAny = false) {
    const select = $(selector);
    if (!select) return;
    const previous = select.value;
    const options = includeAny ? ['any', ...values] : values;
    select.innerHTML = options.map((value) => `<option value="${escapeHTML(value)}">${escapeHTML(value.toUpperCase())}</option>`).join('');
    if (options.includes(previous)) select.value = previous;
  }

  let lastCapture = null;
  let lastMacPreview = null;
  let sweepRanAt = null;

  function renderCaptureInsights() {
    const packets = Array.isArray(lastCapture?.packets) ? lastCapture.packets : [];
    const protocolSummary = $('#protocolSummary');
    const protocolBars = $('#protocolBars');
    const conversationSummary = $('#conversationSummary');
    const conversationMap = $('#conversationMap');
    const correlationFlow = $('#captureCorrelationFlow');
    if (!protocolSummary || !protocolBars || !conversationSummary || !conversationMap || !correlationFlow) return;
    if (!packets.length) {
      protocolSummary.textContent = 'WAITING';
      conversationSummary.textContent = 'WAITING';
      protocolBars.innerHTML = '<span class="ops-result-placeholder">Noch keine Metadaten gelesen.</span>';
      conversationMap.innerHTML = '<span class="ops-result-placeholder">Quelle → Ziel wird nach dem Capture gruppiert.</span>';
      correlationFlow.innerHTML = '<span class="ops-result-placeholder">Ein Capture bildet noch keine Gegenmaßnahme. Erst beobachten, dann korrelieren.</span>';
      return;
    }

    const protocols = new Map();
    const conversations = new Map();
    packets.forEach((packet) => {
      const protocol = String(packet.protocol || 'UNKNOWN').toUpperCase();
      protocols.set(protocol, (protocols.get(protocol) || 0) + 1);
      const source = packet.source || '—';
      const destination = packet.destination || '—';
      const key = `${source} → ${destination}`;
      conversations.set(key, (conversations.get(key) || 0) + 1);
    });
    const protocolRows = [...protocols.entries()].sort((a, b) => b[1] - a[1]);
    const maxProtocol = Math.max(...protocolRows.map(([, count]) => count), 1);
    protocolSummary.textContent = `${packets.length} ROWS / ${protocolRows.length} PROTOCOLS`;
    protocolBars.innerHTML = protocolRows.slice(0, 5).map(([protocol, count]) => `<div class="protocol-bar"><span>${escapeHTML(protocol)}</span><i><b style="width:${Math.max(12, (count / maxProtocol) * 100)}%"></b></i><strong>${count}</strong></div>`).join('');

    const conversationRows = [...conversations.entries()].sort((a, b) => b[1] - a[1]);
    conversationSummary.textContent = `${conversationRows.length} FLOWS`;
    conversationMap.innerHTML = conversationRows.slice(0, 4).map(([route, count]) => { const parts = route.split(' → '); return `<div class="conversation-row"><span>${escapeHTML(parts[0])}</span><i>→</i><span>${escapeHTML(parts.slice(1).join(' → '))}</span><b>${count}</b></div>`; }).join('');

    const latestSignal = state?.honeypot_logs?.[0];
    const latestIncident = state?.incidents?.find((incident) => incident.status === 'open') || state?.incidents?.[0];
    const latestAudit = state?.activity?.find((event) => String(event.kind || '').includes('ops.capture'));
    const decoy = state?.honeypots?.find((pot) => pot.id === latestSignal?.honeypot_id) || state?.honeypots?.[0];
    const captureLabel = lastCapture.mode === 'simulation' ? 'SAFE DEMO' : String(lastCapture.engine || 'LOCAL').toUpperCase();
    const chain = [
      ['01 / PACKETS', `${packets.length} ROWS`, captureLabel],
      ['02 / DECOY', decoy?.name || 'VIRTUAL NODE', decoy?.status === 'active' ? 'ACTIVE' : 'READY'],
      ['03 / INCIDENT', latestIncident?.id || 'NO MATCH', latestIncident?.status ? String(latestIncident.status).toUpperCase() : 'CORRELATE'],
      ['04 / AUDIT', latestAudit ? 'RECORDED' : 'READY', latestAudit ? formatTime(latestAudit.created_at, true) : 'AWAITING LOG']
    ];
    correlationFlow.innerHTML = chain.map(([label, value, meta], index) => `${index ? '<i>→</i>' : ''}<div class="capture-chain-node"><span>${escapeHTML(label)}</span><strong>${escapeHTML(value)}</strong><small>${escapeHTML(meta)}</small></div>`).join('');
  }

  function renderCaptureResult() {
    const target = $('#captureResult');
    if (!target) return;
    if (!lastCapture) {
      target.innerHTML = '<span class="ops-result-placeholder">Bereit. Profil und Interface wählen, dann Capture starten.</span>';
      renderCaptureInsights();
      return;
    }
    const demo = lastCapture.mode === 'simulation';
    const packets = Array.isArray(lastCapture.packets) ? lastCapture.packets : [];
    const rows = packets.slice(0, 30).map((packet) => `<div class="packet-row"><span>${escapeHTML(packet.time || '—')}</span><strong>${escapeHTML(packet.source || '—')}</strong><strong>${escapeHTML(packet.destination || '—')}</strong><b>${escapeHTML(packet.protocol || '—')}</b></div>`).join('');
    target.innerHTML = `<div class="ops-result-head"><span>${lastCapture.ok ? `${packets.length} METADATA ROWS` : 'CAPTURE NICHT VERFÜGBAR'}</span><small class="${demo ? 'is-demo' : ''}">${demo ? 'SAFE DEMO' : escapeHTML(String(lastCapture.engine || 'LOCAL').toUpperCase())}</small></div>${lastCapture.ok && packets.length ? `<div class="packet-table"><div class="packet-row packet-row--head"><span>TIME</span><span>SOURCE</span><span>DESTINATION</span><span>PROTO</span></div>${rows}</div>` : `<span class="ops-result-placeholder">${escapeHTML(lastCapture.notice || lastCapture.error || 'Keine Zeilen empfangen.')}</span>`}`;
    renderCaptureInsights();
  }

  function renderOps() {
    if (!opsState) return;
    const interfaces = Array.isArray(opsState.interfaces) && opsState.interfaces.length ? opsState.interfaces : ['lo'];
    setOpsSelectOptions('#captureInterface', interfaces, true);
    setOpsSelectOptions('#macInterface', interfaces, false);
    const engine = String(opsState.capture_engine || 'simulation');
    const badge = $('#captureModeBadge');
    if (badge) {
      badge.textContent = engine === 'simulation' ? 'SAFE DEMO FALLBACK' : `${engine.toUpperCase()} / METADATA`;
      badge.className = `tag ${engine === 'simulation' ? 'tag--high' : 'tag--green'}`;
    }
    const toolLabels = { tshark: 'TSHARK', tcpdump: 'TCPDUMP', proxychains: 'PROXYCHAINS', macchanger: 'MACCHANGER', ip: 'IP TOOL' };
    const tools = opsState.tools || {};
    $('#opsCapabilityStrip').innerHTML = Object.entries(toolLabels).map(([key, label]) => `<span class="ops-capability ${tools[key] ? '' : 'ops-capability--missing'}">${label} ${tools[key] ? 'READY' : 'NOT FOUND'}</span>`).join('') + `<span class="ops-capability ${engine === 'simulation' ? 'ops-capability--pending' : ''}">CAPTURE: ${escapeHTML(engine.toUpperCase())}</span>`;
    const proxy = opsState.proxy || {};
    $('#proxyStateBadge').textContent = proxy.configured ? 'READY' : proxy.available ? 'BINARY ONLY' : 'NOT FOUND';
    $('#proxyStateBadge').className = `tag ${proxy.configured ? 'tag--green' : 'tag--high'}`;
    $('#proxyDetails').innerHTML = `<div><span>BINARY</span><strong class="${proxy.available ? 'is-ready' : 'is-missing'}">${escapeHTML(proxy.binary || 'NOT FOUND')}</strong></div><div><span>CONFIG</span><strong class="${proxy.configs?.length ? 'is-ready' : 'is-missing'}">${proxy.configs?.length ? `${proxy.configs.length} FOUND` : 'NOT FOUND'}</strong></div><div><span>MODE</span><strong>INSPECTION ONLY</strong></div>`;
    const selectedInterface = $('#macInterface')?.value || interfaces[0];
    const mac = (opsState.mac || {})[selectedInterface] || { current: 'unknown', macchanger_available: false };
    $('#macStatus').innerHTML = `<span>CURRENT MAC</span><strong>${escapeHTML(mac.current || 'unknown')}</strong>`;
    if (lastMacPreview && lastMacPreview.interface === selectedInterface) {
      $('#macPreviewOutput').innerHTML = `<div class="mac-preview"><span>PROPOSED LOCAL UNICAST</span><strong>${escapeHTML(lastMacPreview.proposed)}</strong><code>${escapeHTML(lastMacPreview.command_preview)}</code><small class="ops-result-placeholder">${escapeHTML(lastMacPreview.warning)}</small></div>`;
    } else {
      $('#macPreviewOutput').innerHTML = '<span class="ops-result-placeholder">Noch keine Vorschau. Das System bleibt unverändert.</span>';
    }
    renderCaptureResult();
    if (sweepRanAt) {
      $('#opsSweepResult').innerHTML = `<span class="sweep-check"><strong>DISCOVER</strong><small>${Object.values(tools).filter(Boolean).length} lokale Tools verfügbar · ${interfaces.length} Interfaces</small></span><span class="sweep-check ${proxy.configured ? '' : 'sweep-check--warn'}"><strong>PROXYCHAINS</strong><small>${proxy.configured ? 'Binary + Config gefunden' : 'nicht vollständig konfiguriert'}</small></span><span class="sweep-check"><strong>MAC READ</strong><small>${escapeHTML(mac.current || 'unknown')} · no mutation</small></span><span class="sweep-check ${lastCapture?.ok ? '' : 'sweep-check--warn'}"><strong>CAPTURE</strong><small>${lastCapture?.ok ? `${lastCapture.packets?.length || 0} metadata rows` : 'nicht verfügbar'}</small></span>`;
    }
  }

  function toolStatusLabel(status) {
    return ({ ready: 'READY', limited: 'LIMITED', simulated: 'SIMULATION', 'not-installed': 'NOT FOUND' }[status] || String(status || 'UNKNOWN').toUpperCase());
  }

  function toolCard(tool) {
    const lastRun = tool.last_run;
    const action = tool.actions?.[0];
    const status = String(tool.status || 'limited');
    return `<article class="tool-card tool-card--${escapeHTML(tool.accent || 'cyan')}" data-tool-category="${escapeHTML(tool.category)}" data-tool-name="${escapeHTML(`${tool.name} ${tool.summary} ${tool.module}`.toLowerCase())}">
      <div class="tool-card-top"><span class="tool-icon">${escapeHTML(tool.icon || '◈')}</span><div class="tool-heading"><span class="tool-category">${escapeHTML(tool.category)} / ${escapeHTML(tool.module)}</span><h3>${escapeHTML(tool.name)}</h3></div><span class="tool-status tool-status--${escapeHTML(status)}"><i></i>${toolStatusLabel(status)}</span></div>
      <p class="tool-summary-copy">${escapeHTML(tool.summary)}</p>
      <div class="tool-boundary"><span>SAFETY RAIL</span><strong>${escapeHTML(tool.boundary)}</strong></div>
      <p class="tool-explain">${escapeHTML(tool.explain)}</p>
      <div class="tool-card-meta"><span>${tool.availability ? 'CAPABILITY DETECTED' : 'FALLBACK / LIMITED'}</span><span>${tool.enabled ? 'WATCH ON' : 'WATCH PAUSED'}</span></div>
      <div class="tool-card-actions"><button class="button button--tiny button--primary" data-run-tool="${escapeHTML(tool.id)}" data-tool-action="${escapeHTML(action?.id || '')}">${escapeHTML(action?.label || 'RUN')} ↗</button><button class="tool-watch-button ${tool.enabled ? 'tool-watch-button--on' : ''}" data-toggle-tool="${escapeHTML(tool.id)}" data-tool-enabled="${tool.enabled ? 'true' : 'false'}">${tool.enabled ? '◉ WATCH ON' : '○ WATCH OFF'}</button></div>
      <div class="tool-last-run">${lastRun ? `<span>LAST: ${formatTime(lastRun.completed_at, true)} · ${escapeHTML(lastRun.mode)}</span><strong>${escapeHTML(lastRun.status.toUpperCase())}</strong>` : '<span>NO RUN RECORDED YET</span><strong>—</strong>'}</div>
    </article>`;
  }

  function runDetails(run) {
    const details = run.details && Object.keys(run.details).length ? JSON.stringify(run.details, null, 2) : run.error || 'No additional details.';
    return `<details class="tool-run-details"><summary>DETAILS ↗</summary><pre>${escapeHTML(details)}</pre></details>`;
  }

  function renderTools() {
    if (!toolsState) return;
    const allTools = Array.isArray(toolsState.tools) ? toolsState.tools : [];
    const filtered = allTools.filter((tool) => {
      const matchesFilter = toolFilter === 'all' || tool.category === toolFilter;
      const query = toolSearch.trim().toLowerCase();
      return matchesFilter && (!query || `${tool.name} ${tool.summary} ${tool.module} ${tool.category}`.toLowerCase().includes(query));
    });
    const available = allTools.filter((tool) => tool.availability).length;
    const watched = allTools.filter((tool) => tool.enabled).length;
    $('#toolCountAll').textContent = String(allTools.length);
    $('#toolSummary').innerHTML = `<div><strong>${allTools.length}</strong><span>KNOWN MODULES</span></div><div><strong>${available}</strong><span>CAPABILITIES READY</span></div><div><strong>${watched}</strong><span>WATCH POSTURES ON</span></div><div><strong>${toolsState.runs?.length || 0}</strong><span>AUDITED RUNS</span></div>`;
    $('#toolGrid').innerHTML = filtered.length ? filtered.map(toolCard).join('') : '<div class="empty-state">NO MODULES MATCH THIS FILTER</div>';
    $$('.atlas-filters .filter-tab').forEach((tab) => tab.classList.toggle('filter-tab--active', tab.dataset.toolFilter === toolFilter));
    const runs = Array.isArray(toolsState.runs) ? toolsState.runs : [];
    $('#toolRunCount').textContent = `${runs.length} RUNS`;
    $('#toolRunLog').innerHTML = runs.slice(0, 20).map((run) => {
      const tool = allTools.find((item) => item.id === run.tool_id);
      return `<article class="tool-run-row"><span class="tool-run-icon">${escapeHTML(tool?.icon || '◈')}</span><div><strong>${escapeHTML(tool?.name || run.tool_id)}</strong><span>${escapeHTML(run.action)} · ${escapeHTML(run.mode)} · ${formatTime(run.completed_at, true)}</span><p>${escapeHTML(run.summary)}</p>${runDetails(run)}</div><b class="tool-run-status tool-run-status--${escapeHTML(run.status)}">${escapeHTML(run.status.toUpperCase())}</b></article>`;
    }).join('') || '<div class="empty-state">NO TOOL RUNS YET — START WITH A SAFE AUDIT</div>';
  }

  async function loadToolsAndState() {
    await Promise.all([loadState(false), loadTools(false)]);
  }

  async function runTool(toolId, action) {
    if (offlineMode) { toast('Server nicht verbunden — kein Tool-Run ausgeführt.', 'error'); return; }
    const button = document.querySelector(`[data-run-tool="${toolId}"]`);
    if (button) { button.disabled = true; button.textContent = '↯ RUNNING …'; }
    try {
      const run = await request(`/api/tools/${encodeURIComponent(toolId)}/run`, { method: 'POST', body: JSON.stringify({ action }) });
      await Promise.all([loadState(false), loadTools(false)]);
      toast(`${toolId.toUpperCase()} protokolliert: ${run.summary}`, run.status === 'completed' ? 'success' : 'error');
    } catch (error) {
      toast(error.message || 'Tool-Run fehlgeschlagen.', 'error');
    } finally {
      if (button) { button.disabled = false; button.textContent = `${(toolsState?.tools.find((tool) => tool.id === toolId)?.actions?.[0]?.label || 'RUN')} ↗`; }
    }
  }

  async function toggleTool(toolId, enabled) {
    if (offlineMode) { toast('Server nicht verbunden — Watch-Posture nicht gespeichert.', 'error'); return; }
    try {
      await request(`/api/tools/${encodeURIComponent(toolId)}/toggle`, { method: 'POST', body: JSON.stringify({ enabled }) });
      await Promise.all([loadState(false), loadTools(false)]);
      toast(`${toolId.toUpperCase()}: Watch-Posture ${enabled ? 'aktiviert' : 'pausiert'}.`, 'success');
    } catch (error) {
      toast(error.message || 'Watch-Posture konnte nicht gespeichert werden.', 'error');
    }
  }

  async function runToolSweep() {
    if (offlineMode) { toast('Server nicht verbunden — kein Audit gestartet.', 'error'); return; }
    if (!toolsState) await loadTools(false);
    const button = $('#runToolSweep');
    button.disabled = true;
    button.textContent = '✦ SAFE AUDIT LÄUFT …';
    $('#toolAuditState').innerHTML = '<i></i> AUDIT RUNNING';
    try {
      const jobs = (toolsState?.tools || []).map((tool) => ({ toolId: tool.id, action: tool.actions?.[0]?.id }));
      await Promise.all(jobs.filter((job) => job.action).map((job) => request(`/api/tools/${encodeURIComponent(job.toolId)}/run`, { method: 'POST', body: JSON.stringify({ action: job.action }) })));
      await Promise.all([loadState(false), loadTools(false)]);
      toast(`${jobs.length} allowlisted Tool-Checks abgeschlossen und auditiert.`, 'success');
      $('#toolAuditState').innerHTML = '<i></i> AUDIT READY';
    } catch (error) {
      toast(error.message || 'Safe Audit fehlgeschlagen.', 'error');
      $('#toolAuditState').innerHTML = '<i></i> AUDIT ERROR';
    } finally {
      button.disabled = false;
      button.textContent = '✦ SAFE AUDIT AUSFÜHREN';
    }
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
    const allowed = ['command', 'mesh', 'lab', 'ops', 'tools', 'drift', 'about'];
    currentView = allowed.includes(view) ? view : 'command';
    $$('.view-panel').forEach((panel) => panel.classList.toggle('view-panel--active', panel.dataset.viewPanel === currentView));
    $$('.nav-item').forEach((button) => button.classList.toggle('nav-item--active', button.dataset.view === currentView));
    $('#viewCrumb').textContent = ({ command: 'COMMAND DECK', mesh: 'AGENT MESH', lab: 'HONEYPOT LAB', ops: 'DEFENSE OPS', tools: 'TOOL ATLAS', drift: 'SIGNAL DRIFT', about: 'PROJECT BRIEF' })[currentView];
    renderTabGuide(currentView);
    if (currentView === 'ops') loadOpsOverview(false);
    if (currentView === 'tools') loadTools(false);
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

  async function runCapture() {
    if (offlineMode) { toast('Server nicht verbunden — Defense Ops bleibt im Demo-Modus.', 'error'); return; }
    const button = $('#runCapture');
    button.disabled = true;
    button.textContent = '↯ CAPTURE LÄUFT …';
    try {
      const result = await request('/api/ops/capture', {
        method: 'POST',
        body: JSON.stringify({
          interface: $('#captureInterface').value || 'lo',
          preset: $('#capturePreset').value,
          duration: $('#captureDuration').value,
          limit: $('#captureLimit').value
        })
      });
      lastCapture = result;
      await Promise.all([loadState(false), loadOpsOverview(false)]);
      toast(result.mode === 'simulation' ? 'Kein Capture-Tool gefunden — sichere Demo-Metadaten angezeigt.' : 'Metadaten-Capture abgeschlossen. Kein Payload angefordert.', result.ok ? 'success' : 'error');
    } catch (error) {
      toast(error.message || 'Capture konnte nicht gestartet werden.', 'error');
    } finally {
      button.disabled = false;
      button.textContent = '↯ CAPTURE STARTEN';
    }
  }

  async function checkProxy() {
    if (offlineMode) { toast('Server nicht verbunden — Proxychains wird nur lokal geprüft.', 'error'); return; }
    const button = $('#proxyCheck');
    button.disabled = true;
    button.textContent = '◎ PRÜFE …';
    try {
      const result = await request('/api/ops/proxy-check', { method: 'POST', body: '{}' });
      if (!opsState) opsState = clone(fallbackOps);
      opsState.proxy = result;
      renderOps();
      await loadState(false);
      toast(result.configured ? 'Proxychains-Binary und Config gefunden — keine Route gestartet.' : 'Proxychains ist nicht vollständig konfiguriert.', result.configured ? 'success' : 'normal');
    } catch (error) {
      toast(error.message || 'Proxychains-Check fehlgeschlagen.', 'error');
    } finally {
      button.disabled = false;
      button.textContent = '◎ PROFILE PRÜFEN';
    }
  }

  async function loadMacStatus(interfaceName) {
    if (!interfaceName || offlineMode) return;
    try {
      const result = await request(`/api/ops/mac?interface=${encodeURIComponent(interfaceName)}`);
      if (!opsState) opsState = clone(fallbackOps);
      opsState.mac = opsState.mac || {};
      opsState.mac[interfaceName] = result;
      renderOps();
    } catch (error) {
      toast(error.message || 'MAC-Status konnte nicht gelesen werden.', 'error');
    }
  }

  async function previewMac() {
    if (offlineMode) { toast('Server nicht verbunden — MAC bleibt unverändert.', 'error'); return; }
    const interfaceName = $('#macInterface').value || 'lo';
    const button = $('#macPreview');
    button.disabled = true;
    button.textContent = '◇ ERZEUGE VORSCHAU …';
    try {
      lastMacPreview = await request('/api/ops/mac-preview', { method: 'POST', body: JSON.stringify({ interface: interfaceName }) });
      renderOps();
      await loadState(false);
      toast('MAC-Rotation nur vorbereitet — Systemidentität nicht verändert.', 'success');
    } catch (error) {
      toast(error.message || 'MAC-Vorschau fehlgeschlagen.', 'error');
    } finally {
      button.disabled = false;
      button.textContent = '◇ ROTATION VORSCHAU';
    }
  }

  async function runSweep() {
    if (offlineMode) { toast('Server nicht verbunden — kein Sweep ausgeführt.', 'error'); return; }
    const button = $('#opsSweep');
    button.disabled = true;
    button.textContent = '✦ SWEEP LÄUFT …';
    try {
      await loadOpsOverview(false);
      const result = await request('/api/ops/capture', {
        method: 'POST',
        body: JSON.stringify({ interface: $('#captureInterface').value || 'lo', preset: $('#capturePreset').value || 'metadata', duration: 3, limit: 8 })
      });
      lastCapture = result;
      sweepRanAt = Date.now();
      await Promise.all([loadState(false), loadOpsOverview(false)]);
      renderOps();
      toast('Read-only Health Sweep abgeschlossen — Ergebnis im Audit Trail.', result.ok ? 'success' : 'normal');
    } catch (error) {
      toast(error.message || 'Health Sweep fehlgeschlagen.', 'error');
    } finally {
      button.disabled = false;
      button.textContent = '✦ SWEEP AUSFÜHREN';
    }
  }

  function startPrototypeInteraction() {
    const stage = $('#prototypeStage');
    if (!stage || !motionPreferred) return;
    stage.addEventListener('pointermove', (event) => {
      const bounds = stage.getBoundingClientRect();
      const x = (event.clientX - bounds.left) / bounds.width - .5;
      const y = (event.clientY - bounds.top) / bounds.height - .5;
      stage.style.setProperty('--preview-shift-x', `${(x * 8).toFixed(2)}px`);
      stage.style.setProperty('--preview-shift-y', `${(y * -5).toFixed(2)}px`);
    });
    stage.addEventListener('pointerleave', () => {
      stage.style.removeProperty('--preview-shift-x');
      stage.style.removeProperty('--preview-shift-y');
    });
  }

  function startLandingInteraction() {
    if (!motionPreferred) return;
    const visual = $('.hero-visual');
    if (visual) {
      visual.addEventListener('pointermove', (event) => {
        const bounds = visual.getBoundingClientRect();
        const x = (event.clientX - bounds.left) / bounds.width - .5;
        const y = (event.clientY - bounds.top) / bounds.height - .5;
        visual.style.setProperty('--tilt-x', `${(x * 5).toFixed(2)}deg`);
        visual.style.setProperty('--tilt-y', `${(-y * 5).toFixed(2)}deg`);
      });
      visual.addEventListener('pointerleave', () => {
        visual.style.removeProperty('--tilt-x');
        visual.style.removeProperty('--tilt-y');
      });
    }
    $$('.prototype-card').forEach((card) => {
      card.addEventListener('pointermove', (event) => {
        const bounds = card.getBoundingClientRect();
        const x = (event.clientX - bounds.left) / bounds.width - .5;
        const y = (event.clientY - bounds.top) / bounds.height - .5;
        card.style.setProperty('--card-ry', `${(x * 5).toFixed(2)}deg`);
        card.style.setProperty('--card-rx', `${(-y * 5).toFixed(2)}deg`);
      });
      card.addEventListener('pointerleave', () => {
        card.style.removeProperty('--card-rx');
        card.style.removeProperty('--card-ry');
      });
    });
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
    $$('[data-design-variant]').forEach((button) => button.addEventListener('click', () => openPrototypePreview(button.dataset.designVariant)));
    $('#clearPrototypeSelection')?.addEventListener('click', clearPrototypeDirection);
    $('#prototypeSelectButton')?.addEventListener('click', lockPrototypeDirection);
    $('#previewCaptureButton')?.addEventListener('click', capturePreviewMetadata);
    $('[data-close-prototype]')?.addEventListener('click', closePrototypePreview);
    $('#prototypeBackdrop')?.addEventListener('click', (event) => { if (event.target === $('#prototypeBackdrop')) closePrototypePreview(); });
    $$('.preview-agent').forEach((button) => button.addEventListener('click', () => handlePrototypeAgent(button.dataset.previewAgent)));
    $$('.preview-action').forEach((button) => button.addEventListener('click', () => handlePrototypeAction(button.dataset.previewAction)));
    $$('.preview-step').forEach((button) => button.addEventListener('click', () => handlePrototypeStep(button.dataset.previewStep)));
    $('[data-scroll-prototypes]')?.addEventListener('click', () => $('#design-lab')?.scrollIntoView({ behavior: motionPreferred ? 'smooth' : 'auto' }));
    $('#backToStart')?.addEventListener('click', () => { $('#appView').classList.add('is-hidden'); $('#startScreen').classList.remove('is-hidden'); window.scrollTo({ top: 0, behavior: 'auto' }); });
    $$('.nav-item').forEach((button) => button.addEventListener('click', () => setView(button.dataset.view)));
    $$('[data-view-link]').forEach((button) => button.addEventListener('click', () => { enterCockpit(currentView); setView(button.dataset.viewLink); }));
    $$('[data-plan-filter]').forEach((button) => button.addEventListener('click', () => { planFilter = button.dataset.planFilter; renderPlans(); }));
    $$('[data-tool-filter]').forEach((button) => button.addEventListener('click', () => { toolFilter = button.dataset.toolFilter; renderTools(); }));
    $('#toolSearch')?.addEventListener('input', (event) => { toolSearch = event.target.value; renderTools(); });
    $$('[data-open-modal]').forEach((button) => button.addEventListener('click', () => openModal(button.dataset.openModal)));
    $('#tabGuideAction')?.addEventListener('click', () => {
      const action = $('#tabGuideAction').dataset.guideAction;
      if (['plan', 'honeypot', 'message', 'agent'].includes(action)) openModal(action);
      else if (action === 'ops-sweep') runSweep();
      else if (action === 'tools-sweep') runToolSweep();
      else if (['command', 'mesh', 'lab', 'ops', 'tools', 'drift', 'about'].includes(action)) setView(action);
    });
    $$('[data-close-modal]').forEach((button) => button.addEventListener('click', closeModal));
    $('#modalBackdrop')?.addEventListener('click', (event) => { if (event.target === $('#modalBackdrop')) closeModal(); });
    document.addEventListener('keydown', (event) => { if (event.key === 'Escape') { if (!$('#prototypeBackdrop').classList.contains('is-hidden')) closePrototypePreview(); else closeModal(); } });
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
    $('#opsRefresh')?.addEventListener('click', () => loadOpsOverview(true));
    $('#runCapture')?.addEventListener('click', runCapture);
    $('#proxyCheck')?.addEventListener('click', checkProxy);
    $('#macInterface')?.addEventListener('change', () => { lastMacPreview = null; renderOps(); loadMacStatus($('#macInterface').value); });
    $('#macPreview')?.addEventListener('click', previewMac);
    $('#opsSweep')?.addEventListener('click', runSweep);
    $('#runToolSweep')?.addEventListener('click', runToolSweep);
    document.addEventListener('click', (event) => {
      const runButton = event.target.closest('[data-run-tool]');
      if (runButton) { event.preventDefault(); runTool(runButton.dataset.runTool, runButton.dataset.toolAction); return; }
      const toggleButton = event.target.closest('[data-toggle-tool]');
      if (toggleButton) { event.preventDefault(); toggleTool(toggleButton.dataset.toggleTool, toggleButton.dataset.toolEnabled !== 'true'); }
    });
    $('#planForm')?.addEventListener('submit', async (event) => { event.preventDefault(); const data = new FormData(event.target); const okay = await mutate('/api/plans', 'POST', Object.fromEntries(data.entries()), 'Plan gebroadcastet — jeder Agent sieht jetzt denselben nächsten Schritt.'); if (okay) { event.target.reset(); closeModal(); setView('mesh'); } });
    $('#honeypotForm')?.addEventListener('submit', async (event) => { event.preventDefault(); const data = new FormData(event.target); const okay = await mutate('/api/honeypots', 'POST', Object.fromEntries(data.entries()), 'Virtueller Decoy angelegt — noch kein Listener aktiv.'); if (okay) { event.target.reset(); closeModal(); setView('lab'); } });
    $('#messageForm')?.addEventListener('submit', async (event) => { event.preventDefault(); const data = new FormData(event.target); const okay = await mutate('/api/messages', 'POST', Object.fromEntries(data.entries()), 'Kontext an den Agent Mesh verteilt.'); if (okay) { event.target.reset(); closeModal(); setView('mesh'); } });
    $('#agentForm')?.addEventListener('submit', async (event) => { event.preventDefault(); const data = new FormData(event.target); const okay = await mutate('/api/agents', 'POST', Object.fromEntries(data.entries()), 'Agent ist online und im gemeinsamen Kontext registriert.'); if (okay) { event.target.reset(); closeModal(); setView('mesh'); } });
  }

  function updateClock() {
    const now = new Date();
    const time = now.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'UTC' });
    $('#clockTime').textContent = time;
    $('#landingTime').textContent = `${time} UTC`;
  }

  async function boot() {
    selectedPrototype = getStoredPrototype();
    renderPrototypeSelection();
    bindEvents();
    updateClock(); window.setInterval(updateClock, 1000);
    startPrototypeInteraction();
    startLandingInteraction();
    startBackgroundCanvas();
    await loadState(true);
    window.setInterval(() => { if (!document.hidden) loadState(false); }, 8000);
  }

  boot();
})();
