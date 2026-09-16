// HSC 桥接模式 —— 登录脚本 v2（验证码自动重试版）
//
// 运行（在你自己的 Mac 终端）：
//   cd /Users/a1-6/hsc_auto/ui/midscene
//   node bridge_login.mjs
//
// 凭证在 .env 里（已 gitignore）：HSC_LOGIN_URL / HSC_USER / HSC_PASS
//
// ===== 设计要点（每条都是被真实失败逼出来的）=====
// 1. 【密码不进提示词】用 aiInput(value, locatePrompt) —— value 走动作参数、不进自然语言提示词
//    （提示词才会发给模型），密码不经过模型。
// 2. 【验证码靠"看"】官方对验证码没有专门功能，用的就是同一个视觉模型：
//    aiQuery 让它读图片上的字符。验证码本身是反自动化设计，读错很正常 → 所以有重试。
// 3. 【零 AI 成本自检】evaluateJavaScript 读 DOM，判断"在不在登录页""登没登进去""密码框空没空"，
//    不花模型调用，也就不可能被 AI 的幻觉骗过。
// 4. 【防假绿】点登录后必须【DOM 硬校验】才判定成功。绝不因为"动作执行完了"就报成功。
// 5. 【自动重试 3 次】读错验证码 → 点图片刷新 → 重读 → 重填 → 再提交。三次都不行才转人工。
// 6. 【人工兜底】最后的保险：人工完成登录，脚本做校验。保证这条路永远走得通。

import 'dotenv/config';
import { AgentOverChromeBridge } from '@midscene/web/bridge-mode';
import readline from 'node:readline/promises';

const LOGIN_URL = process.env.HSC_LOGIN_URL || 'https://192.168.124.55:26400';
const USER = process.env.HSC_USER;
const PASS = process.env.HSC_PASS;
const MAX_ATTEMPTS = Number(process.env.HSC_LOGIN_ATTEMPTS || 3);

if (!USER || !PASS) {
  console.error('[env] 缺少 HSC_USER / HSC_PASS。请在 ui/midscene/.env 里补上：');
  console.error('      HSC_USER="ceshi"');
  console.error('      HSC_PASS="你的密码"');
  process.exit(2);
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const t0 = Date.now();
const el = () => `${((Date.now() - t0) / 1000).toFixed(1)}s`;

// 桥接的 evaluateJavaScript 透传 CDP 且不带 returnByValue，所以一律返回 JSON 字符串
async function readJs(agent, expr) {
  const res = await agent.evaluateJavaScript(expr);
  const v = res?.result?.value;
  if (v === undefined) console.error('[js] 读取失败：', JSON.stringify(res).slice(0, 260));
  return v;
}

function parse(s) {
  try {
    return typeof s === 'string' ? JSON.parse(s) : s;
  } catch {
    return null;
  }
}

// 零 AI 成本：登录页探测（含"密码框是否为空"——用来判断重试时要不要补填密码）
const LOGIN_PROBE = String.raw`(() => {
  const t = (document.body && document.body.innerText) || '';
  const pw = document.querySelector('input[type=password]');
  return JSON.stringify({
    href: location.href,
    hasCaptchaWord: t.includes('验证码'),
    hasPasswordInput: !!pw,
    passwordEmpty: pw ? String(pw.value || '').length === 0 : false,
    inputCount: document.querySelectorAll('input').length
  });
})()`;

// 零 AI 成本：是否已进入系统内部
const INSIDE_PROBE = String.raw`(() => {
  const t = (document.body && document.body.innerText) || '';
  const menus = ['智慧大屏','资产管理','脆弱性管理','合规运营','安服流程管理','安全知识库','系统管理','工单管理']
    .filter(m => t.includes(m));
  return JSON.stringify({
    href: location.href,
    matchedMenus: menus,
    matchedCount: menus.length,
    stillHasPasswordInput: !!document.querySelector('input[type=password]'),
    leftLoginUrl: !/login|signin|sign-in/i.test(location.href)
  });
})()`;

// 硬校验（双判据，防单点误判）：
//   必要条件：登录表单已消失（密码框没了）
//   充分条件：① 看到至少 1 个已知顶部菜单  或  ② URL 已离开 login 路径
async function checkInside(agent) {
  const p = parse(await readJs(agent, INSIDE_PROBE));
  const ok = !!(p && !p.stillHasPasswordInput && (p.matchedCount >= 1 || p.leftLoginUrl));
  return { ok, probe: p };
}

async function askHuman(msg) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  try {
    return await rl.question(msg);
  } finally {
    rl.close();
  }
}

const CAPTCHA_ASK =
  '返回 {captchaText: string}。' +
  'captchaText = 页面中验证码图片上显示的那几个字符（一般是 4 位字母数字混合）。' +
  '只返回图片上的字符本身，不要返回"验证码"这三个字，不要加空格。' +
  '如果当前页面看不到验证码图片，返回空字符串 ""';

