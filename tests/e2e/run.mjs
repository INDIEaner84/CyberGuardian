#!/usr/bin/env node
// CyberGuardian browser checks.
//
//   cd tests/e2e && npm ci && npm test                 # all checks
//   npm test -- --grep "themes|a11y: agentur"          # subset (regular expression)
//
// Environment:
//   CHROME_PATH      Chrome/Chromium binary (falls back to CHROME_BIN and common install paths)
//   CHROME_HEADLESS  "shell" for chrome-headless-shell style binaries
//   CHROME_ARGS      extra browser flags, space separated
//   E2E_BASE_URL     test an already running cockpit instead of starting server.py
//   E2E_ARTIFACTS    directory for failure screenshots (default: tests/e2e/artifacts, emptied per run)
//   E2E_CONTRAST_DEBUG  directory: keep every contrast screenshot and print box coordinates
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describeError, run } from './lib/harness.mjs';
import { createPageFactory, launchBrowser } from './lib/browser.mjs';
import { startServer } from './lib/server.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..', '..');
const args = process.argv.slice(2);
const grepIndex = args.indexOf('--grep');
const grep = grepIndex >= 0 && args[grepIndex + 1] ? new RegExp(args[grepIndex + 1], 'i') : null;
const artifacts = path.resolve(process.env.E2E_ARTIFACTS || path.join(here, 'artifacts'));

fs.rmSync(artifacts, { recursive: true, force: true });

for (const spec of ['themes', 'cockpit', 'responsive', 'a11y']) {
  await import(`./specs/${spec}.mjs`);
}

const server = process.env.E2E_BASE_URL ? null : await startServer({ root });
const base = (process.env.E2E_BASE_URL || server.url).replace(/\/$/, '');
let browser;
let exitCode = 1;
try {
  const launched = await launchBrowser();
  browser = launched.browser;
  console.log(`Cockpit: ${base}\nBrowser: ${await browser.version()} (${launched.executablePath})`);
  const { failed } = await run({
    grep,
    context: async () => {
      const factory = createPageFactory(browser, base);
      return { open: factory.open, base, pages: factory.pages, dispose: factory.dispose };
    },
    onFailure: async (entry, ctx) => {
      fs.mkdirSync(artifacts, { recursive: true });
      const slug = entry.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 90);
      let index = 0;
      for (const { page } of ctx.pages) {
        if (page.isClosed()) continue;
        index += 1;
        const file = path.join(artifacts, `${slug}-${index}.png`);
        await page.screenshot({ path: file, fullPage: false }).catch(() => {});
      }
    },
  });
  exitCode = failed.length ? 1 : 0;
  if (failed.length && process.env.GITHUB_ACTIONS === 'true') reportToGitHub(failed);
  if (failed.length && server) {
    const tail = server.logs().split('\n').slice(-25).join('\n');
    if (tail.trim()) console.log(`\nserver.py log (tail):\n${tail}`);
  }
} catch (error) {
  console.error(error);
} finally {
  await browser?.close().catch(() => {});
  await server?.stop();
}
process.exit(exitCode);

/** Failures as check annotations (first 10 show on the run page) and in the job summary. */
function reportToGitHub(failed) {
  const data = (text) => text.replace(/%/g, '%25').replace(/\r/g, '%0D').replace(/\n/g, '%0A');
  const property = (text) => data(text).replace(/:/g, '%3A').replace(/,/g, '%2C');
  for (const result of failed) {
    console.log(`::error title=${property(result.name)}::${data(describeError(result.error).slice(0, 4000))}`);
  }
  if (process.env.GITHUB_STEP_SUMMARY) {
    const rows = failed.map((result) => `### ✗ ${result.name}\n\n\`\`\`\n${describeError(result.error).slice(0, 6000)}\n\`\`\`\n`);
    fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, `## Browser checks: ${failed.length} failed\n\n${rows.join('\n')}`);
  }
}
