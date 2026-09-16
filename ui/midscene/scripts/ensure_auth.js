#!/usr/bin/env node
/**
 * 跑用例前的「登录态体检 + 自动刷新」。
 *
 * ---- 为什么需要它 ----
 * HSC 的 token 会过期，而 storage_state 文件是死是活从文件本身看不出来。
 * 之前的表现：用例一跑，浏览器打开就停在 /login，midscene 抛一句
 * 「当前页面是登录界面，不是 XX 页面」——完全看不出是登录态的问题。
 *
 * 本脚本作为 Playwright 的 globalSetup 在每次 npm test 前自动执行：
 *   ① 快速探活：拿 state 里的 token 打一次鉴权接口（~300ms，不开浏览器）；
 *   ② 已失效 → 调 ui/tests/refresh_state.py 重新登录（视觉模型优先 + ddddocr 兜底）；
 *   ③ 刷新后再验一次，仍进不去就抛明确错误，而不是让用例裸奔到 /login。
 *
 * 独立使用：
 *   npm run auth              # 体检 + 按需刷新
 *   npm run auth:force        # 无条件重新登录一次
 *   HSC_SKIP_AUTH_CHECK=1 npx playwright test   # 跳过体检（CI / 调试用）
 *   HSC_AUTH_ROLE=admin npm run auth            # 指定角色账号
 */
const fs = require('fs');
const path = require('path');
const https = require('https');
const { spawnSync } = require('child_process');
const { chromium } = require('@playwright/test');
const env = require('./hsc-env');

const FORCE = process.argv.includes('--force');

/** 从 storage_state 的 localStorage 里取出 HSC 的 JWT */
function readToken() {
  try {
    const st = JSON.parse(fs.readFileSync(env.STORAGE_STATE, 'utf8'));
    for (const origin of st.origins || []) {
      for (const kv of origin.localStorage || []) {
        if (!kv.name.endsWith('LOCAL__KEY__')) continue;
        try {
          const t = JSON.parse(kv.value)?.value?.TOKEN__?.value;
          if (t) return t;
        } catch {
          /* 结构不符，继续找下一个 key */
        }
      }
    }
  } catch {
    /* 文件不存在 / 不是合法 JSON */
  }
  return null;
}

/**
 * 快速探活：用 Node 原生 https 打一次需要鉴权的接口。
 * 55 是自签且已过期的证书，必须 rejectUnauthorized:false，否则连不上（CERT_HAS_EXPIRED）。
 * @returns true=有效 / false=已失效 / null=探不动（网络或接口变动，交给浏览器判定）
 */
function probeToken(token) {
  return new Promise((resolve) => {
    let u;
    try {
      u = new URL(`${env.API_BASE_URL}/system/auth/routes?_t=${Date.now()}`);
    } catch {
      return resolve(null);
    }
    const req = https.request(
      {
        hostname: u.hostname,
        port: u.port || 443,
        path: u.pathname + u.search,
        method: 'GET',
        rejectUnauthorized: false,
        timeout: 8000,
        headers: { Authorization: token, 'X-Access-Token': token },
      },
      (res) => {
        let body = '';
        res.on('data', (c) => (body += c));
        res.on('end', () => {
          try {
            resolve(JSON.parse(body).success === true);
          } catch {
            resolve(null);
          }
        });
      }
    );
    req.on('error', () => resolve(null));
    req.on('timeout', () => {
      req.destroy();
      resolve(null);
    });
    req.end();
  });
}