(async () => {
  const agent = new AgentOverChromeBridge();

  console.log('[bridge] 打开 HSC 登录页…');
  console.log('[bridge] 地址 =', LOGIN_URL, '| 账号 =', USER, `| 最多尝试 ${MAX_ATTEMPTS} 次`);
  await agent.connectNewTabWithUrl(LOGIN_URL);
  await sleep(3500);

  // ===== ⓪ 零成本预检 =====
  const p0 = parse(await readJs(agent, LOGIN_PROBE));
  console.log(`[check] ⓪ 页面探测 [${el()}] =`, JSON.stringify(p0));

  if (p0 && !p0.hasPasswordInput && !p0.hasCaptchaWord) {
    const inside = await checkInside(agent);
    if (inside.ok) {
      console.log('[skip] 当前 Chrome 里已是登录状态，无需登录。');
      console.log('[skip] 想真正测登录，先在 Chrome 里退出登录再跑本脚本。');
      await agent.destroy();
      return;
    }
    console.warn('[warn] 没看到密码框也没看到顶部菜单，页面可能还在加载或结构变了，继续尝试。');
  }

  // ===== ① 填账号 =====
  console.log(`\n[bridge] ① 点"用户名/账号"输入框并输入账号… [${el()}]`);
  await agent.aiInput(USER, '页面上的"用户名"或"账号"输入框（通常是表单里的第一个文本输入框）');
  await sleep(700);

  // ===== ② 填密码 =====
  console.log(`[bridge] ② 点"密码"输入框并输入密码… [${el()}]`);
  await agent.aiInput(PASS, '页面上的"密码"输入框（输入框里的字是隐藏圆点的那种）');
  await sleep(700);
  console.log('[check] ①② 已填写（账号/密码内容不打印到终端，避免留痕）');

  // ===== ③④ 验证码：读 → 填 → 提交 → 校验；失败则刷新重试 =====
  let passed = false;
  let humanUsed = false;

  for (let attempt = 1; attempt <= MAX_ATTEMPTS && !passed; attempt++) {
    console.log(`\n———— 第 ${attempt}/${MAX_ATTEMPTS} 次尝试 [${el()}] ————`);

    if (attempt > 1) {
      // 上一次失败 → 刷新验证码 + （必要时）补填被清空的密码
      console.log('[bridge] 点验证码图片刷新出一张新的…');
      await agent.aiTap(
        '页面上的验证码图片本身，或者它旁边的"换一张""看不清"这类刷新链接/文字。' +
        '点击后验证码会变成新的一张'
      );
      await sleep(1500);

      const st = parse(await readJs(agent, LOGIN_PROBE));
      if (st && st.passwordEmpty) {
        console.log('[bridge] 检测到密码框被清空，重新填写…');
        await agent.aiInput(PASS, '页面上的"密码"输入框（输入框里的字是隐藏圆点的那种）');
        await sleep(600);
      }
    }

    // --- 读验证码 ---
    let code = '';
    try {
      const c = await agent.aiQuery(CAPTCHA_ASK);
      code = String(c?.captchaText || '').trim().replace(/\s+/g, '');
    } catch (e) {
      console.warn('[warn] 读验证码失败：', String(e.message).split('\n')[0]);
    }
    console.log(`[check] AI 读到的验证码 = ${JSON.stringify(code)} [${el()}]`);

    if (!/^[A-Za-z0-9]{3,6}$/.test(code)) {
      console.log('[warn] 本次读数不像有效验证码，跳过本次提交。');
      continue;
    }

    // --- 填验证码 ---
    await agent.aiInput(code, '页面上的"验证码"输入框（验证码图片左边或右边那个较短的输入框）');
    await sleep(700);

    // --- 提交 + 硬校验 ---
    console.log('[bridge] 点击"登录"按钮…');
    await agent.aiTap('页面上的"登录"按钮（表单下方的提交按钮）');
    await sleep(3800);

    const inside = await checkInside(agent);
    console.log(`[check] 登录后探测 [${el()}] =`, JSON.stringify(inside.probe));
    if (inside.ok) {
      passed = true;
      console.log(`\n[PASS] ✅ 登录成功（第 ${attempt} 次尝试，DOM 硬校验通过）[${el()}]`);
      break;
    }
    console.log(`[fail] 第 ${attempt} 次未通过 DOM 校验（验证码可能读错了）。`);
  }

  // ===== ⑤ 人工兜底 =====
  if (!passed) {
    console.error(`\n[FAIL] ❌ 自动尝试 ${MAX_ATTEMPTS} 次均未通过 DOM 校验。`);
    console.log('[human] 验证码本就是反自动化设计，读不准属正常。现在请【在浏览器里手动完成整个登录】');
    console.log('[human] （含验证码，看不清就点图片刷新）。');
    await askHuman('>>> 确认已进入系统内部后，按回车，我再做一次 DOM 校验… ');
    const finalCheck = await checkInside(agent);
    console.log('[check] ⑤ 人工登录后探测 =', JSON.stringify(finalCheck.probe));
    if (finalCheck.ok) {
      passed = true;
      humanUsed = true;
      console.log(`\n[PASS] ✅ 已进入系统（人工完成）[${el()}]`);
    } else {
      console.error('\n[FAIL] ❌ DOM 仍未看到顶部一级菜单，登录未成功。');
      console.error('       请把终端输出 + 登录页截图发给我，我继续排查。');
    }
  }

  await agent.destroy();
  console.log(humanUsed ? '\n[bridge] 完成（本次为人工完成登录），已断开桥接。' : '\n[bridge] 完成，已断开桥接。');
  if (!passed) process.exit(4);
})().catch((e) => {
  console.error('\n[bridge] 运行出错：', e);
  process.exit(1);
});
