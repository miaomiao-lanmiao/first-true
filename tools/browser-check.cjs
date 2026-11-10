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
    const requests = [];
    let reply = 'data: {"token":"synthetic streamed reply"}\n\ndata: {"done":true}\n\n';
    await page.route(`${url}/api/chat`, async route => {
      requests.push(route.request().postDataJSON());
      await route.fulfill({ status: 200, contentType: 'text/event-stream', body: reply });
    });
    let allowSave;
    const saveReleased = new Promise(resolve => { allowSave = resolve; });
    await page.route(`${url}/api/sessions/*/messages`, async route => {
      await saveReleased;
      await route.continue();
    }, { times: 1 });
    const firstSave = page.waitForRequest(request => request.method() === 'PUT' && request.url().endsWith('/messages'));
    const firstSend = page.evaluate(async () => { document.querySelector('#input').value = 'first synthetic turn'; await send(); });
    try {
      await firstSave;
      await page.evaluate(async () => { document.querySelector('#input').value = 'second synthetic turn'; await send(); });
      assert.equal(requests.length, 1, 'A new request must wait for the previous reply to be saved.');
    } finally {
      allowSave();
      await firstSend;
    }
    assert.ok((await page.locator('#messages').innerText()).includes('synthetic streamed reply'));
    assert.equal(await page.evaluate(() => currentHistory().at(-1).content), 'synthetic streamed reply');
    reply = 'data: {"token":"second synthetic reply"}\n\ndata: {"done":true}\n\n';
    await page.evaluate(async () => { document.querySelector('#input').value = 'second synthetic turn'; await send(); });
    const messages = await page.locator('#messages').innerText();
    assert.ok(messages.includes('synthetic streamed reply'));
    assert.ok(messages.includes('second synthetic reply'));
    assert.equal(requests[1].messages.at(-2).content, 'synthetic streamed reply');
    const previousAssistants = await page.evaluate(() => currentHistory().filter(message => message.role === 'assistant').length);
    reply = 'data: {"error":"Provider request failed. Check configuration and connectivity."}\n\n';
    await page.evaluate(async () => { document.querySelector('#input').value = 'failed synthetic turn'; await send(); });
    assert.ok((await page.locator('#messages').innerText()).includes('Provider request failed'));
    assert.equal(await page.evaluate(() => currentHistory().filter(message => message.role === 'assistant').length), previousAssistants);
    const savedAfterFailure = await page.evaluate(async () => (await fetch(`/api/sessions/${encodeURIComponent(state.activeSession)}`)).json());
    assert.equal(savedAfterFailure.messages.filter(message => message.role === 'assistant').length, previousAssistants);
    reply = 'data: {"token":"synthetic unfinished answer"}\n\n';
    await page.evaluate(async () => { document.querySelector('#input').value = 'interrupted synthetic turn'; await send(); });
    assert.ok((await page.locator('#messages').innerText()).includes('响应中断'));
    assert.equal(await page.evaluate(() => currentHistory().filter(message => message.role === 'assistant').length), previousAssistants);
    assert.deepEqual(errors, []);
    assert.deepEqual(external, []);
    fs.mkdirSync(path.join(root, 'reports'), { recursive: true });
    await page.screenshot({ path: path.join(root, 'reports', 'echo-browser-check.png') });
    console.log('Browser checks passed: local assets, session reload, mocked streamed replies across turns, failed replies excluded from saved history, no external requests.');
  } finally {
    if (browser) await browser.close();
    server.kill();
    await new Promise(resolve => server.exitCode !== null ? resolve() : server.once('exit', resolve));
    fs.rmSync(storage, { recursive: true, force: true });
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
