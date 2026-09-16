#!/usr/bin/env node
/**
 * HSC × Midscene YAML 流程执行器
 *
 * 用法：
 *   node scripts/run-yaml.js flows/asset_discover.yaml
 *   node scripts/run-yaml.js flows/xxx.yaml --var CASE_ID=SCAN-003 --var EXPECT=87
 *   HSC_HEADLESS=1 node scripts/run-yaml.js flows/xxx.yaml      # 无头（CI）
 *
 * YAML 里用 {{变量名}} 引用变量；内置 BASE_URL / ENV。
 * 同一个 YAML 换一组 --var 就是一条新用例 —— 这就是数据驱动。
 *
 * ---------------------------------------------------------------------------
 * 为什么自己实现指令分发，而不是直接调 agent.runYaml()？
 * 2026-09-10 在 @midscene/web 1.12.5 上实测，runYaml 有两个硬伤：
 *   ① `javascript` 指令不生效 —— 返回值不进 result，里面抛错也不让任务失败。
 *      而 DOM 硬断言（防假绿的关键）恰恰要靠它。
 *   ② aiAssert 失败时抛出的错误信息被丢掉，只剩一句
 *      "Error(s) occurred in running yaml script:"，排查全靠猜。
 * 自己分发就 30 行，换来：断言一定生效、报错一定清楚、执行过程完全可见。
 * ---------------------------------------------------------------------------
 */
const fs = require('fs');
const path = require('path');
const env = require('./hsc-env'); // 已加载 .env，解析好环境/地址/登录态
const yaml = require('js-yaml');
const { chromium } = require('playwright');
const { PlaywrightAgent } = require('@midscene/web/playwright');

// 这些字段是"配置"，不是"指令"
const META_KEYS = new Set([
  'name',
  'continueOnError',
  'errorMessage',
  'timeout',
  'cacheable',
  'deepLocate',
  'deepThink',
  'context',
]);

const SUPPORTED = [
  'ai / aiAct / aiAction',
  'aiTap',
  'aiHover',
  'aiInput (+value)',
  'aiKeyboardPress (+keyName)',
  'aiScroll',
  'hoverAt（真实鼠标 hover，配 data-hov 标记用）',
  'aiQuery / aiNumber / aiString / aiBoolean / aiAsk',
  'aiAssert',
  'aiWaitFor',
  'javascript',
  'sleep',
  'recordToReport',
].join(', ');

// ---------- 参数解析 ----------
function parseArgs(argv) {
  const vars = {};
  let file = null;
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--var') {
      const kv = argv[++i] || '';
      const j = kv.indexOf('=');
      if (j > 0) vars[kv.slice(0, j)] = kv.slice(j + 1);
    } else if (!a.startsWith('--')) {
      file = a;
    }
  }
  return { file, vars };
}

// ---------- {{变量}} 替换 ----------
function substitute(text, vars) {
  const missing = new Set();
  const out = text.replace(/\{\{\s*([\w.]+)\s*\}\}/g, (m, k) => {
    if (k in vars) return String(vars[k]);
    missing.add(k);
    return m;
  });
  return { out, missing: [...missing] };
}

// ---------- URL 归一化 ----------
// 三种写法都支持：
//   1. http(s)://...      绝对地址，原样用
//   2. demo/xxx.html      相对路径，若本地文件存在 → 转成 file:// （方便离线演示）
//   3. /assetDiscover     前端路由，拼到当前环境的 WEB_BASE_URL 上
function resolveUrl(url) {
  if (!url) return null;
  if (/^[a-z]+:\/\//i.test(url)) return url;
  const local = path.resolve(env.ROOT, url);
  if (fs.existsSync(local)) return `file://${local}`;
  return `${env.WEB_BASE_URL.replace(/\/+$/, '')}/${String(url).replace(/^\/+/, '')}`;
}

/**
 * HSC 55 是开发环境，后端偶发 500/502。
 * 2026-09-10 实测撞到：首屏进了「500 服务器出错了」错误页并一直不恢复。
 * 这类抖动会被 AI 如实读成"没有卡片"，报出与用例无关的失败，
 * 所以进页面后先等应用真正可用，再开始跑步骤。
 */
async function waitForAppReady(page, { timeoutMs = 40000, reloadEveryMs = 10000 } = {}) {
  const started = Date.now();
  let lastReload = 0;

  const isErrorPage = () =>
    page
      .evaluate(() => {
        const t = (document.body.innerText || '').replace(/\s+/g, '');
        return t.length < 400 && /500|501|502|服务器出错|服务器错误/.test(t);
      })
      .catch(() => false);

  while (Date.now() - started < timeoutMs) {
    if (!(await isErrorPage())) {
      const waited = ((Date.now() - started) / 1000).toFixed(1);
      if (Number(waited) > 2) console.log(`[nav] 页面已就绪（等待 ${waited}s）`);
      return true;
    }
    if (Date.now() - lastReload > reloadEveryMs) {
      console.log('[nav] 页面仍是后端错误页，刷新一次…');
      await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 }).catch(() => {});
      lastReload = Date.now();
    }
    await page.waitForTimeout(1000);
  }
  console.warn('[nav] 等待超时，页面仍不可用 —— 这是环境问题，不是用例问题');
  return false;
}

