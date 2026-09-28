// Chrome discovery, launch and an instrumented page factory.
import fs from 'node:fs';
import puppeteer from 'puppeteer-core';

const CHROME_CANDIDATES = [
  process.env.CHROME_PATH,
  process.env.CHROME_BIN, // set on GitHub-hosted Ubuntu runners
  process.env.PUPPETEER_EXECUTABLE_PATH,
  '/usr/bin/google-chrome',
  '/usr/bin/google-chrome-stable',
  '/usr/bin/chromium',
  '/usr/bin/chromium-browser',
  '/snap/bin/chromium',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
];

export function findChrome() {
  const found = CHROME_CANDIDATES.find((candidate) => candidate && fs.existsSync(candidate));
  if (!found) {
    throw new Error('No Chrome/Chromium found. Set CHROME_PATH to a Chrome, Chromium or chrome-headless-shell binary.');
  }
  return found;
}

export async function launchBrowser() {
  const executablePath = findChrome();
  const extraArgs = (process.env.CHROME_ARGS || '').split(/\s+/).filter(Boolean);
  const browser = await puppeteer.launch({
    executablePath,
    // CHROME_HEADLESS=shell for chrome-headless-shell style binaries, otherwise the new headless mode.
    headless: process.env.CHROME_HEADLESS === 'shell' ? 'shell' : true,
    args: [
      // The browser only ever visits the throw-away loopback server started by the runner.
      '--no-sandbox',
      '--disable-dev-shm-usage',
      '--hide-scrollbars',
      '--font-render-hinting=none',
      '--lang=de-DE',
      ...extraArgs,
    ],
  });
  return { browser, executablePath };
}

const IGNORED_FAILURES = [/net::ERR_ABORTED/];

/**
 * Creates `open(options)` for one test. Every page gets:
 *  - console error, page error, failed request and HTTP >= 400 tracking (`issues`)
 *  - CSP violation capture (`cspViolations()`)
 *  - optional one-time localStorage seeding (survives reloads untouched)
 */
export function createPageFactory(browser, baseUrl) {
  const contexts = new Set();
  const pages = [];

  async function open({
    path = '/',
    theme,
    storage = {},
    viewport = { width: 1440, height: 1000 },
    reducedMotion = true,
    context = null,
    waitUntil = 'networkidle0',
    ignore = [],
  } = {}) {
    const browserContext = context || await browser.createBrowserContext();
    if (!context) contexts.add(browserContext);
    const page = await browserContext.newPage();
    const issues = [];
    const ignored = [...IGNORED_FAILURES, ...ignore];
    const record = (message) => { if (!ignored.some((pattern) => pattern.test(message))) issues.push(message); };
    page.on('console', (message) => { if (message.type() === 'error') record(`console.error: ${message.text()}`); });
    page.on('pageerror', (error) => record(`pageerror: ${error.message}`));
    page.on('requestfailed', (request) => record(`requestfailed: ${request.url()} (${request.failure()?.errorText})`));
    page.on('response', (response) => { if (response.status() >= 400) record(`HTTP ${response.status()}: ${response.url()}`); });

    await page.setViewport(viewport);
    await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: reducedMotion ? 'reduce' : 'no-preference' }]);
    await page.evaluateOnNewDocument(() => {
      window.__cspViolations = [];
      document.addEventListener('securitypolicyviolation', (event) => {
        window.__cspViolations.push(`${event.violatedDirective} blocked ${event.blockedURI || 'inline'}`);
      });
    });

    const seed = { ...storage };
    if (theme !== undefined) seed['cyberguardian.theme'] = theme === 'nightwatch' ? null : theme;
    if (Object.keys(seed).length) {
      await page.evaluateOnNewDocument((entries) => {
        // Seed once per tab so reload tests observe what the app itself persisted.
        if (window.top !== window || sessionStorage.getItem('__e2eSeeded')) return;
        for (const [key, value] of Object.entries(entries)) {
          if (value === null) localStorage.removeItem(key); else localStorage.setItem(key, value);
        }
        sessionStorage.setItem('__e2eSeeded', '1');
      }, seed);
    }

    const entry = { page, issues, label: path };
    pages.push(entry);
    if (path !== null) {
      await page.goto(new URL(path, baseUrl).href, { waitUntil });
      await page.evaluate(() => document.fonts.ready.then(() => true));
    }

    return {
      page,
      issues,
      base: baseUrl,
      context: browserContext,
      cspViolations: () => page.evaluate(() => window.__cspViolations.slice()),
    };
  }

  async function dispose() {
    for (const { page } of pages) { if (!page.isClosed()) await page.close().catch(() => {}); }
    for (const browserContext of contexts) await browserContext.close().catch(() => {});
  }

  return { open, dispose, pages };
}
