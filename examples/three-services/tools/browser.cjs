const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const { mkdirSync, writeFileSync } = require('node:fs');
const path = require('node:path');
const { createInterface } = require('node:readline');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

async function main() {
  const projects = path.resolve(process.argv[2]);
  const evidence = path.resolve(process.argv[3]);
  const child = spawn(process.env.DEMO_PYTHON || 'python3', [
    '-B', path.join(__dirname, 'serve.py'), projects,
    '--web-port', '0', '--campaign-port', '0', '--capacity-port', '0',
  ], { stdio: ['ignore', 'pipe', 'pipe'] });
  const lines = createInterface({ input: child.stdout });
  let log = '';
  child.stderr.on('data', data => { log = (log + data).slice(-6000); });
  let browser;
  try {
    const urls = await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Startup timeout ' + log)), 5000);
      child.once('error', error => { clearTimeout(timer); reject(error); });
      child.once('exit', code => { clearTimeout(timer); reject(new Error('Service exit ' + code + log)); });
      lines.once('line', line => { clearTimeout(timer); resolve(JSON.parse(line)); });
    });
    browser = await chromium.launch({ headless: true, executablePath: process.env.CHROME_PATH });
    const page = await browser.newPage({ viewport: { width: 1200, height: 800 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const endpoint = '/ops/api/v1/campaigns';
    async function query(action, ids, total, position) {
      const [response] = await Promise.all([
        page.waitForResponse(response => new URL(response.url()).pathname === endpoint), action(),
      ]);
      assert.equal(response.status(), 200);
      const body = await response.json();
      assert.deepEqual(body.items.map(item => item.id), ids);
      assert.equal(body.total, total);
      await page.waitForFunction(({ ids, total, position }) => {
        const rendered = [...document.querySelectorAll('.activity-id')].map(el => el.textContent);
        return JSON.stringify(rendered) === JSON.stringify(ids)
          && document.querySelector('#summary').textContent === '共 ' + total + ' 条'
          && document.querySelector('#position').textContent === position;
      }, { ids, total, position });
      return { body, query: Object.fromEntries(new URL(response.url()).searchParams) };
    }
    const search = page.getByRole('button', { name: '查询', exact: true });
    const next = page.getByRole('button', { name: '下一页', exact: true });
    const keyword = page.getByLabel('关键词');
    const status = page.getByLabel('活动状态');
    const bookable = page.getByLabel('仅看可报名');

    const initial = await query(() => page.goto(urls.web), ['A101', 'A102', 'A103', 'A104'], 4, '第 1 / 1 页');
    assert.deepEqual(await page.locator('.remaining').allTextContents(), ['10', '3', '0', '0']);
    await query(() => page.getByLabel('每页条数').selectOption('1'), ['A101'], 4, '第 1 / 4 页');
    await query(() => next.click(), ['A102'], 4, '第 2 / 4 页');
    await bookable.check();
    const pending = await query(() => next.click(), ['A103'], 4, '第 3 / 4 页');
    assert.equal(pending.query.bookable, undefined);
    const filtered = await query(() => search.click(), ['A102'], 1, '第 1 / 1 页');
    assert.equal(filtered.query.bookable, 'true');
    await query(() => page.getByLabel('每页条数').selectOption('20'), ['A102'], 1, '第 1 / 1 页');
    await keyword.fill('夏季');
    await query(() => search.click(), [], 0, '第 1 / 1 页');
    await page.getByText('暂无匹配的活动').waitFor({ state: 'visible' });
    await keyword.fill('春季');
    await status.selectOption('ACTIVE');
    const combined = await query(() => search.click(), ['A102'], 1, '第 1 / 1 页');
    mkdirSync(evidence, { recursive: true });
    await page.screenshot({ path: path.join(evidence, 'feature-desktop.png'), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), true);
    await page.screenshot({ path: path.join(evidence, 'feature-mobile.png'), fullPage: true });
    await page.setViewportSize({ width: 1200, height: 800 });
    await keyword.fill('');
    await status.selectOption('');
    await bookable.uncheck();
    const restored = await query(() => search.click(), ['A101', 'A102', 'A103', 'A104'], 4, '第 1 / 1 页');
    assert.deepEqual(errors, []);
    const result = {
      id: 'AC08', status: 'PASS',
      actual: { browser: browser.version(), initial, pending, filtered, combined, restored, errors },
    };
    writeFileSync(path.join(evidence, 'result.json'), JSON.stringify(result, null, 2) + '\n');
    console.log('PASS AC08 actual browser -> portal-web -> campaign-api -> capacity-api');
  } finally {
    if (browser) await browser.close();
    lines.close();
    child.kill();
    if (child.exitCode === null) await new Promise(resolve => child.once('exit', resolve));
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
