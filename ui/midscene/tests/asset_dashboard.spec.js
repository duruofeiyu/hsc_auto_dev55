// ============================================================================
// HSC 资产管理 → 资产发现（路由 /assetDiscover）—— 统计卡片 & 趋势图浮层验证
// 对应手工用例：TC-HSC55-SCAN-002 / SCAN-003 / SCAN-004
// ============================================================================
// 【本轮踩过的三个坑，都写在这里，别再踩】
//
// 坑 1｜路由拼错：手工用例备注写 /AssetDiscovery，实际菜单树里是 assetDiscover
//   （来自 /system/auth/routes：资产管理 assetsManage → 资产发现 assetDiscover）。
//   /AssetDiscovery 打开只是一个「500 服务器出错了」错误页。
//
// 坑 2｜假绿：原来 SCAN-002 只断言「页面上有统计卡片」，结果哪怕落到
//   资产概览页（卡片是 资产总数/主机设备/…）也照样通过。
//   修法：断言必须钉住本页专有卡片名（见 REQUIRED_CARDS），落到别的页立刻红。
//
// 坑 3｜AI hover 找不准细条：卡片里的趋势图只有 417x70 px，是卡片里很窄的一条。
//   让 AI「悬停任务执行概览卡片」会落到卡片空白处 → 浮层不出现 → 假红。
//   修法：坐标是 DOM 能算准的事，就别问 AI（见 hoverTrendChart）。
//
// 【分工原则】
//   DOM 能确定的事（进页面、找卡片、算坐标、读浮层文本）→ 全部走 DOM，快且免费；
//   只在最后留 1 次 AI 交叉验证，用来确认「AI 看到的和 DOM 读到的一致」。
// ============================================================================

import { test, expect } from '@playwright/test';
import { PlaywrightAiFixture } from '@midscene/web/playwright';

const aiTest = test.extend(PlaywrightAiFixture());

// 资产发现页深链接（真实路由，来自 /system/auth/routes 菜单树）
const PAGE_URL = process.env.HSC_ASSET_URL || '/assetDiscover';

// 本页面「专有」的卡片名 —— 把断言钉死在正确页面上，防止再次假绿
const REQUIRED_CARDS = ['探测任务总数', '任务执行概览', '扫描活跃度'];

// 卡片里的趋势图标题（用于定位要 hover 的那一条 canvas）
const CARD = {
  execution: '任务执行概览',   // 带趋势图的执行情况卡片
  activity: '扫描活跃度',       // 扫描活跃度卡片
};

