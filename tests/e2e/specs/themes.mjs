// Style worlds: switching, persistence, previews, cross-tab sync and canvas palettes.
import assert from 'node:assert/strict';
import { test } from '../lib/harness.mjs';
import {
  STYLE_WORLDS, THEMES, assertClean, canvasStats, chooseTheme, enterCockpit, focusedDescription,
  isVisible, openView, paintedTheme, pause, storedTheme,
} from '../lib/app.mjs';

const pageColours = (page) => page.evaluate(() => ({
  background: getComputedStyle(document.body).backgroundColor,
  text: getComputedStyle(document.querySelector('.hero-copy p') || document.body).color,
  meta: document.querySelector('meta[name="theme-color"]').content,
  headline: getComputedStyle(document.querySelector('h1')).fontFamily,
}));

test('landing: renders cleanly with a visible hero and no CSP, console or network problems', async ({ open }) => {
  const handle = await open();
  const hero = await handle.page.$eval('h1', (element) => ({ text: element.textContent.trim(), opacity: getComputedStyle(element).opacity }));
  assert.ok(hero.text.length > 10, 'hero headline has text');
  assert.equal(hero.opacity, '1', 'hero is not frozen invisible under reduced motion');
  assert.equal(await paintedTheme(handle.page), 'nightwatch');
  await assertClean(handle);
});

test('themes: every style world applies from the STIL switch, persists and recolours the page', async ({ open }) => {
  const handle = await open({ theme: 'nightwatch' });
  const { page } = handle;
  const base = await pageColours(page);
  const seen = new Map([['nightwatch', base]]);
  for (const theme of STYLE_WORLDS) {
    await chooseTheme(page, theme);
    assert.equal(await storedTheme(page), theme, `${theme} persisted in localStorage`);
    const colours = await pageColours(page);
    assert.notEqual(colours.meta, base.meta, `${theme} sets its own meta theme-color`);
    assert.notEqual(colours.headline, base.headline, `${theme} swaps the headline typography`);
    for (const [other, previous] of seen) {
      assert.ok(colours.background !== previous.background || colours.text !== previous.text, `${theme} looks different from ${other}`);
    }
    seen.set(theme, colours);
    const status = await page.$eval('#themeStatus', (element) => element.textContent.trim());
    assert.ok(status.length > 0, 'Design Lab status names the active world');
    assert.equal(await page.$eval(`.world-card[data-theme="${theme}"]`, (card) => card.classList.contains('is-active')), true, `${theme} card marked active`);
  }
  await chooseTheme(page, 'nightwatch');
  assert.equal(await storedTheme(page), null, 'default look removes the stored choice');
  assert.deepEqual(await pageColours(page), base, 'Nightwatch is restored exactly');
  await assertClean(handle);
});

test('themes: stored world is painted before <body> exists (no flash of the default look)', async ({ open, base }) => {
  const handle = await open({ theme: 'uboot', path: null });
  const { page } = handle;
  await page.evaluateOnNewDocument(() => {
    const observer = new MutationObserver(() => {
      if (!document.body) return;
      window.__themeAtBody = document.documentElement.getAttribute('data-theme');
      observer.disconnect();
    });
    observer.observe(document, { childList: true, subtree: true });
  });
  await page.goto(new URL('/', base).href, { waitUntil: 'networkidle0' });
  assert.equal(await page.evaluate(() => window.__themeAtBody), 'uboot');
  await page.reload({ waitUntil: 'networkidle0' });
  assert.equal(await page.evaluate(() => window.__themeAtBody), 'uboot', 'still painted early after reload');
  assert.equal(await page.$eval('.landing-topline select[data-theme-select]', (select) => select.value), 'uboot');
  await assertClean(handle);
});

test('themes: an unknown stored value falls back to Nightwatch', async ({ open }) => {
  const handle = await open({ storage: { 'cyberguardian.theme': '"><img src=x onerror=alert(1)>' } });
  assert.equal(await paintedTheme(handle.page), 'nightwatch');
  assert.equal(await handle.page.$eval('.landing-topline select[data-theme-select]', (select) => select.value), 'nightwatch');
  await assertClean(handle);
});

test('themes: STANDARD ↺ returns to Nightwatch and clears the choice', async ({ open }) => {
  const handle = await open({ theme: 'cyberpunk' });
  const { page } = handle;
  assert.equal(await paintedTheme(page), 'cyberpunk');
  assert.equal(await page.$eval('#themeReset', (button) => button.disabled), false);
  await page.click('#themeReset');
  assert.equal(await paintedTheme(page), 'nightwatch');
  assert.equal(await storedTheme(page), null);
  assert.equal(await page.$eval('#themeReset', (button) => button.disabled), true, 'reset disabled once on default');
  await assertClean(handle);
});

