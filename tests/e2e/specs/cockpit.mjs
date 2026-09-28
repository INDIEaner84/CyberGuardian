// Cockpit flows against the real control plane API.
import assert from 'node:assert/strict';
import { test } from '../lib/harness.mjs';
import { VIEWS, assertClean, enterCockpit, focusedDescription, isVisible, openView, pause } from '../lib/app.mjs';

const CRUMBS = {
  command: 'COMMAND DECK', mesh: 'AGENT MESH', lab: 'HONEYPOT LAB', ops: 'DEFENSE OPS',
  tools: 'TOOL ATLAS', drift: 'SIGNAL DRIFT', about: 'PROJECT BRIEF',
};

test('cockpit: every rail entry activates its panel, crumb and tab guide', async ({ open }) => {
  const handle = await open();
  const { page } = handle;
  await enterCockpit(page);
  assert.equal(await page.$eval('#syncState', (element) => element.textContent.trim()), 'LIVE', 'control plane reachable');
  for (const view of VIEWS) {
    await openView(page, view);
    const snapshot = await page.evaluate(() => ({
      active: [...document.querySelectorAll('.view-panel--active')].map((panel) => panel.dataset.viewPanel),
      nav: [...document.querySelectorAll('.nav-item--active')].map((item) => item.dataset.view),
      crumb: document.querySelector('#viewCrumb').textContent.trim(),
      guide: document.querySelector('#tabGuideTitle').textContent.trim(),
    }));
    assert.deepEqual(snapshot.active, [view], `${view}: exactly one panel visible`);
    assert.deepEqual(snapshot.nav, [view], `${view}: rail highlights the entry`);
    assert.equal(snapshot.crumb, CRUMBS[view]);
    assert.ok(snapshot.guide.length > 0, `${view}: tab guide explains the view`);
  }
  await assertClean(handle);
});

test('cockpit: dialogs take focus, trap Tab, close on Escape and return focus', async ({ open }) => {
  const handle = await open();
  const { page } = handle;
  await enterCockpit(page);
  const trigger = '[data-open-modal="plan"]';
  await page.focus(trigger);
  await page.keyboard.press('Enter');
  await page.waitForSelector('#planModal:not(.is-hidden)');
  await pause(80);
  assert.equal(await focusedDescription(page), 'input', 'first field focused');
  for (let index = 0; index < 12; index += 1) {
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.querySelector('#planModal').contains(document.activeElement)), true, `Tab #${index + 1} stays inside the dialog`);
  }
  await page.keyboard.down('Shift');
  for (let index = 0; index < 8; index += 1) await page.keyboard.press('Tab');
  await page.keyboard.up('Shift');
  assert.equal(await page.evaluate(() => document.querySelector('#planModal').contains(document.activeElement)), true, 'Shift+Tab stays inside the dialog');
  await page.keyboard.press('Escape');
  await page.waitForSelector('#modalBackdrop.is-hidden');
  assert.match(await focusedDescription(page), /\[data-open-modal="plan"\]/, 'focus returns to the trigger');
  await assertClean(handle);
});

test('cockpit: a new plan round-trips through the API into the plan board', async ({ open, base }) => {
  const handle = await open();
  const { page } = handle;
  await enterCockpit(page);
  await page.click('[data-open-modal="plan"]');
  await page.waitForSelector('#planModal:not(.is-hidden)');
  const title = `E2E Evidence Relay ${Date.now().toString(36)}`;
  await page.type('#planForm input[name="title"]', title);
  await page.type('#planForm textarea[name="objective"]', 'Browser-Test: Plan anlegen, broadcasten und im Board wiederfinden.');
  await page.click('#planForm button[type="submit"]');
  await page.waitForSelector('#modalBackdrop.is-hidden');
  await page.waitForSelector('.view-panel--active[data-view-panel="mesh"]');
  const api = await (await fetch(`${base}/api/state`)).json();
  const stored = api.plans.find((plan) => plan.title === title);
  assert.ok(stored, `plan persisted in the control plane (got: ${api.plans.map((plan) => JSON.stringify(plan.title)).join(', ')})`);
  await openView(page, 'command');
  await page.waitForFunction((expected) => [...document.querySelectorAll('#planList .plan-title')].some((element) => element.textContent === expected), { timeout: 5000 }, title);
  await assertClean(handle);
});