// ---------- 定位类可选参数 ----------
function pickLocateOpts(item) {
  const o = {};
  for (const k of ['deepLocate', 'deepThink', 'cacheable', 'xpath', 'context']) {
    if (k in item) o[k] = item[k];
  }
  return o;
}

function describeCmd(item) {
  const k = Object.keys(item).find((x) => !META_KEYS.has(x));
  const v = typeof item[k] === 'string' ? item[k].split('\n')[0].slice(0, 56) : '';
  return `${k}: ${v}`;
}

// ---------- 单步执行 ----------
async function runFlowItem({ agent, page, item, results }) {
  const cmdKey = Object.keys(item).find((k) => !META_KEYS.has(k));
  if (!cmdKey) throw new Error(`这一步没有可识别的指令：${JSON.stringify(item)}`);
  const val = item[cmdKey];
  const record = (v) => {
    if (item.name) results[item.name] = v;
    return v;
  };

  switch (cmdKey) {
    case 'ai':
    case 'aiAct':
    case 'aiAction':
      return record(await agent.aiAct(val));

    case 'aiTap':
      return void (await agent.aiTap(val, pickLocateOpts(item)));

    case 'aiHover':
      return void (await agent.aiHover(val, pickLocateOpts(item)));

    case 'aiInput':
      return void (await agent.aiInput(val, { ...pickLocateOpts(item), value: item.value }));

    case 'aiKeyboardPress':
      return void (await agent.aiKeyboardPress(val, { ...pickLocateOpts(item), keyName: item.keyName }));

    case 'aiScroll':
      return void (
        await agent.aiScroll(val, {
          ...pickLocateOpts(item),
          ...(item.scrollType ? { scrollType: item.scrollType } : {}),
          ...(item.direction ? { direction: item.direction } : {}),
          ...(item.distance ? { distance: item.distance } : {}),
        })
      );

    case 'hoverAt':
      // 真实鼠标 hover（Playwright page.hover）。2026-09-16 加：Element UI 的
      // el-dropdown 列头筛选，合成 dispatchEvent(mouseenter) 在组件重渲染后不生效，
      // 只有真实鼠标移动能触发 hover 类交互。选择器支持 Playwright 引擎语法；
      // 惯用配合：先 javascript 给目标元素 setAttribute('data-hov','1')，再
      // hoverAt: '[data-hov] .el-dropdown' —— 定位与动作两步都确定性。
      return void (await page.hover(val, { timeout: item.timeout || 8000 }));

    case 'aiQuery':
    case 'aiNumber':
    case 'aiString':
    case 'aiBoolean':
    case 'aiAsk':
      return record(await agent[cmdKey](val));

    case 'aiAssert': {
      const r = await agent.aiAssert(val, item.errorMessage);
      const pass = r ? r.pass !== false : true;
      if (!pass) {
        throw new Error(`断言未通过：${val}\n模型判断：${(r && (r.thought || r.message)) || '(未给出原因)'}`);
      }
      return record('pass');
    }

    case 'aiWaitFor':
      return void (await agent.aiWaitFor(val, item.timeout ? { timeoutMs: item.timeout } : undefined));

    case 'sleep':
      return void (await page.waitForTimeout(Number(val)));

    case 'javascript': {
      // 在页面上下文执行。里面 throw 会把错误原样带回 → 这就是硬断言：
      // 不经过模型判断，没有"假绿"空间。
      const wrapped = `(async () => { ${val} })()`;
      return record(await page.evaluate(wrapped));
    }

    case 'recordToReport':
      return void (await agent.recordToReport(val, { content: item.content || '' }));

    default:
      throw new Error(`不支持的指令 "${cmdKey}"。支持：${SUPPORTED}`);
  }
}

