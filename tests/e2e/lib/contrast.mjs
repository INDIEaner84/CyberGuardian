// Rendered text contrast (WCAG 1.4.3) measured on real pixels.
//
// axe-core skips text over gradients, images, pseudo-elements and translucent
// layers ("incomplete") — exactly what the HUD themes are made of. This check
// hides all glyphs, screenshots the page and compares every text colour with the
// pixels actually painted behind it, so gradients and glows are covered too.
import { decodePng } from './png.mjs';

const HIDE_TEXT_CSS = `
  [data-cg-probe], [data-cg-probe] *, [data-cg-probe]::before, [data-cg-probe]::after,
  [data-cg-probe] *::before, [data-cg-probe] *::after, [data-cg-probe]::placeholder {
    color: transparent !important; -webkit-text-fill-color: transparent !important;
    -webkit-text-stroke-color: transparent !important; text-shadow: none !important;
    text-decoration-color: transparent !important; caret-color: transparent !important;
    transition: none !important;
  }`;

/** Marks every visible text-bearing element inside `root` and records its colours. */
function collectProbes(root) {
  const scope = document.querySelector(root);
  if (!scope) return [];
  const parse = (value) => {
    const match = value.match(/rgba?\(([^)]+)\)/);
    if (!match) return null;
    const parts = match[1].split(/[\s,/]+/).filter(Boolean).map(Number);
    return [parts[0], parts[1], parts[2], parts.length > 3 ? parts[3] : 1];
  };
  const groups = new Map();
  const walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT, {
    acceptNode: (node) => (node.nodeValue.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT),
  });
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const element = node.parentElement;
    if (!element) continue;
    if (!groups.has(element)) groups.set(element, []);
    groups.get(element).push(node);
  }
  // Form controls show their value without a text node.
  for (const control of scope.querySelectorAll('select, textarea, input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"]):not([type="range"]):not([type="color"])')) {
    const label = control.tagName === 'SELECT' ? control.selectedOptions[0]?.textContent : control.value;
    if (label && label.trim()) groups.set(control, [{ nodeValue: label }]);
  }
  const probes = [];
  for (const [element, nodes] of groups) {
    if (element.closest('[aria-hidden="true"], [inert], .is-hidden, [hidden], script, style, noscript, template, option, canvas, svg')) continue;
    if (element.closest('button:disabled, input:disabled, select:disabled, textarea:disabled, fieldset:disabled, [aria-disabled="true"]')) continue;
    const style = getComputedStyle(element);
    if (style.visibility !== 'visible') continue;
    // Closed <details>, content-visibility and friends: laid out but not painted.
    if (element.checkVisibility && !element.checkVisibility({ visibilityProperty: true, contentVisibilityAuto: true })) continue;
    let opacity = 1;
    for (let current = element; current; current = current.parentElement) opacity *= Number(getComputedStyle(current).opacity);
    if (opacity < 0.02) continue;
    let colour = parse(style.webkitTextFillColor) || parse(style.color);
    const strokeWidth = Number.parseFloat(style.webkitTextStrokeWidth) || 0;
    if (colour && colour[3] === 0 && strokeWidth > 0) colour = parse(style.webkitTextStrokeColor);
    if (!colour || colour[3] === 0) continue; // gradient / clipped text cannot be judged by colour
    const index = probes.length;
    element.setAttribute('data-cg-probe', String(index));
    const text = nodes.map((node) => node.nodeValue).join(' ').replace(/\s+/g, ' ').trim();
    const id = element.id ? `#${element.id}` : '';
    const classes = [...element.classList].slice(0, 2).map((name) => `.${name}`).join('');
    probes.push({
      index,
      name: `${element.tagName.toLowerCase()}${id}${classes}`,
      text: text.slice(0, 32),
      colour: [colour[0], colour[1], colour[2], colour[3] * opacity],
      size: Number.parseFloat(style.fontSize),
      weight: Number.parseInt(style.fontWeight, 10) || 400,
    });
  }
  return probes;
}

/**
 * Visible text boxes (CSS px, viewport coordinates) for the pending probes that are entirely
 * on screen right now. Only the unclipped part counts (ellipsis); clipped-away text (sr-only) is skipped.
 */