// ---------------------------------------------------------------------------
// 登录态守卫：被踹回 /login 时立刻抛「人话」，别让 midscene 那句
// 「当前页面是登录界面」把真正原因盖掉。
// （防假绿的另一半：也要防"假失败"——报错指错方向同样是浪费）
// ---------------------------------------------------------------------------
async function assertLoggedIn(page) {
  const onLogin = /\/login(\/|\?|#|$)/.test(page.url());
  const hasLoginForm = (await page.locator('input[placeholder="账号"]').count()) > 0;
  if (onLogin || hasLoginForm) {
    throw new Error(
      [
        `登录态已失效：页面被重定向到登录页（${page.url()}）`,
        '  这不是用例本身的问题，而是 ui/tests/.auth 里的 storage_state 过期了。',
        '  修复：cd ui/midscene && npm run auth   （会自动重新登录并刷新登录态）',
      ].join('\n')
    );
  }
}

async function openAssetDiscover(page) {
  await page.goto(PAGE_URL);
  await assertLoggedIn(page);
  // 等统计卡片渲染出来（DOM 判断，不花 AI 调用）
  await page
    .locator('text=探测任务总数')
    .first()
    .waitFor({ state: 'visible', timeout: 30000 });
  await page.waitForTimeout(1500);   // 留一点时间给卡片里的趋势图 canvas 绘制
}

// ---------------------------------------------------------------------------
// DOM 工具：读页面可见正文 / 求两次正文的差集
// innerText 天然排除隐藏元素，所以「hover 后多出来的行」基本就是浮层内容。
// ---------------------------------------------------------------------------
async function visibleText(page) {
  return (await page.locator('body').innerText()) || '';
}

function addedLines(before, after) {
  const old = new Set(before.split('\n').map((s) => s.trim()).filter(Boolean));
  return after
    .split('\n')
    .map((s) => s.trim())
    .filter((s) => s && !old.has(s));
}

// ---------------------------------------------------------------------------
// DOM 工具：把鼠标移到「指定卡片里那条趋势图」的正中央
// 取「同时包含该卡片标题、且含 canvas 的最小元素」，再取 canvas 中心坐标。
// 返回移动到的坐标，便于出错时定位。
// ---------------------------------------------------------------------------
async function hoverTrendChart(page, cardTitle) {
  const box = await page.evaluate((title) => {
    const candidates = [...document.querySelectorAll('div,section,article')]
      .filter((el) => {
        const t = el.innerText || '';
        return t.includes(title) && el.querySelector('canvas');
      })
      // 选「最具体」的那个：canvas 数量最少、面积最小
      .sort((a, b) => {
        const ca = a.querySelectorAll('canvas').length;
        const cb = b.querySelectorAll('canvas').length;
        if (ca !== cb) return ca - cb;
        const ra = a.getBoundingClientRect();
        const rb = b.getBoundingClientRect();
        return ra.width * ra.height - rb.width * rb.height;
      });
    const holder = candidates[0];
    if (!holder) return null;
    const c = holder.querySelector('canvas');
    const r = c.getBoundingClientRect();
    if (!r.width || !r.height) return null;
    return { x: r.x + r.width / 2, y: r.y + r.height / 2, w: Math.round(r.width), h: Math.round(r.height) };
  }, cardTitle);

  if (!box) throw new Error(`没找到「${cardTitle}」卡片里的趋势图 canvas`);
  await page.mouse.move(box.x, box.y);
  return box;
}

// 把鼠标移开（确定性动作，不花 AI 调用）
async function moveAway(page) {
  await page.mouse.move(5, 5);
  await page.waitForTimeout(900);
}

// ===========================================================================
// TC-HSC55-SCAN-002：统计卡片数据显示
// 预期：卡片正常展示；数字为非负整数、格式正确；百分比在 0-100% 之间
// 说明：这些卡片文本本来就是 DOM 文本（不是 canvas），所以用 DOM 直接读，精确且零成本。
// 因此这条用原生 test 而不是 aiTest —— 不创建 midscene agent，不花任何 AI 调用。
// ===========================================================================
test('TC-HSC55-SCAN-002 资产发现-统计卡片数据显示', async ({ page }) => {
  await openAssetDiscover(page);

  const cards = await page.evaluate((names) =>
    names.map((name) => {
      // 找到「包含该卡片名、且含数字」的最小可见块 —— 才是卡片本体，
      // 只按卡片名找会命中外层标题元素（innerText 就只有标题、没有数值）。
      const el = [...document.querySelectorAll('div,section,article')]
        .filter((e) => {
          const t = e.innerText || '';
          return t.includes(name) && /\d/.test(t);
        })
        .sort((a, b) => {
          const ra = a.getBoundingClientRect();
          const rb = b.getBoundingClientRect();
          return ra.width * ra.height - rb.width * rb.height;
        })[0];
      return { name, text: (el?.innerText || '').replace(/\s+/g, ' ').trim() };
    }), REQUIRED_CARDS);

  console.log('[cards]');
  for (const c of cards) console.log(`   ${c.name}: ${c.text.slice(0, 120)}`);

  for (const c of cards) {
    // 防假绿第一道：三张本页专有卡片必须都在。落到资产概览等其它页面会立刻红。
    expect(c.text, `没有读到「${c.name}」卡片，当前页面可能不是资产发现页`).not.toBe('');

    const nums = c.text.match(/-?\d+(\.\d+)?/g) || [];
    expect(nums.length, `「${c.name}」里读不到任何数字：${c.text}`).toBeGreaterThan(0);

    for (const n of nums) {
      // 预期结果 2/4：非负整数，失败/成功次数均 ≥ 0
      expect(Number(n), `「${c.name}」出现负数：${n}`).toBeGreaterThanOrEqual(0);
      // 预期结果 3：百分比数值在 0-100% 范围内
      if (c.text.includes(`${n}%`)) {
        expect(Number(n), `「${c.name}」百分比越界：${n}%`).toBeLessThanOrEqual(100);
      }
    }
  }

  // 预期结果 1 的强化版：数值不能是空占位符（-, --, N/A 之类）
  for (const c of cards) {
    expect(c.text, `「${c.name}」疑似未取到数据：${c.text}`).not.toMatch(/^\s*[-—]+\s*$/);
  }
});

// ===========================================================================
// TC-HSC55-SCAN-003：统计卡片 hover 浮动数据展示
// 预期：出现浮动框；移开后消失
// 说明：卡片里的趋势图是 417x70 的细条，坐标由 DOM 算，不使用 AI 悬停。
// ===========================================================================
aiTest('TC-HSC55-SCAN-003 资产发现-统计卡片hover浮动数据展示', async ({ page, aiQuery }) => {
  await openAssetDiscover(page);

  // 三段式 ①：未悬停时不该有浮层
  const baseline = await visibleText(page);
  await moveAway(page);

  // 三段式 ②：DOM 定位坐标 → 悬停到趋势图正中央
  const box = await hoverTrendChart(page, CARD.execution);
  console.log('[hover] 任务执行概览趋势图中心 =', JSON.stringify(box));
  await page.waitForTimeout(900);

  const afterHover = await visibleText(page);
  const shown = addedLines(baseline, afterHover);
  console.log('[tooltip@card] 悬停后新增文本 =', JSON.stringify(shown));

  expect(shown.length, '悬停统计卡片趋势图后应当出现浮动提示框内容').toBeGreaterThan(0);
  // 预期结果：浮层里是「日期 + 数值」这类关键数据
  expect(
    shown.some((t) => /\d{1,2}-\d{1,2}|\d{1,2}月\d{1,2}日/.test(t)),
    `浮层里应当含日期，实际新增文本：${JSON.stringify(shown)}`
  ).toBe(true);
  expect(
    shown.some((t) => /\d+/.test(t)),
    `浮层里应当含数值，实际新增文本：${JSON.stringify(shown)}`
  ).toBe(true);

  // AI 交叉验证（只此一次）：确认 AI 看到的和 DOM 读到的一致。
  // ⚠️ 实测结论（2026-09-10，GLM-4.6v）：同一个浮层，两条用例结果不一致 ——
  //    SCAN-003 的卡片趋势图，DOM 已明确读到 "09-08"/"76"，AI 却返回 {"shown": false}；
  //    SCAN-004 的活动度趋势图，AI 又正确看到 {"shown": true, "text": "09-08 成功 0 失败 0"}。
  //    → 视觉模型对这类一闪而过的小浮层判定**不稳定**。
  //    所以这里【只打日志、不断言】，断言权归 DOM；留着它是为了持续观察模型表现。
  const aiSaid = await aiQuery(
    '页面上是否出现了一个跟随鼠标的浮动提示框（tooltip）？只返回 JSON：{"shown": true或false, "text": "浮层文字"}'
  );
  console.log('[ai-cross-check]', JSON.stringify(aiSaid));

  // 三段式 ③：移开后浮层消失
  await moveAway(page);
  const afterLeave = await visibleText(page);
  const stillThere = addedLines(baseline, afterLeave).filter((t) => shown.includes(t));
  expect(stillThere, `鼠标移开后浮层应当消失，但仍看到：${JSON.stringify(stillThere)}`).toEqual([]);
});

// ===========================================================================
// TC-HSC55-SCAN-004：趋势图 hover 浮动数据展示
// 预期：趋势图正常渲染；hover 数据点出现浮层且含日期、次数；移开后消失
// ===========================================================================
aiTest('TC-HSC55-SCAN-004 资产发现-折线图hover浮动数据展示', async ({ page, aiQuery }) => {
  await openAssetDiscover(page);

  const baseline = await visibleText(page);
  await moveAway(page);

  const box = await hoverTrendChart(page, CARD.activity);
  console.log('[hover] 扫描活跃度趋势图中心 =', JSON.stringify(box));
  await page.waitForTimeout(900);

  const afterHover = await visibleText(page);
  const shown = addedLines(baseline, afterHover);
  console.log('[tooltip@chart] 悬停后新增文本 =', JSON.stringify(shown));

  expect(shown.length, '悬停扫描活跃度趋势图后应当出现浮动提示框内容').toBeGreaterThan(0);
  expect(
    shown.some((t) => /\d{1,2}-\d{1,2}|\d{1,2}月\d{1,2}日/.test(t)),
    `浮层里应当含日期，实际新增文本：${JSON.stringify(shown)}`
  ).toBe(true);

  const aiSaid = await aiQuery(
    '页面上是否出现了一个跟随鼠标的浮动提示框（tooltip）？只返回 JSON：{"shown": true或false, "text": "浮层文字"}'
  );
  console.log('[ai-cross-check]', JSON.stringify(aiSaid));

  await moveAway(page);
  const afterLeave = await visibleText(page);
  const stillThere = addedLines(baseline, afterLeave).filter((t) => shown.includes(t));
  expect(stillThere, `鼠标移开后浮层应当消失，但仍看到：${JSON.stringify(stillThere)}`).toEqual([]);
});

// ===========================================================================
// 跑完这一轮，你应该拿到三样东西：
//   ① console 打印的真实卡片文本与浮层原文 → 用来把断言收紧到真实值
//   ② midscene_run/report/*.html            → 回看 AI 每一步的框选落在哪
//   ③ 一个明确结论：这条路走得通吗
// 走通了，就照着 templates/asset_new_task.param.spec.js 铺到别的页面。
// ===========================================================================
