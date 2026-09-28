// Tiny sequential test runner: no framework, readable output, per-test timeout.
import { inspect } from 'node:util';

const registry = [];

/** Registers a test. `fn` receives a context object prepared by the runner. */
export function test(name, fn, { timeout = 45_000 } = {}) {
  registry.push({ name, fn, timeout });
}

function withTimeout(promise, ms, name) {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(`timed out after ${ms} ms: ${name}`)), ms);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

export function describeError(error) {
  if (!error) return 'unknown error';
  if (error.name === 'AssertionError' && error.generatedMessage === false) return error.message;
  if (error.name === 'AssertionError') {
    const lines = [error.message];
    if ('actual' in error && typeof error.actual === 'object') lines.push(`actual: ${inspect(error.actual, { depth: 4, breakLength: 110 })}`);
    return lines.join('\n');
  }
  return error.stack || String(error);
}

/**
 * Runs all registered tests in order.
 * @param {object} options
 * @param {RegExp|null} options.grep only run tests whose name matches
 * @param {(t: {name: string}) => Promise<object>} options.context builds the per-test context
 * @param {(t: {name: string}, context: object, error: Error) => Promise<void>} options.onFailure
 */
export async function run({ grep = null, context, onFailure }) {
  const selected = registry.filter((entry) => !grep || grep.test(entry.name));
  const results = [];
  const started = Date.now();
  console.log(`\nCyberGuardian browser checks — ${selected.length} of ${registry.length} tests\n`);
  for (const entry of selected) {
    const begin = Date.now();
    const ctx = await context(entry);
    let error = null;
    try {
      await withTimeout(Promise.resolve().then(() => entry.fn(ctx)), entry.timeout, entry.name);
    } catch (caught) {
      error = caught;
      try { await onFailure?.(entry, ctx, caught); } catch (hookError) { console.error(`  (failure hook: ${hookError.message})`); }
    }
    try { await ctx.dispose?.(); } catch (disposeError) { error ??= disposeError; }
    const ms = Date.now() - begin;
    results.push({ name: entry.name, ok: !error, ms, error });
    if (error) {
      console.log(`  ✗ ${entry.name} (${ms} ms)`);
      console.log(describeError(error).split('\n').map((line) => `      ${line}`).join('\n'));
    } else {
      console.log(`  ✓ ${entry.name} (${ms} ms)`);
    }
  }
  const failed = results.filter((result) => !result.ok);
  const seconds = ((Date.now() - started) / 1000).toFixed(1);
  console.log(`\n${results.length - failed.length} passed, ${failed.length} failed (${seconds} s)`);
  if (failed.length) {
    console.log('\nFailed:');
    failed.forEach((result) => console.log(`  - ${result.name}`));
  }
  return { results, failed };
}