async function main() {
  const { file, vars } = parseArgs(process.argv.slice(2));
  if (!file) {
    console.error('用法: node scripts/run-yaml.js <flow.yaml> [--var key=value ...]');
    process.exit(2);
  }
  const abs = path.resolve(env.ROOT, file);
  if (!fs.existsSync(abs)) {
    console.error(`[x] 找不到 YAML 文件：${abs}`);
    process.exit(2);
  }
  if (!env.hasState()) {
    console.error(`[x] 登录态不存在：${env.STORAGE_STATE}\n    先跑一次：npm run auth:force`);
    process.exit(2);
  }

  const raw = fs.readFileSync(abs, 'utf8');
  const { out, missing } = substitute(raw, { BASE_URL: env.WEB_BASE_URL, ENV: env.ENV, ...vars });
  if (missing.length) {
    console.warn(`[!] 以下变量没传值，将按字面量执行：${missing.join(', ')}`);
    console.warn('    传值示例：node scripts/run-yaml.js <file> --var NAME=值');
  }

  const doc = yaml.load(out) || {};
  const target = doc.page || doc.web || doc.browser || {};
  const url = resolveUrl(target.url);
  const tasks = Array.isArray(doc.tasks) ? doc.tasks : [];
  if (!tasks.length) {
    console.error('[x] YAML 里没有 tasks，无事可做');
    process.exit(2);
  }

  console.log(`[env] 环境=${env.ENV}  UI=${env.WEB_BASE_URL}`);
  console.log(`[auth] 登录态=${path.basename(env.STORAGE_STATE)}`);
  console.log(`[flow] ${path.relative(env.ROOT, abs)}  共 ${tasks.length} 个任务`);

  const browser = await chromium.launch({ headless: process.env.HSC_HEADLESS === '1' });
  const context = await browser.newContext({
    storageState: env.STORAGE_STATE,
    ignoreHTTPSErrors: true, // HSC 55 自签证书
    viewport: { width: 1600, height: 900 },
  });
  const page = await context.newPage();

  let failed = 0;
  let skipped = 0;
  try {
    if (url) {
      console.log(`[nav] ${url}`);
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
      await page.waitForTimeout(1500);
      await waitForAppReady(page);
    }

    // 缓存（2026-09-16 启用）：aiTap/aiInput 等定位结果与 aiAct 规划步骤落盘到
    // midscene_run/cache/，重复回归时命中缓存直接回放，省模型调用与耗时；
    // DOM 文本/结构变化会自动失效回退 AI（不会假命中）。查询类 API（aiQuery 等）不缓存。
    const agent = new PlaywrightAgent(page, {
      cache: { id: `hsc-flows-${env.ENV}` },
    });

    for (const [i, task] of tasks.entries()) {
      const title = task.name || `任务${i + 1}`;
      const flow = Array.isArray(task.flow) ? task.flow : [];
      console.log(`\n=== [${i + 1}/${tasks.length}] ${title} ===`);

      const results = {};
      let taskFailed = false;

      for (const [j, item] of flow.entries()) {
        const label = item.name ? item.name : describeCmd(item);
        const t0 = Date.now();
        try {
          await runFlowItem({ agent, page, item, results });
          console.log(`  ✓ [${j + 1}/${flow.length}] ${label}  (${((Date.now() - t0) / 1000).toFixed(1)}s)`);
        } catch (e) {
          taskFailed = true;
          console.error(`  ✗ [${j + 1}/${flow.length}] ${label}  (${((Date.now() - t0) / 1000).toFixed(1)}s)`);
          console.error(`      ${String((e && e.message) || e).split('\n').join('\n      ')}`);
          break; // 同任务内后续步骤不再跑
        }
      }

      if (Object.keys(results).length) {
        console.log('  [提取结果]', JSON.stringify(results, null, 2));
      }

      if (taskFailed) {
        failed++;
        if (!task.continueOnError) {
          skipped = tasks.length - i - 1;
          console.error(`  （未标记 continueOnError，跳过剩余 ${skipped} 个任务）`);
          break;
        }
      }
    }

    try {
      await agent.destroy();
    } catch {
      /* 某些版本无 destroy，忽略 */
    }
  } finally {
    await browser.close();
  }

  const passed = tasks.length - failed - skipped;
  console.log(`\n[结果] ${passed} passed, ${failed} failed${skipped ? `, ${skipped} skipped` : ''}`);
  process.exit(failed ? 1 : 0);
}

main().catch((e) => {
  console.error('[x] 执行器异常：', e);
  process.exit(1);
});
