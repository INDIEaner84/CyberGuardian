// Starts `server.py` on a free loopback port with a throw-away state file.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';

function freePort() {
  return new Promise((resolve, reject) => {
    const probe = net.createServer();
    probe.unref();
    probe.on('error', reject);
    probe.listen(0, '127.0.0.1', () => {
      const { port } = probe.address();
      probe.close(() => resolve(port));
    });
  });
}

async function waitForHealth(url, child, logs, deadline) {
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error(`server.py exited early (code ${child.exitCode}):\n${logs.join('')}`);
    try {
      const response = await fetch(`${url}/api/health`);
      if (response.ok) return;
    } catch (_) { /* not listening yet */ }
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  throw new Error(`server.py did not become healthy in time:\n${logs.join('')}`);
}

/**
 * @param {object} options
 * @param {string} options.root repository root (where server.py lives)
 * @param {string} [options.python] interpreter, defaults to $PYTHON or python3
 */
export async function startServer({ root, python = process.env.PYTHON || 'python3' }) {
  const port = await freePort();
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), 'cyberguardian-e2e-'));
  const stateFile = path.join(stateDir, 'control_plane.json');
  const logs = [];
  const child = spawn(python, ['server.py', '--host', '127.0.0.1', '--port', String(port), '--data-file', stateFile], {
    cwd: root,
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  child.stdout.on('data', (chunk) => logs.push(chunk.toString()));
  child.stderr.on('data', (chunk) => logs.push(chunk.toString()));
  const url = `http://127.0.0.1:${port}`;
  try {
    await waitForHealth(url, child, logs, Date.now() + 20_000);
  } catch (error) {
    child.kill('SIGKILL');
    throw error;
  }
  return {
    url,
    stateFile,
    logs: () => logs.join(''),
    async stop() {
      if (child.exitCode === null) {
        const exited = new Promise((resolve) => child.once('exit', resolve));
        child.kill('SIGTERM');
        await Promise.race([exited, new Promise((resolve) => setTimeout(resolve, 3000))]);
        if (child.exitCode === null) child.kill('SIGKILL');
      }
      fs.rmSync(stateDir, { recursive: true, force: true });
    },
  };
}