test('themes: VORSCHAU recolours temporarily; Escape restores the applied world and focus', async ({ open }) => {
  const handle = await open({ theme: 'akira' });
  const { page } = handle;
  const trigger = '[data-theme-preview="cyberpunk"]';
  await page.focus(trigger);
  await page.keyboard.press('Enter');
  await page.waitForSelector('#prototypeBackdrop:not(.is-hidden)');
  assert.equal(await paintedTheme(page), 'cyberpunk', 'preview paints the whole page');
  assert.equal(await storedTheme(page), 'akira', 'preview does not persist');
  await pause(80);
  assert.equal(await focusedDescription(page), 'button[data-close-prototype]', 'focus moves to the close button');
  await page.keyboard.press('Escape');
  await page.waitForSelector('#prototypeBackdrop.is-hidden');
  assert.equal(await paintedTheme(page), 'akira', 'closing restores the applied world');
  assert.equal(await focusedDescription(page), `button${trigger}`, 'focus returns to the trigger');
  await assertClean(handle);
});

test('themes: DIESES THEME NUTZEN inside the preview applies the world', async ({ open }) => {
  const handle = await open({ theme: 'nightwatch' });
  const { page } = handle;
  await page.click('[data-theme-preview="uboot"]');
  await page.waitForSelector('#prototypeBackdrop:not(.is-hidden)');
  assert.match(await page.$eval('#prototypeSelectButton', (button) => button.textContent), /NUTZEN/);
  await page.click('#prototypeSelectButton');
  assert.equal(await storedTheme(page), 'uboot');
  assert.match(await page.$eval('#prototypeSelectButton', (button) => button.textContent), /AKTIV/);
  await page.click('[data-close-prototype]');
  await page.waitForSelector('#prototypeBackdrop.is-hidden');
  assert.equal(await paintedTheme(page), 'uboot', 'world stays applied after closing');
  await assertClean(handle);
});

test('themes: the four design studies preview in the Nightwatch palette under any world', async ({ open }) => {
  const handle = await open({ theme: 'enterprise' });
  const { page } = handle;
  const studies = await page.$$eval('[data-design-variant]', (buttons) => [...new Set(buttons.map((button) => button.dataset.designVariant))]);
  assert.deepEqual(studies.sort(), ['nightwatch', 'orbit', 'tactical', 'theatre']);
  for (const study of studies) {
    await page.click(`[data-design-variant="${study}"]`);
    await page.waitForSelector('#prototypeBackdrop:not(.is-hidden)');
    assert.equal(await paintedTheme(page), 'nightwatch', `${study} study is drawn in Nightwatch`);
    assert.equal(await page.$eval('#prototypeStage', (stage) => stage.dataset.variant), study);
    await page.keyboard.press('Escape');
    await page.waitForSelector('#prototypeBackdrop.is-hidden');
    assert.equal(await paintedTheme(page), 'enterprise', `closing ${study} restores Enterprise`);
  }
  await assertClean(handle);
});

test('themes: a choice made in one tab follows in the other open tabs', async ({ open }) => {
  const first = await open({ theme: 'nightwatch' });
  const second = await open({ context: first.context });
  await enterCockpit(second.page);
  await chooseTheme(first.page, 'agentur');
  await second.page.waitForFunction(() => document.documentElement.getAttribute('data-theme') === 'agentur', { timeout: 5000 });
  assert.equal(await second.page.$eval('.topbar select[data-theme-select]', (select) => select.value), 'agentur');
  await chooseTheme(second.page, 'nightwatch', '.topbar');
  await first.page.waitForFunction(() => !document.documentElement.hasAttribute('data-theme'), { timeout: 5000 });
  await assertClean(first, 'first tab');
  await assertClean(second, 'second tab');
});

test('themes: cockpit topbar switch and landing switch stay in sync', async ({ open }) => {
  const handle = await open({ theme: 'nightwatch' });
  const { page } = handle;
  await enterCockpit(page);
  assert.equal(await isVisible(page, '.topbar select[data-theme-select]'), true, 'STIL switch visible in the cockpit');
  await chooseTheme(page, 'enterprise', '.topbar');
  await page.click('#backToStart');
  await page.waitForSelector('#startScreen:not(.is-hidden)');
  assert.equal(await page.$eval('.landing-topline select[data-theme-select]', (select) => select.value), 'enterprise');
  await assertClean(handle);
});

test('themes: the Signal Drift canvas paints a distinct scene in every world', async ({ open }) => {
  const handle = await open({ theme: 'nightwatch' });
  const { page } = handle;
  await enterCockpit(page, 'drift');
  const averages = new Map();
  for (const theme of THEMES) {
    await chooseTheme(page, theme, '.topbar');
    await pause(60);
    const stats = await canvasStats(page, '#driftCanvas');
    assert.ok(stats.painted > 0.95, `${theme}: drift scene covers the canvas (got ${stats.painted.toFixed(2)})`);
    averages.set(theme, stats.average.join(','));
  }
  assert.equal(new Set(averages.values()).size, THEMES.length, `each world paints its own palette: ${[...averages].map(([key, value]) => `${key}=${value}`).join(' ')}`);
  await openView(page, 'command');
  await assertClean(handle);
});
