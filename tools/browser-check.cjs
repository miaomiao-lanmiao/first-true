const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { chromium } = require(process.env.ECHO_PLAYWRIGHT_PATH || 'playwright');
const root = path.resolve(__dirname, '..');
const storage = fs.mkdtempSync(path.join(os.tmpdir(), 'echo-browser-'));
const python = process.env.ECHO_TEST_PYTHON || path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const port = 18139;
const url = `http://127.0.0.1:${port}`;
const server = spawn(python, ['-m', 'uvicorn', 'echo.web:app', '--host', '127.0.0.1', '--port', String(port)], {
  cwd: root, env: { ...process.env, ECHO_CONFIG_DIR: storage }, windowsHide: true,
  stdio: ['ignore', 'ignore', 'pipe'],
});
let serverErrors = '';
server.stderr.on('data', data => { serverErrors += data; });

async function main() {
  let browser;
  try {
    for (let attempt = 0; attempt < 60; attempt++) {
      try { if ((await fetch(url)).ok) break; } catch {}
      if (attempt === 59) throw new Error(`Local test server failed to start. ${serverErrors}`);
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    browser = await chromium.launch({ channel: 'msedge', headless: true, chromiumSandbox: true });
    const context = await browser.newContext({ acceptDownloads: false, permissions: [], serviceWorkers: 'block' });
    const external = [];
    const errors = [];
    await context.route('**/*', route => {
      const target = new URL(route.request().url());
      if (target.origin === url) return route.continue();
      external.push(target.hostname); return route.abort();
    });
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(url);
    await page.waitForFunction(() => document.querySelector('#modelSelect').options.length > 0);
    assert.notEqual(await page.locator('#modelSelect').inputValue(), 'undefined');
    const markdown = await page.evaluate(() => {
      const element = document.createElement('div');
      element.innerHTML = renderMarkdown('<img src=x onerror="window.__unexpected=1"><script>window.__unexpected=1</script> **safe**');
      return { dangerous: element.querySelectorAll('script,[onerror]').length, text: element.textContent, bold: !!element.querySelector('strong') };
    });
    assert.equal(markdown.dangerous, 0);
    assert.ok(markdown.bold);
    const stored = await page.evaluate(async () => {
      await newSession();
      await persistMessages([{ role: 'user', content: 'synthetic local test' }]);
      const response = await fetch(`/api/sessions/${state.activeSession}`);
      return response.json();
    });
    assert.equal(stored.messages[0].content, 'synthetic local test');
    await page.reload();
    await page.locator('.session-title').first().click();
    await page.waitForFunction(() => document.querySelector('#messages').textContent.includes('synthetic local test'), undefined, { timeout: 3000 });
    assert.equal(await page.evaluate(() => currentHistory().length), 1);
    fs.writeFileSync(path.join(storage, 'sessions', 'legacy notes.json'), JSON.stringify({
      title: 'Legacy notes fixture', messages: [{ role: 'user', content: 'synthetic legacy browser message' }],
    }));
    await page.reload();
    await page.locator('.session-title').filter({ hasText: 'Legacy notes fixture' }).click();
    await page.waitForFunction(() => document.querySelector('#messages').textContent.includes('synthetic legacy browser message'), undefined, { timeout: 3000 });
    assert.deepEqual(errors, []);
    assert.deepEqual(external, []);
    fs.mkdirSync(path.join(root, 'reports'), { recursive: true });
    await page.screenshot({ path: path.join(root, 'reports', 'echo-browser-check.png') });
    console.log('Browser checks passed: local assets, safe Markdown, session persistence after reload, legacy sessions, no page errors or external asset requests.');
  } finally {
    if (browser) await browser.close();
    server.kill();
    await new Promise(resolve => server.exitCode !== null ? resolve() : server.once('exit', resolve));
    fs.rmSync(storage, { recursive: true, force: true });
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