function measureProbes(pending) {
  const viewportWidth = document.documentElement.clientWidth;
  const viewportHeight = window.innerHeight;
  const range = document.createRange();
  const intersect = (a, b) => ({ left: Math.max(a.left, b.left), top: Math.max(a.top, b.top), right: Math.min(a.right, b.right), bottom: Math.min(a.bottom, b.bottom) });
  const area = (box) => Math.max(0, box.right - box.left) * Math.max(0, box.bottom - box.top);
  const textRects = (element) => {
    if (element.matches('select, textarea, input')) {
      const box = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      const inset = (side) => (Number.parseFloat(style[`padding${side}`]) || 0) + (Number.parseFloat(style[`border${side}Width`]) || 0);
      const arrow = element.tagName === 'SELECT' ? 18 : 0;
      return [{ left: box.left + inset('Left'), top: box.top + inset('Top'), right: box.right - inset('Right') - arrow, bottom: box.bottom - inset('Bottom') }];
    }
    const rects = [];
    for (const node of element.childNodes) {
      if (node.nodeType !== Node.TEXT_NODE || !node.nodeValue.trim()) continue;
      range.selectNodeContents(node);
      for (const rect of range.getClientRects()) rects.push({ left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom });
    }
    return rects.filter((rect) => area(rect) >= 1);
  };
  const result = {};
  for (const index of pending) {
    const element = document.querySelector(`[data-cg-probe="${index}"]`);
    if (!element) { result[index] = { skip: true }; continue; }
    let clip = { left: -1e6, top: -1e6, right: 1e6, bottom: 1e6 };
    for (let parent = element; parent && parent !== document.body; parent = parent.parentElement) {
      const style = getComputedStyle(parent);
      if (style.overflowX !== 'visible' || style.overflowY !== 'visible') clip = intersect(clip, parent.getBoundingClientRect());
    }
    const rects = textRects(element);
    const total = rects.reduce((sum, rect) => sum + area(rect), 0);
    const shown = rects.map((rect) => intersect(rect, clip)).filter((box) => area(box) >= 1);
    const visible = shown.reduce((sum, box) => sum + area(box), 0);
    const top = Math.min(...shown.map((box) => box.top));
    const bottom = Math.max(...shown.map((box) => box.bottom));
    // Text covered by something else (e.g. the sticky top bar) is measured at another scroll position.
    const uncovered = shown.every((box) => {
      const hit = document.elementFromPoint(Math.min(viewportWidth - 1, Math.max(0, (box.left + box.right) / 2)), Math.min(viewportHeight - 1, Math.max(0, (box.top + box.bottom) / 2)));
      return !hit || element.contains(hit) || hit.contains(element);
    });
    const onScreen = shown.length && top >= 0 && bottom <= viewportHeight && uncovered;
    if (!total || visible < 4) {
      // Wait until the element is on screen, then skip it: it is clipped away (sr-only), not low-contrast.
      const box = element.getBoundingClientRect();
      if (box.top >= 0 && box.bottom <= viewportHeight) result[index] = { skip: true };
      continue;
    }
    if (onScreen) {
      result[index] = { boxes: shown.map((box) => intersect(box, { left: 0, top: 0, right: viewportWidth, bottom: viewportHeight })).filter((box) => area(box) >= 1) };
    } else if (uncovered && bottom - top > viewportHeight * 0.9 && top < viewportHeight && bottom > 0) {
      result[index] = { boxes: shown.map((box) => intersect(box, { left: 0, top: 0, right: viewportWidth, bottom: viewportHeight })).filter((box) => area(box) >= 1) };
    }
  }
  return result;
}

const linear = (channel) => {
  const value = channel / 255;
  return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
};
const luminance = (rgb) => 0.2126 * linear(rgb[0]) + 0.7152 * linear(rgb[1]) + 0.0722 * linear(rgb[2]);
const ratio = (a, b) => {
  const [light, dark] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (light + 0.05) / (dark + 0.05);
};
const hex = (rgb) => `#${rgb.map((channel) => Math.round(channel).toString(16).padStart(2, '0')).join('')}`;

