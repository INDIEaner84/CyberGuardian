// Page-level helpers for the CyberGuardian cockpit.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);

export const THEMES = ['nightwatch', 'enterprise', 'akira', 'cyberpunk', 'agentur', 'uboot'];
export const STYLE_WORLDS = THEMES.slice(1);
export const VIEWS = ['command', 'mesh', 'lab', 'ops', 'tools', 'drift', 'about'];
export const MOBILE = { width: 390, height: 844, deviceScaleFactor: 1, isMobile: true, hasTouch: true };
export const TABLET = { width: 820, height: 1180 };

export const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/** Theme currently painted on <html> (Nightwatch has no attribute). */
export function paintedTheme(page) {
  return page.evaluate(() => document.documentElement.getAttribute('data-theme') || 'nightwatch');
}

/** Theme persisted by the app (null = default). */
export function storedTheme(page) {
  return page.evaluate(() => localStorage.getItem('cyberguardian.theme'));
}

export async function chooseTheme(page, theme, scope = '.landing-topline') {
  await page.select(`${scope} select[data-theme-select]`, theme);
  await page.waitForFunction((expected) => (document.documentElement.getAttribute('data-theme') || 'nightwatch') === expected, { timeout: 5000 }, theme);
  await page.evaluate(() => document.fonts.ready.then(() => true));
}

export async function isVisible(page, selector) {
  return page.$eval(selector, (element) => {
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0 && !element.closest('.is-hidden');
  }).catch(() => false);
}

export async function enterCockpit(page, view = 'command') {
  await page.click('[data-enter="command"]');
  await page.waitForSelector('#appView:not(.is-hidden)', { timeout: 5000 });
  if (view !== 'command') await openView(page, view);
}

export async function openView(page, view) {
  await page.click(`.nav-item[data-view="${view}"]`);
  await page.waitForSelector(`.view-panel--active[data-view-panel="${view}"]`, { timeout: 5000 });
  await page.evaluate(() => document.fonts.ready.then(() => true));
}

/** Name of the element that currently has focus, for readable assertions. */
export function focusedDescription(page) {
  return page.evaluate(() => {
    const element = document.activeElement;
    if (!element || element === document.body) return 'body';
    const id = element.id ? `#${element.id}` : '';
    const data = [...element.attributes].filter((attribute) => attribute.name.startsWith('data-')).map((attribute) => (attribute.value ? `[${attribute.name}="${attribute.value}"]` : `[${attribute.name}]`)).join('');
    return `${element.tagName.toLowerCase()}${id}${data}`;
  });
}

/** No console errors, failed requests, HTTP errors or CSP violations on this page. */
export async function assertClean(handle, label = 'page') {
  const csp = await handle.cspViolations();
  assert.deepEqual(csp, [], `${label}: Content-Security-Policy violations`);
  assert.deepEqual(handle.issues, [], `${label}: console/network problems`);
}

/**
 * Elements whose box leaves the viewport horizontally without being clipped by a
 * scroll/clip container inside it (html/body clipping hides real overflow, so it does not count).
 */
export function horizontalOverflow(page) {
  return page.evaluate(() => {
    const viewport = document.documentElement.clientWidth;
    const selector = 'a, button, input, select, textarea, label, h1, h2, h3, h4, p, li, td, th, dt, dd, strong, img, canvas, svg, [role="button"]';
    const within = (rect) => rect.left >= -1 && rect.right <= viewport + 1;
    // Content inside a horizontal scroller can be reached by scrolling; content cut off by
    // overflow: hidden / clip is lost — that counts as overflow too.
    const scrolls = (element) => /auto|scroll/.test(getComputedStyle(element).overflowX);
    const offenders = [];
    for (const element of document.querySelectorAll(selector)) {
      if (element.closest('[aria-hidden="true"], .is-hidden, [hidden]')) continue;
      const rect = element.getBoundingClientRect();
      if (rect.width < 1 || rect.height < 1 || within(rect)) continue;
      const style = getComputedStyle(element);
      if (style.visibility === 'hidden' || Number(style.opacity) === 0) continue;
      let reachable = false;
      for (let parent = element.parentElement; parent && parent !== document.body; parent = parent.parentElement) {
        if (scrolls(parent) && within(parent.getBoundingClientRect())) { reachable = true; break; }
      }
      if (reachable) continue;
      const name = element.id ? `#${element.id}` : `${element.tagName.toLowerCase()}.${[...element.classList].join('.')}`;
      offenders.push(`${name} "${(element.textContent || '').trim().slice(0, 30)}" [${Math.round(rect.left)}…${Math.round(rect.right)} of ${viewport}]`);
    }
    return offenders;
  });
}

