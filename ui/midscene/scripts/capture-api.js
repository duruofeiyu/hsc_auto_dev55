#!/usr/bin/env node
/**
 * F12 抓包替身：用 Playwright 打开 HSC 页面，把 Network 面板里的请求全抓下来。
 *
 * 相比手动翻 F12 的优势：
 *   - 完整（含页面初始化阶段的全部请求，不会漏掉一闪而过的）
 *   - 可导出 JSON（方便拿去做接口测试用例 / 对比两次改动的差异）
 *   - 能分别看「已登录」和「未登录」两个视角（这是前缀 bug 的关键变量）
 *
 * 用法：
 *   node scripts/capture-api.js /assetDiscover
 *   node scripts/capture-api.js /assetDiscover --wait 10
 *   node scripts/capture-api.js /assetDiscover --out disc.json
 *   node scripts/capture-api.js /assetDiscover --no-auth        # 未登录视角
 *   node scripts/capture-api.js /assetDiscover --filter asset   # 只看 URL 含 asset 的
 *   node scripts/capture-api.js /assetDiscover --headers        # 显示请求头（token 脱敏）
 *   node scripts/capture-api.js /assetDiscover --detail 5       # 打印前 5 条的响应体
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');
const env = require('./hsc-env');

// ---------------- 参数解析 ----------------
const argv = process.argv.slice(2);
const opts = { pagePath: null, wait: 6, out: null, auth: true, filter: null, headers: false, detail: 2 };

for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === '--wait') opts.wait = Number(argv[++i]) || 6;
  else if (a === '--out') opts.out = argv[++i];
  else if (a === '--no-auth') opts.auth = false;
  else if (a === '--filter') opts.filter = argv[++i];
  else if (a === '--headers') opts.headers = true;
  else if (a === '--detail') opts.detail = Number(argv[++i]) || 0;
  else if (!a.startsWith('-')) opts.pagePath = a;
}

if (!opts.pagePath) {
  console.error('用法：node scripts/capture-api.js <页面路径> [--wait 秒] [--out 文件] [--no-auth] [--filter 关键字]');
  console.error('示例：node scripts/capture-api.js /assetDiscover --wait 10');
  process.exit(1);
}

const targetUrl = /^https?:\/\//i.test(opts.pagePath)
  ? opts.pagePath
  : `${env.WEB_BASE_URL.replace(/\/+$/, '')}/${String(opts.pagePath).replace(/^\/+/, '')}`;

// ---------------- 工具函数 ----------------
/** token 脱敏：保留前 12 后 6 */
function mask(v) {
  if (!v || v.length < 30) return v || '<空>';
  return `${v.slice(0, 12)}…${v.slice(-6)}（共 ${v.length} 位）`;
}

function shortUrl(u) {
  return u.replace(env.ORIGIN, '').replace('/hsc-system-api', '·api');
}

function formatBytes(n) {
  return n > 1024 ? `${(n / 1024).toFixed(1)}KB` : `${n}B`;
}

// ---------------- 抓包 ----------------
const records = new Map();
const consoleErrors = [];