test('cockpit: honeypot lab creates, activates and feeds a synthetic signal', async ({ open, base }) => {
  const handle = await open();
  const { page } = handle;
  await enterCockpit(page, 'lab');
  await page.click('[data-open-modal="honeypot"]');
  await page.waitForSelector('#honeypotModal:not(.is-hidden)');
  const name = `E2E-${Date.now().toString(36).slice(-5).toUpperCase()}`;
  await page.type('#honeypotForm input[name="name"]', name);
  await page.click('#honeypotForm button[type="submit"]');
  await page.waitForSelector('#modalBackdrop.is-hidden');
  const pot = (await (await fetch(`${base}/api/state`)).json()).honeypots.find((item) => item.name === name);
  assert.ok(pot, 'decoy persisted');
  assert.notEqual(pot.status, 'active', 'new decoys start without a listener');
  await page.waitForSelector(`#labPotGrid [data-toggle-pot="${pot.id}"]`);
  await page.click(`#labPotGrid [data-toggle-pot="${pot.id}"]`);
  await page.waitForFunction((id) => document.querySelector(`#labPotGrid [data-toggle-pot="${id}"]`)?.textContent.includes('DEACTIVATE'), { timeout: 5000 }, pot.id);
  const before = await page.$$eval('#signalTable tr, #signalTable .signal-row, #signalTable article', (rows) => rows.length);
  await page.click(`#labPotGrid [data-simulate-pot="${pot.id}"]`);
  await page.waitForFunction((count) => document.querySelectorAll('#signalTable tr, #signalTable .signal-row, #signalTable article').length > count, { timeout: 5000 }, before);
  const after = (await (await fetch(`${base}/api/state`)).json()).honeypots.find((item) => item.id === pot.id);
  assert.ok(after.signals >= 1, 'synthetic signal counted on the decoy');
  await assertClean(handle);
});

test('cockpit: tool atlas search narrows the catalog and an allowlisted action is audited', async ({ open }) => {
  const handle = await open();
  const { page } = handle;
  await enterCockpit(page, 'tools');
  await page.waitForSelector('#toolGrid .tool-card');
  const total = await page.$$eval('#toolGrid .tool-card', (cards) => cards.length);
  assert.ok(total >= 10, `catalog lists the known modules (got ${total})`);
  await page.type('#toolSearch', 'wireguard');
  const filtered = await page.$$eval('#toolGrid .tool-card h3', (titles) => titles.map((title) => title.textContent));
  assert.ok(filtered.length >= 1 && filtered.length < total, `search narrows the grid (${filtered.join(', ')})`);
  assert.ok(filtered.every((title) => /wire/i.test(title)), 'only matching modules remain');
  const runsBefore = await page.$eval('#toolRunCount', (element) => Number.parseInt(element.textContent, 10) || 0);
  await page.click('#toolGrid .tool-card [data-run-tool]');
  await page.waitForFunction((count) => (Number.parseInt(document.querySelector('#toolRunCount').textContent, 10) || 0) > count, { timeout: 15000 }, runsBefore);
  await page.$eval('#toolSearch', (input) => input.select());
  await page.keyboard.press('Backspace');
  assert.equal(await page.$$eval('#toolGrid .tool-card', (cards) => cards.length), total, 'clearing the search restores the catalog');
  await assertClean(handle);
});

test('cockpit: motion toggle pauses the canvases and is remembered', async ({ open }) => {
  const handle = await open({ reducedMotion: false, storage: { 'cyberguardian.reduceMotion': null } });
  const { page } = handle;
  await enterCockpit(page);
  assert.equal(await page.evaluate(() => document.body.classList.contains('reduce-motion')), false);
  await page.click('#motionToggle');
  assert.equal(await page.evaluate(() => document.body.classList.contains('reduce-motion')), true);
  assert.equal(await page.$eval('#motionToggle', (button) => button.getAttribute('aria-pressed')), 'true');
  assert.equal(await page.evaluate(() => localStorage.getItem('cyberguardian.reduceMotion')), '1');
  const running = await page.evaluate(() => document.getAnimations().filter((animation) => animation.playState === 'running' && animation.effect?.getTiming().iterations === Infinity).length);
  assert.equal(running, 0, 'no infinite CSS animation keeps running');
  await page.reload({ waitUntil: 'networkidle0' });
  assert.equal(await page.evaluate(() => document.body.classList.contains('reduce-motion')), true, 'preference survives reload');
  await assertClean(handle);
});

test('cockpit: an unreachable control plane degrades to the local demo', async ({ open }) => {
  const handle = await open({ path: null, ignore: [/HTTP 503/, /Failed to load resource/] });
  const { page } = handle;
  await page.setRequestInterception(true);
  page.on('request', (request) => {
    if (new URL(request.url()).pathname.startsWith('/api/')) request.respond({ status: 503, contentType: 'application/json', body: '{"error":"offline"}' });
    else request.continue();
  });
  await page.goto(new URL('/', handle.base).href, { waitUntil: 'networkidle0' });
  await enterCockpit(page);
  await page.waitForFunction(() => document.querySelector('#syncState').textContent.includes('DEMO'), { timeout: 5000 });
  assert.equal(await isVisible(page, '#planList'), true, 'demo data still renders');
  assert.ok(await page.$$eval('#planList .plan-row', (rows) => rows.length) > 0, 'fallback plans shown');
  await assertClean(handle);
});