/** 兜底判定：真开一个浏览器，看进系统后是不是被踹回登录页 */
async function browserCheck() {
  const browser = await chromium.launch({
    headless: true,
    args: ['--ignore-certificate-errors'],
  });
  try {
    const ctx = await browser.newContext({
      storageState: env.hasState() ? env.STORAGE_STATE : undefined,
      ignoreHTTPSErrors: true,
    });
    const page = await ctx.newPage();
    await page.goto(env.WEB_BASE_URL, { waitUntil: 'domcontentloaded', timeout: 25000 });
    await page.waitForTimeout(3500);
    const loginForm = await page.locator('input[placeholder="账号"]').count();
    const onLogin = /\/login(\/|\?|#|$)/.test(page.url());
    return { alive: loginForm === 0 && !onLogin, url: page.url() };
  } finally {
    await browser.close();
  }
}

/** 调 Python 侧重新登录（验证码识别逻辑在 ui/tests/login_page.py，不重复实现） */
function refresh() {
  const py = path.join(env.PROJECT_ROOT, 'venv', 'bin', 'python');
  const script = path.join(env.UI_ROOT, 'tests', 'refresh_state.py');
  if (!fs.existsSync(py)) throw new Error(`找不到项目 Python：${py}（请确认 hsc_auto/venv 存在）`);
  if (!fs.existsSync(script)) throw new Error(`找不到刷新脚本：${script}`);

  console.log(`[auth] 登录态已失效 → 重新登录（角色 ${env.AUTH_ROLE}，环境 ${env.ENV}）…`);
  const r = spawnSync(py, [script, '--role', env.AUTH_ROLE], {
    cwd: env.PROJECT_ROOT,
    stdio: 'inherit',
    // 关键：显式把本项目的 HSC_ENV 传给子进程。
    // 根 .env 里的 HSC_ENV 可能是另一个环境（config.py 会读它，且「不覆盖已存在的环境变量」），
    // 不传的话会出现「Node 体检 55、Python 却去登 123」的错位，刷新完还是登不上。
    env: { ...process.env, HSC_ENV: env.ENV },
  });
  if (r.status !== 0) throw new Error('登录态刷新失败，详见上方 Python 输出');
}

async function verify() {
  const token = readToken();
  if (token) {
    const ok = await probeToken(token);
    if (ok === true) return { ok: true, how: '接口探活' };
  }
  const c = await browserCheck();
  return c.alive ? { ok: true, how: '浏览器实测' } : { ok: false, url: c.url };
}

async function main() {
  if (process.env.HSC_SKIP_AUTH_CHECK === '1') {
    console.log('[auth] 已跳过登录态体检（HSC_SKIP_AUTH_CHECK=1）');
    return;
  }

  console.log(`[auth] 体检登录态：${path.basename(env.STORAGE_STATE)}（角色 ${env.AUTH_ROLE}）`);

  if (!FORCE && env.hasState()) {
    const token = readToken();
    if (!token) {
      console.log('[auth] state 文件里没读到 token');
    } else {
      const ok = await probeToken(token);
      if (ok === true) {
        console.log('[auth] ✅ 登录态有效，直接开跑');
        return;
      }
      if (ok === null) {
        // 探活接口本身不通（网络/路径变动），用浏览器做一次可靠判定，避免误判触发无谓重登
        console.log('[auth] 接口探活不明确，改用浏览器实测…');
        const c = await browserCheck();
        if (c.alive) {
          console.log('[auth] ✅ 浏览器实测已登录，直接开跑');
          return;
        }
      } else {
        console.log('[auth] ⚠️ token 已过期（接口返回未授权）');
      }
    }
  }

  refresh();

  const v = await verify();
  if (!v.ok) {
    throw new Error(
      [
        '登录态刷新后仍然无法进入系统。',
        `  当前落点：${v.url || '(未知)'}`,
        '  可能原因：① 账号密码已变更（检查项目根 .env 的 HSC_UI_*_PASSWORD）；',
        '           ② 55 环境不可达或后端异常；',
        '           ③ 该账号被锁定 / 登录次数受限。',
        '  排查命令：./venv/bin/python ui/tests/refresh_state.py --role ' +
          env.AUTH_ROLE +
          ' --headed',
      ].join('\n')
    );
  }
  console.log(`[auth] ✅ 登录态已刷新并校验通过（${v.how}）`);
}

// Playwright globalSetup 调用；也支持 node scripts/ensure_auth.js 直接跑
module.exports = main;

if (require.main === module) {
  main().catch((e) => {
    console.error('\n[auth] ❌ ' + e.message);
    process.exit(1);
  });
}