async function main() {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    storageState: opts.auth && env.hasState() ? env.STORAGE_STATE : undefined,
    ignoreHTTPSErrors: true,
    viewport: { width: 1600, height: 900 },
  });
  const page = await ctx.newPage();

  page.on('request', (req) => {
    const url = req.url();
    if (!url.startsWith(env.ORIGIN)) return;
    const type = req.resourceType();
    if (!['xhr', 'fetch', 'document'].includes(type)) return;
    records.set(req, {
      type,
      method: req.method(),
      url: url.replace(env.ORIGIN, ''),
      rawUrl: url,
      requestHeaders: req.headers(),
      postData: req.postData() || null,
      status: null,
      durationMs: null,
      mime: null,
      size: 0,
      body: null,
      _startedAt: Date.now(),
    });
  });

  page.on('response', async (resp) => {
    const rec = records.get(resp.request());
    if (!rec) return;
    rec.status = resp.status();
    rec.durationMs = Date.now() - rec._startedAt;
    rec.mime = (resp.headers()['content-type'] || '').split(';')[0];
    // 只看文本类响应（JSON/HTML/JS），二进制跳过
    if (/json|text|xml|javascript/i.test(rec.mime)) {
      try {
        const t = await resp.text();
        rec.size = Buffer.byteLength(t, 'utf8');
        rec.body = t.slice(0, 4000);
      } catch {
        rec.body = '<响应体读取失败>';
      }
    }
  });

  page.on('console', (m) => {
    if (m.type() === 'error') consoleErrors.push(m.text());
  });
  page.on('pageerror', (e) => consoleErrors.push(String(e.message)));

  let navError = null;
  try {
    await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
  } catch (e) {
    navError = String(e.message).split('\n')[0];
  }
  await page.waitForTimeout(opts.wait * 1000);

  const finalUrl = page.url().replace(env.ORIGIN, '');
  const bodyText = await page.evaluate(() => (document.body.innerText || '').replace(/\s+/g, ' ').trim());

  await browser.close();

  // ---------------- 输出 ----------------
  const all = [...records.values()];
  // --filter 只筛接口，不影响 Document（否则会误报「页面本身 0 条」）
  const docs = all.filter((r) => r.type === 'document');
  let apis = all.filter((r) => r.type !== 'document');
  if (opts.filter) apis = apis.filter((r) => r.url.includes(opts.filter));
  const pendingCount = apis.filter((r) => r.status == null).length;

  console.log(`\n=========== 抓包结果 · ${opts.pagePath} ===========`);
  console.log(`环境      : ${env.ENV}  ${env.ORIGIN}`);
  console.log(`登录态    : ${opts.auth ? (env.hasState() ? path.basename(env.STORAGE_STATE) + '（已登录）' : '⚠️ 无 state 文件 → 实际是未登录视角') : '未登录视角（--no-auth）'}`);
  console.log(`最终 URL  : ${finalUrl}`);
  if (navError) console.log(`导航警告  : ${navError}`);

  console.log(`\n── Document（页面本身）${docs.length} 条 ──`);
  docs.forEach((r) => console.log(`   ${r.method.padEnd(5)} ${r.status || '-'}  ${r.url}`));

  console.log(`\n── 接口请求（xhr/fetch）共 ${apis.length} 条 ──`);
  if (!apis.length) console.log('   （无）');
  apis.forEach((r, i) => {
    const n = String(i + 1).padStart(2);
    const statusStr = r.status == null ? '…' : String(r.status);
    const ms = r.durationMs != null ? `${r.durationMs}ms` : '-';
    const sz = r.size ? formatBytes(r.size) : '';
    console.log(`   ${n}  ${r.method.padEnd(5)} ${statusStr.padEnd(4)} ${ms.padEnd(7)} ${sz.padEnd(7)} ${shortUrl(r.url)}`);
  });
  if (pendingCount) {
    console.log(`   （其中 ${pendingCount} 条在抓包结束前仍未返回，标记为 … —— 可加大 --wait 再抓一次）`);
  }

  if (opts.headers) {
    console.log('\n── 请求头（token 脱敏；取第一条接口请求）──');
    const sample = apis.find((r) => r.requestHeaders.authorization) || apis[0];
    if (sample) {
      Object.entries(sample.requestHeaders)
        .filter(([k]) => ![':authority', ':method', ':path', ':scheme'].includes(k))
        .forEach(([k, v]) => {
          const val = /^(authorization|x-access-token|cookie)$/i.test(k) ? mask(v) : v;
          console.log(`   ${k}: ${val}`);
        });
    }
  }

  if (opts.detail > 0 && apis.length) {
    console.log(`\n── 响应详情（前 ${Math.min(opts.detail, apis.length)} 条）──`);
    apis.slice(0, opts.detail).forEach((r) => {
      console.log(`\n   [${r.method} ${shortUrl(r.url)}]  ${r.status} ${r.durationMs}ms`);
      if (r.postData) console.log(`   请求体: ${r.postData.slice(0, 400)}`);
      console.log(`   响应体: ${r.body ? r.body.slice(0, 600) : '<无>'}`);
    });
  }

  // 页面健康判定
  const isErrorPage = bodyText.length < 400 && /500|501|502|服务器出错|非常抱歉/.test(bodyText);
  const isLoginPage = /账号登录|忘记密码|验证码/.test(bodyText) || /\/login$/.test(finalUrl);
  const isBlank = !navError && bodyText.length < 50 && !isErrorPage && !isLoginPage;
  const host = env.ORIGIN.replace(/^https?:\/\//, '');
  console.log('\n── 页面状态 ──');
  if (navError) {
    console.log(`   ❌ 页面根本打不开：${navError}`);
    console.log(`      → 先确认网络/VPN 是否连通：curl -sk https://${host}/  或  ping ${host.split(':')[0]}`);
  } else if (isErrorPage) {
    console.log(`   ❌ 停在错误页（正文 ${bodyText.length} 字）—— 这不是后端挂了，先核对 URL 前缀`);
  } else if (isLoginPage) {
    console.log(`   🔐 停在登录页（正文 ${bodyText.length} 字）—— 未登录或被踢回`);
  } else if (isBlank) {
    console.log(`   ⚠️ 页面几乎空白（正文 ${bodyText.length} 字）—— 加载失败或前端渲染异常`);
  } else {
    console.log(`   ✅ 正常业务页（正文 ${bodyText.length} 字）`);
  }

  if (consoleErrors.length) {
    console.log(`   ⚠️ 控制台报错 ${consoleErrors.length} 条：`);
    consoleErrors.slice(0, 3).forEach((e) => console.log(`      ${e.slice(0, 140)}`));
  } else {
    console.log('   ✓ 控制台无报错');
  }

  // ---------------- 导出 ----------------
  if (opts.out) {
    const outDir = path.join(env.ROOT, 'midscene_run', 'capture');
    fs.mkdirSync(outDir, { recursive: true });
    const outFile = path.isAbsolute(opts.out) ? opts.out : path.join(outDir, opts.out);
    const payload = {
      capturedAt: new Date().toISOString(),
      env: env.ENV,
      target: opts.pagePath,
      finalUrl,
      loggedIn: opts.auth && env.hasState(),
      pageState: navError ? 'unreachable' : isErrorPage ? 'error' : isLoginPage ? 'login' : isBlank ? 'blank' : 'ok',
      navError: navError || null,
      documentCount: docs.length,
      apiCount: apis.length,
      apis: apis.map(({ _startedAt, requestHeaders, ...rest }) => ({
        ...rest,
        requestHeaders: Object.fromEntries(
          Object.entries(requestHeaders).map(([k, v]) => [
            k,
            /^(authorization|x-access-token|cookie)$/i.test(k) ? `<已脱敏 长度${String(v).length}>` : v,
          ])
        ),
      })),
    };
    fs.writeFileSync(outFile, JSON.stringify(payload, null, 2), 'utf8');
    console.log(`\n[导出] ${outFile}  （token 已脱敏；该目录已在 .gitignore 中）`);
  }

  console.log('');
  // 退出码：0 正常 / 2 环境不可用（打不开或错误页）—— 便于脚本化判断
  process.exit(navError || isErrorPage ? 2 : 0);
}

main().catch((e) => {
  console.error('[x] 抓包失败：', e.message);
  process.exit(1);
});