/** Pairs of the given elements whose boxes overlap (hidden elements are ignored). */
export function overlappingPairs(page, selectors) {
  return page.evaluate((list) => {
    const boxes = list.map((selector) => {
      const element = document.querySelector(selector);
      if (!element) return null;
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      if (style.display === 'none' || style.visibility === 'hidden' || rect.width < 1 || rect.height < 1) return null;
      return { selector, rect };
    }).filter(Boolean);
    const overlaps = [];
    for (let i = 0; i < boxes.length; i += 1) {
      for (let j = i + 1; j < boxes.length; j += 1) {
        const a = boxes[i].rect; const b = boxes[j].rect;
        const x = Math.min(a.right, b.right) - Math.max(a.left, b.left);
        const y = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
        if (x > 1 && y > 1) overlaps.push(`${boxes[i].selector} × ${boxes[j].selector}`);
      }
    }
    return overlaps;
  }, selectors);
}

let axeSource = null;

/**
 * Runs axe-core (WCAG 2.1 A/AA) on the page. Returns readable violation lines.
 * @param {object} [options]
 * @param {string|object} [options.context] axe context (defaults to the whole document)
 */
// Faded, aria-hidden ornaments (WCAG 1.4.3 exempts pure decoration). Nothing focusable lives inside.
const DECORATIVE = ['.rail-orbit'];

export async function axeViolations(page, { context = null } = {}) {
  axeSource ??= fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
  if (!(await page.evaluate(() => Boolean(window.axe)))) await page.evaluate(axeSource);
  const violations = await page.evaluate(async (scope, decorative) => {
    const include = scope ? [[scope]] : [['html']];
    const result = await window.axe.run({ include, exclude: decorative.map((selector) => [selector]) }, {
      runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'] },
      resultTypes: ['violations'],
    });
    return result.violations.map((violation) => ({
      id: violation.id,
      impact: violation.impact,
      nodes: violation.nodes.map((node) => {
        const check = node.any[0] || node.all[0] || node.none[0];
        return `${node.target.join(' ')} — ${(check?.message || node.failureSummary || '').split('\n')[0].slice(0, 180)}`;
      }),
    }));
  }, context, DECORATIVE);
  return violations.flatMap((violation) => violation.nodes.map((node) => `[${violation.impact}] ${violation.id}: ${node}`));
}

/** Samples the drift canvas; returns average colour and share of painted pixels. */
export function canvasStats(page, selector) {
  return page.$eval(selector, (canvas) => {
    const context = canvas.getContext('2d');
    const { width, height } = canvas;
    if (!width || !height) return { painted: 0, average: [0, 0, 0] };
    const data = context.getImageData(0, 0, width, height).data;
    let painted = 0; const sum = [0, 0, 0]; let samples = 0;
    for (let index = 0; index < data.length; index += 4 * 97) {
      samples += 1;
      if (data[index + 3] > 0) { painted += 1; sum[0] += data[index]; sum[1] += data[index + 1]; sum[2] += data[index + 2]; }
    }
    return { painted: painted / samples, average: sum.map((value) => Math.round(value / Math.max(painted, 1))) };
  });
}