function judge(probe, boxes, image, scale) {
  const ratios = [];
  const backgrounds = [];
  const [red, green, blue, alpha] = probe.colour;
  for (const box of boxes) {
    // Pixels whose centre lies inside the box (fractional edges must not pull in a neighbouring border line).
    const x0 = Math.max(0, Math.ceil(box.left * scale - 0.5)); const x1 = Math.min(image.width, Math.floor(box.right * scale - 0.5) + 1);
    const y0 = Math.max(0, Math.ceil(box.top * scale - 0.5)); const y1 = Math.min(image.height, Math.floor(box.bottom * scale - 0.5) + 1);
    const step = Math.max(1, Math.floor(Math.sqrt(((x1 - x0) * (y1 - y0)) / 400)));
    for (let y = y0; y < y1; y += step) {
      for (let x = x0; x < x1; x += step) {
        const offset = (y * image.width + x) * 4;
        const background = [image.data[offset], image.data[offset + 1], image.data[offset + 2]];
        const text = [red * alpha + background[0] * (1 - alpha), green * alpha + background[1] * (1 - alpha), blue * alpha + background[2] * (1 - alpha)];
        ratios.push(ratio(text, background));
        backgrounds.push(background);
      }
    }
  }
  if (!ratios.length) return null;
  const order = ratios.map((value, index) => index).sort((a, b) => ratios[a] - ratios[b]);
  const pick = order[Math.floor(order.length * 0.1)];
  return { contrast: ratios[pick], background: hex(backgrounds[pick]) };
}

/**
 * Returns readable lines for every text element under `root` whose rendered contrast is below
 * WCAG AA (4.5:1, or 3:1 for text from 24px / 18.66px bold). The 10th-percentile pixel counts,
 * so a single stray glow pixel does not fail a label but a gradient that swallows it does.
 */
export async function contrastFailures(page, root = 'body') {
  const probes = await page.evaluate(collectProbes, root);
  if (!probes.length) return [];
  const style = await page.addStyleTag({ content: HIDE_TEXT_CSS }).catch(() => null);
  const failures = [];
  try {
    const scale = await page.evaluate(() => window.devicePixelRatio || 1);
    const pending = new Set(probes.map((probe) => probe.index));
    const { scrollHeight, viewportHeight } = await page.evaluate(() => ({ scrollHeight: document.documentElement.scrollHeight, viewportHeight: window.innerHeight }));
    const stepSize = Math.max(200, Math.floor(viewportHeight * 0.8));
    for (let y = 0; pending.size && y < scrollHeight + stepSize; y += stepSize) {
      await page.evaluate((top) => { window.scrollTo(0, top); return new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))); }, y);
      const measured = await page.evaluate(measureProbes, [...pending]);
      const ready = Object.entries(measured);
      if (!ready.length) continue;
      const png = Buffer.from(await page.screenshot({ type: 'png' }));
      if (process.env.E2E_CONTRAST_DEBUG) {
        const { writeFileSync } = await import('node:fs');
        writeFileSync(`${process.env.E2E_CONTRAST_DEBUG}/contrast-${Date.now()}-y${y}.png`, png);
      }
      const image = decodePng(png);
      for (const [key, entry] of ready) {
        const index = Number(key);
        pending.delete(index);
        if (entry.skip) continue;
        const probe = probes[index];
        const verdict = judge(probe, entry.boxes, image, scale);
        if (!verdict) continue;
        const large = probe.size >= 24 || (probe.size >= 18.66 && probe.weight >= 700);
        const required = large ? 3 : 4.5;
        if (verdict.contrast + 0.02 < required) {
          const where = process.env.E2E_CONTRAST_DEBUG ? ` @y${y} ${JSON.stringify(entry.boxes.map((box) => [box.left, box.top, box.right, box.bottom].map(Math.round)))}` : '';
          failures.push(`${probe.name} "${probe.text}" ${verdict.contrast.toFixed(2)}:1 < ${required} (text ${hex(probe.colour.slice(0, 3))}${probe.colour[3] < 1 ? `/${probe.colour[3].toFixed(2)}` : ''} on ${verdict.background}, ${probe.size}px/${probe.weight})${where}`);
        }
      }
    }
  } finally {
    await page.evaluate(() => {
      document.querySelectorAll('[data-cg-probe]').forEach((element) => element.removeAttribute('data-cg-probe'));
      window.scrollTo(0, 0);
    });
    if (style) await style.evaluate((node) => node.remove());
  }
  return failures;
}
