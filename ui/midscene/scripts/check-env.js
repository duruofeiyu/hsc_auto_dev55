// 环境体检：一条命令判定「用例跑红」到底是环境问题还是用例问题。
//
// 背景（2026-09-10 实测踩到）：HSC 55 前端会整体崩成「500 服务器出错」错误页，
// 此时 3 条用例全红、看着像断言写错 —— 但后端接口全是 200、控制台零报错，
// 怎么查都"正常"。没有这个体检，很容易去反复"修"一个根本没坏的用例。
//
// 用法：
//   node scripts/check-env.js                        # 查三个关键路由
//   node scripts/check-env.js /assetsVuln /system/user  # 查指定路由
// 退出码：0=环境正常  2=环境故障  3=登录态失效
const env = require('./hsc-env');
const fs = require('fs');
const { chromium } = require('playwright');

const TARGETS = process.argv.slice(2).filter((a) => !a.startsWith('-'));
const ROUTES = TARGETS.length ? TARGETS : ['/', '/assetDiscover', '/assetsOverview'];

const ERR_RE = /500|501|502|服务器出错|非常抱歉/;

/** 页面性质判定：ok / error（前端错误页）/ login（被踹回登录页） */
function judge(text, url) {
  const t = String(text || '').replace(/\s+/g, ' ').trim();
  if (/\/login/i.test(url)) return 'login';
  if (t.length < 400 && ERR_RE.test(t)) return 'error';
  return 'ok';
}

(async () => {
  console.log(`[env] 环境=${env.ENV}  UI=${env.WEB_BASE_URL}`);
  if (!env.hasState()) {
    console.error(`[x] 登录态文件不存在：${env.STORAGE_STATE}`);
    console.error('    先跑：npm run auth');
    process.exit(3);
  }

  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    storageState: env.STORAGE_STATE,
    ignoreHTTPSErrors: true, // HSC 是自签且已过期的证书
  });

  const rows = [];
  let anyErrorPage = false;
  let anyLogin = false;

  for (const route of ROUTES) {
    const url = /^https?:\/\//i.test(route)
      ? route
      : `${env.WEB_BASE_URL.replace(/\/+$/, '')}/${String(route).replace(/^\/+/, '')}`;

    const httpBad = [];
    const jsErrs = [];
    const bizBad = [];

    const page = await ctx.newPage();
    page.on('response', async (r) => {
      if (r.status() >= 400) httpBad.push(`[${r.status()}] ${r.url().slice(0, 110)}`);
      if (!/json/i.test(r.headers()['content-type'] || '')) return;
      try {
        const j = await r.json();
        if (j && (j.success === false || ![0, 200, 20000].includes(Number(j.code)))) {
          bizBad.push(`code=${j.code} success=${j.success} msg=${String(j.message || '').slice(0, 70)}`);
        }
      } catch (_) {}
    });
    page.on('console', (m) => {
      if (m.type() === 'error') jsErrs.push(m.text().slice(0, 200));
    });
    page.on('pageerror', (e) => jsErrs.push('[pageerror] ' + String(e && e.message).slice(0, 200)));

    let text = '';
    let finalUrl = url;
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 40000 });
      await page.waitForTimeout(3500); // 给前端路由 + 图表渲染留时间
      finalUrl = page.url();
      text = await page.evaluate(() => document.body.innerText || '');
    } catch (e) {
      rows.push({ route, kind: 'navfail', detail: String(e.message).split('\n')[0] });
      await page.close();
      continue;
    }
    await page.close();

    const kind = judge(text, finalUrl);
    if (kind === 'error') anyErrorPage = true;
    if (kind === 'login') anyLogin = true;

    rows.push({
      route,
      kind,
      detail: String(text).replace(/\s+/g, ' ').trim().slice(0, 90),
      httpBad: [...new Set(httpBad)],
      jsErrs: [...new Set(jsErrs)],
      bizBad: [...new Set(bizBad)],
    });
  }

  await browser.close();

  // ---------- 报告 ----------
  const label = { ok: '✅ 正常页', error: '❌ 前端错误页', login: '🔒 登录页', navfail: '⚠️ 打不开' };
  console.log('\n=== 逐页结果 ===');
  for (const r of rows) {
    console.log(`${label[r.kind]}  ${r.route}   ${r.detail}`);
    if (r.httpBad && r.httpBad.length) console.log(`     HTTP>=400: ${r.httpBad.slice(0, 3).join(' | ')}`);
    if (r.jsErrs && r.jsErrs.length) console.log(`     JS 错误: ${r.jsErrs.slice(0, 2).join(' | ')}`);
    if (r.bizBad && r.bizBad.length) console.log(`     业务失败响应: ${r.bizBad.slice(0, 3).join(' | ')}`);
  }

  console.log('\n=== 分层取证 ===');
  const sum = (k) => rows.reduce((n, r) => n + ((r[k] && r[k].length) || 0), 0);
  const nHttp = sum('httpBad');
  const nJs = sum('jsErrs');
  const nBiz = sum('bizBad');
  const dirty = nHttp + nJs + nBiz;
  console.log(`HTTP>=400 请求: ${nHttp} 条  |  JS 报错: ${nJs} 条  |  业务失败响应: ${nBiz} 条`);
  console.log(
    dirty === 0
      ? '三层全部干净 —— 若同时出现错误页，说明是【前端渲染层】故障（后端接口其实是正常的）。'
      : '三层有命中项 —— 按上面的清单逐个查，这些通常就是根因。'
  );

  console.log('\n=== 结论 ===');
  if (anyLogin) {
    console.log('🔒 有页面被踹回登录页 —— 登录态已失效。先跑：npm run auth');
    console.log('   （注意：这种情况下列用工全红是【登录态问题】，不是断言问题。）');
    process.exit(3);
  }
  if (anyErrorPage) {
    console.log('❌ 页面停在「服务器出错」错误页。两种可能，**先查第一种**：');
    console.log('   ① URL 写错了（最常见）—— HSC 前端部署在【根路径】，地址里不要加 /hsc-system-web。');
    console.log('      带前缀时 Vue Router 匹配不到路由 → 渲染这个错误组件；症状是"手动浏览器正常、自动化全红"。');
    console.log('      正确：' + env.ORIGIN + '/assetDiscover');
    console.log('      另：/#/xxx 的 hash 路由已废弃，会被踢回登录页。');
    console.log('   ② 环境真的坏了 —— 若上面 HTTP / JS / 业务层都干净，就属【前端渲染层】故障。');
    console.log('   ⚠️ 无论哪种，用例跑红都【不是断言的问题】，别去改用例。');
    process.exit(2);
  }
  const navFail = rows.filter((r) => r.kind === 'navfail').length;
  if (navFail) {
    console.log(`⚠️ ${navFail} 个路由打不开（其余正常）—— 可能是路由写错或该页被下线，核对菜单树。`);
    process.exit(1);
  }
  console.log('✅ 环境正常，页面可测。用例若仍跑红，那就是用例本身的问题。');
  process.exit(0);
})();
