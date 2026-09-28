// Accessibility in every style world: axe-core (WCAG 2.1/2.2 A + AA), text contrast measured on
// the rendered pixels (covers the gradients and glows axe has to skip) and visible keyboard focus.
import assert from 'node:assert/strict';
import { test } from '../lib/harness.mjs';
import { MOBILE, STYLE_WORLDS, THEMES, VIEWS, assertClean, axeViolations, enterCockpit, openView, pause } from '../lib/app.mjs';
import { contrastFailures } from '../lib/contrast.mjs';

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"])';

/**
 * Tabs through every visible focusable element inside `root` and returns the ones whose
 * focused rendering is indistinguishable from their resting rendering.
 */
async function invisibleFocus(page, root) {
  const count = await page.evaluate((scopeSelector, focusable) => {
    const scope = document.querySelector(scopeSelector);
    const visible = (element) => {
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && !element.closest('.is-hidden, [inert]');
    };
    const look = (element) => {
      const style = getComputedStyle(element);
      return [style.outlineStyle === 'none' ? 'none' : `${style.outlineStyle} ${style.outlineWidth} ${style.outlineColor}`,
        style.boxShadow, style.borderColor, style.backgroundColor, style.color, style.textDecorationLine].join(' | ');
    };
    window.__focusTargets = [...scope.querySelectorAll(focusable)].filter(visible);
    window.__focusResting = window.__focusTargets.map(look);
    window.__focusLook = look;
    document.activeElement?.blur();
    window.scrollTo(0, 0);
    return window.__focusTargets.length;
  }, root, FOCUSABLE);
  assert.ok(count > 3, `${root}: found focusable elements (${count})`);
  const problems = new Set();
  const visited = new Set();
  for (let step = 0; step < count + 5 && visited.size < count; step += 1) {
    await page.keyboard.press('Tab');
    const result = await page.evaluate(() => {
      const index = window.__focusTargets.indexOf(document.activeElement);
      if (index < 0) return null;
      const element = document.activeElement;
      const name = element.id ? `#${element.id}` : `${element.tagName.toLowerCase()}${element.className ? `.${String(element.className).trim().split(/\s+/).join('.')}` : ''}`;
      const label = (element.getAttribute('aria-label') || element.textContent || '').trim().slice(0, 24);
      return { index, name: `${name} "${label}"`, same: window.__focusLook(element) === window.__focusResting[index] };
    });
    if (!result) continue;
    visited.add(result.index);
    if (result.same) problems.add(result.name);
  }
  return [...problems];
}

for (const theme of THEMES) {
  test(`a11y: ${theme} — landing page incl. Design Lab passes axe (WCAG A/AA)`, async ({ open }) => {
    const handle = await open({ theme });
    assert.deepEqual(await axeViolations(handle.page), []);
    await assertClean(handle);
  }, { timeout: 60_000 });

  test(`a11y: ${theme} — all seven cockpit views and the plan dialog pass axe`, async ({ open }) => {
    const handle = await open({ theme });
    const { page } = handle;
    await enterCockpit(page);
    const found = [];
    for (const view of VIEWS) {
      await openView(page, view);
      if (view === 'tools') await page.waitForSelector('#toolGrid .tool-card');
      found.push(...(await axeViolations(page, { context: '#appView' })).map((line) => `${view}: ${line}`));
    }
    await openView(page, 'command');
    await page.click('[data-open-modal="plan"]');
    await page.waitForSelector('#planModal:not(.is-hidden)');
    found.push(...(await axeViolations(page, { context: '#modalBackdrop' })).map((line) => `plan dialog: ${line}`));
    assert.deepEqual(found, []);
    await assertClean(handle);
  }, { timeout: 120_000 });

  for (const [label, viewport] of [['desktop', undefined], ['390 px', MOBILE]]) {
    test(`a11y: ${theme} — rendered text contrast meets AA on landing, views and dialog (${label})`, async ({ open }) => {
      const handle = await open({ theme, viewport });
      const { page } = handle;
      const found = (await contrastFailures(page, '#startScreen')).map((line) => `landing: ${line}`);
      await enterCockpit(page);
      for (const view of VIEWS) {
        await openView(page, view);
        if (view === 'tools') await page.waitForSelector('#toolGrid .tool-card');
        found.push(...(await contrastFailures(page, '#appView')).map((line) => `${view}: ${line}`));
      }
      await openView(page, 'command');
      await page.click('[data-open-modal="plan"]');
      await page.waitForSelector('#planModal:not(.is-hidden)');
      found.push(...(await contrastFailures(page, '#modalBackdrop')).map((line) => `plan dialog: ${line}`));
      assert.deepEqual(found, []);
      await assertClean(handle);
    }, { timeout: 120_000 });
  }

  test(`a11y: ${theme} — keyboard focus is visible on the landing page and in the cockpit`, async ({ open }) => {
    const handle = await open({ theme });
    const { page } = handle;
    assert.deepEqual(await invisibleFocus(page, '#startScreen'), [], 'landing');
    await enterCockpit(page);
    assert.deepEqual(await invisibleFocus(page, '#appView'), [], 'cockpit');
    await assertClean(handle);
  }, { timeout: 90_000 });
}

test('a11y: every preview dialog (4 studies, 5 style worlds) passes axe and the contrast check', async ({ open }) => {
  const handle = await open({ theme: 'nightwatch' });
  const { page } = handle;
  const found = [];
  const triggers = [
    ...['nightwatch', 'orbit', 'tactical', 'theatre'].map((name) => `[data-design-variant="${name}"]`),
    ...STYLE_WORLDS.map((name) => `[data-theme-preview="${name}"]`),
  ];
  for (const trigger of triggers) {
    await page.click(trigger);
    await page.waitForSelector('#prototypeBackdrop:not(.is-hidden)');
    await pause(60);
    found.push(...(await axeViolations(page, { context: '#prototypeBackdrop' })).map((line) => `${trigger}: ${line}`));
    found.push(...(await contrastFailures(page, '#prototypeBackdrop')).map((line) => `${trigger}: ${line}`));
    await page.keyboard.press('Escape');
    await page.waitForSelector('#prototypeBackdrop.is-hidden');
  }
  assert.deepEqual(found, []);
  await assertClean(handle);
}, { timeout: 120_000 });
