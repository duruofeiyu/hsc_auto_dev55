// HSC 桥接模式脚本 v10（DOM 优先 + AI 兜底 + 自证式统计）
//
// 运行（在你自己的 Mac 终端）：
//   cd /Users/a1-6/hsc_auto/ui/midscene
//   node bridge_hsc.mjs              # 只看"本页第一页"的口径（v9 行为）
//   node bridge_hsc.mjs --pending    # 追加：筛选 状态=待处理 → 读全库总数（能拿去用的数）
//
// ===== HSC 55 导航结构（2026-09-10 用户截图确认）=====
//   【顶部一级菜单】智慧大屏 / 资产管理 / 脆弱性管理 / 合规运营 / 安服流程管理 /
//                   安全知识库 / 系统管理 / 工单管理
//   【左侧二级菜单·脆弱性管理下】脆弱性概览 / 脆弱性扫描 / 系统漏洞管理 /
//                   网站漏洞管理 / 弱口令管理 / 基线管理 / 处置历史
//   【系统漏洞管理页内页签】漏洞总览 / 资产漏洞
//
// ===== 版本演进（每一版都是被真实失败逼出来的）=====
// v1~v3：写"点击左侧菜单中的脆弱性管理" → 定位错误（实际在顶部）→ AI 找不到就凭坐标乱点 → 又慢又假绿
// v4~v5：改为"顶部一级菜单 → 左侧二级菜单 → 页内标签"，并加"找不到就不许点击"
// v6   ：③ 之后硬校验"当前选中页签"（AI 点完页签没切过去，却在"资产漏洞"上读了数）
// v7   ：深链接直达 /assetsVuln，跳过全部菜单点击；新增 evaluateJavaScript 读 URL 与 DOM 对账
// v8   ：不再让"视觉模型"去点页签、去数行 —— 改用 DOM 精确操作
// v9   ：【本版核心】修正 v8 统计口径的两个硬伤（2026-09-10 15:16 实测暴露）：
//          (a) 表头永远为空 —— Element UI 的 el-table 把表头单独放在
//              .el-table__header-wrapper 里的另一张 <table> 内，那张表没有 tbody 行，
//              被 `if (!rows.length) continue` 直接跳过了。
//          (b) 行数被重复累加 —— 只按 `document.querySelectorAll('table')` 收集，
//              于是把「主表 + 固定列(fixed)副表」以及「隐藏页签里的表」全部算了进来，
//              30+30+7+7=74 行这种明显不合理的数就是这么来的。
//          修法：以 .el-table 容器为统计单元（天然避开 header/fixed 副表），
//                按可见性过滤隐藏页签，并输出每一列的"取值分布"作为自证证据 ——
//                到底是哪个"状态"列、有几行待处理，一目了然，不靠任何人猜。
//         另外：页签已是选中态时跳过点击；页签读取收窄到 .el-tabs 容器，去掉噪声。
// v10  ：【本版新增】`--pending`：用 DOM 把「状态」筛成"待处理"再读分页「共 X 条」，
//          拿到的是**全库待处理总数**（v9 那个 6 只是第一页 30 行里的），这才是能用的数。
//          分页总数改为优先读可见的 .el-pagination__total 并标注来源（更精确，不再全页正则）。
//          筛选四步全走 DOM（Element UI 的 el-select 是 click 冒泡到根节点 toggleMenu），
//          任一步走不通才启用 AI 兜底；筛选后还会校验"状态列是否只剩待处理"，防筛选假生效。

import 'dotenv/config';
import { AgentOverChromeBridge } from '@midscene/web/bridge-mode';

// 深链接：用户 2026-09-10 提供。可用环境变量覆盖，例如
//   HSC_VULN_URL=https://192.168.124.55:26400/xxx node bridge_hsc.mjs
const HSC_VULN_URL =
  process.env.HSC_VULN_URL || 'https://192.168.124.55:26400/assetsVuln';

// 是否追加"筛选状态=待处理 → 读全库总数"这一步（默认关闭，保持原有行为不变）
//   node bridge_hsc.mjs --pending
//   或 HSC_FILTER_PENDING=1 node bridge_hsc.mjs
const FILTER_PENDING =
  process.argv.includes('--pending') || process.env.HSC_FILTER_PENDING === '1';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// 桥接的 evaluateJavaScript 透传 CDP Runtime.evaluate，且不带 returnByValue：
// 对象拿不到值，所以表达式一律返回 JSON 字符串。这里做容错读取。
async function readJs(agent, expr) {
  const res = await agent.evaluateJavaScript(expr);
  const r = res && res.result;
  let v = r && r.value;
  if (v === undefined && r && typeof r.description === 'string') {
    v = r.description.replace(/^["']|["']$/g, '');
  }
  return v;
}

function parse(v) {
  if (typeof v !== 'string') return null;
  try {
    return JSON.parse(v);
  } catch {
    return null;
  }
}

const WHERE_EXPR = String.raw`JSON.stringify({href: location.href, title: document.title})`;

// ===== 读"当前选中的页签"（零 AI）=====
// 只看页面里第一个 .el-tabs（HSC 用 Element UI），避免把别处的 tab 组件读进来。
const ACTIVE_TAB_JS = String.raw`(() => {
  const norm = (s) => String(s == null ? '' : s).replace(/\s+/g, '');
  const box = document.querySelector('.el-tabs');
  const items = box ? Array.from(box.querySelectorAll('.el-tabs__item')) : [];
  const allTabs = items.map((el) => norm(el.textContent)).filter(Boolean);
  const act = items.filter(function (el) {
    return /is-active/i.test(String(el.className || '')) ||
           el.getAttribute('aria-selected') === 'true';
  }).map(function (el) { return norm(el.textContent); }).filter(Boolean);
  return JSON.stringify({
    activeTab: act[0] || '',
    allTabs: allTabs.slice(0, 10),
    elTabsCount: document.querySelectorAll('.el-tabs').length,
    href: location.href
  });
})()`;

// ===== 用 DOM 精确点击「漏洞总览」页签（零 AI、零误差）=====
// 策略：找 textContent 归一化后恰好等于目标文字、且自身不含同样文字的"最内层"元素，
// 对它派发 mousedown/mouseup/click（Vue/React 的监听都能收到，事件冒泡到父级 tab 容器）。
// 找不到就【什么都不点】，返回 near 供排查 —— 绝不瞎点坐标。
const CLICK_TAB_JS = String.raw`(() => {
  const want = '漏洞总览';
  const norm = (s) => String(s == null ? '' : s).replace(/\s+/g, '');
  const all = Array.from(document.querySelectorAll('body *'));
  const same = all.filter((el) => norm(el.textContent) === want);
  const leaf = same.filter((el) => !Array.from(el.children).some((c) => norm(c.textContent) === want));
  const pick = leaf[0] || same[same.length - 1];
  if (!pick) {
    const near = all.filter((el) => norm(el.textContent).indexOf(want) >= 0).slice(0, 8)
      .map((el) => ({ tag: el.tagName, cls: String(el.className || '').slice(0, 70) }));
    return JSON.stringify({ clicked: false, reason: 'no-element-with-exact-text', near: near });
  }
  const r = pick.getBoundingClientRect();
  const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  const fire = (t) => pick.dispatchEvent(new MouseEvent(t, {
    bubbles: true, cancelable: true, view: window, button: 0, clientX: cx, clientY: cy
  }));
  fire('mousedown'); fire('mouseup'); fire('click');
  let row = null;
  let n = pick.parentElement;
  for (let i = 0; i < 4 && n; i++) {
    const kids = Array.from(n.children).map((el) => norm(el.textContent)).filter((t) => t && t.length <= 10);
    if (kids.length >= 2) { row = kids; break; }
    n = n.parentElement;
  }
  return JSON.stringify({
    clicked: true,
    tag: pick.tagName,
    cls: String(pick.className || '').slice(0, 70),
    rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)],
    tabRow: row ? row.slice(0, 12) : []
  });
})()`;

// ===== 统计（确定性，不受模型错觉影响）=====
// 关键：以 .el-table 容器为单位，而不是裸 <table>。
//   · el-table 的主表/表头表/固定列表是分散的三张 <table>，按容器取只算一次
//   · 表头从 .el-table__header-wrapper 里取（v8 的 bug：那张表没 tbody 行，被跳过了）
//   · 只统计"当前可见"的表，隐藏页签里的表不算
//   · 额外输出"低基数列"（取值种类 <= 6 的列）的取值分布 —— 这一列是状态/等级/类型，
//     分布本身即证据：哪个列叫"状态"、待处理几行，全部公开可核对。
const COUNT_JS = String.raw`(() => {
  const norm = (s) => String(s == null ? '' : s).replace(/\s+/g, ' ').trim();

  const isVisible = (el) => {
    let n = el;
    while (n && n.nodeType === 1) {
      const cs = (window.getComputedStyle ? getComputedStyle(n) : null);
      if (cs && (cs.display === 'none' || cs.visibility === 'hidden')) return false;
      n = n.parentElement;
    }
    try {
      const r = el.getBoundingClientRect();
      if (r.width < 1 || r.height < 1) return false;
    } catch (e) { /* ignore */ }
    return true;
  };

  // 优先用 el-table 容器；没有则退回裸 table（并剔除固定列副表，避免重复计数）
  let containers = Array.from(document.querySelectorAll('.el-table'))
    .filter((el) => !el.closest('.el-table__fixed'));
  const usedElTable = containers.length > 0;
  if (!usedElTable) {
    containers = Array.from(document.querySelectorAll('table'))
      .filter((el) => !el.closest('.el-table__fixed, .el-table__fixed-body-wrapper'));
  }

  const out = [];
  let skippedInvisible = 0;
  let skippedNoRows = 0;

  for (const c of containers) {
    const headerWrap = c.querySelector('.el-table__header-wrapper') || c.querySelector('.el-table__header');
    const bodyWrap = (c.classList && c.classList.contains('el-table'))
      ? (c.querySelector('.el-table__body-wrapper') || c)
      : c;

    let headers = [];
    if (headerWrap) {
      headers = Array.from(headerWrap.querySelectorAll('th')).map((th) => norm(th.textContent));
    }
    if (!headers.length) {
      headers = Array.from(c.querySelectorAll('thead th')).map((th) => norm(th.textContent));
    }

    const rowEls = Array.from(bodyWrap.querySelectorAll('tbody tr'))
      .filter((tr) => tr.querySelector('td'));
    if (!rowEls.length) { skippedNoRows++; continue; }
    if (!isVisible(c)) { skippedInvisible++; continue; }

    const rows = rowEls.map((tr) =>
      Array.from(tr.querySelectorAll('td')).map((td) => norm(td.textContent)));

    const colCount = rows.reduce((m, r) => Math.max(m, r.length), 0);
    const enumCols = [];
    const pendingCols = [];
    for (let i = 0; i < colCount; i++) {
      const dist = {};
      const rowsOf = {};
      for (let k = 0; k < rows.length; k++) {
        const v = rows[k][i] == null ? '' : String(rows[k][i]);
        if (!v) continue;
        dist[v] = (dist[v] || 0) + 1;
        (rowsOf[v] = rowsOf[v] || []).push(k + 1);
      }
      const keys = Object.keys(dist);
      // 低基数列（<9 种取值）= 状态/等级/类型 这类枚举列，输出分布作为自证证据
      if (keys.length >= 1 && keys.length <= 8) {
        enumCols.push({ idx: i, header: (headers[i] || '') + '', dist: dist });
      }
      // 含"待处理"的列一律上报，不受上面的阈值影响（状态值种类多时不至于漏判）
      if (Object.prototype.hasOwnProperty.call(dist, '待处理')) {
        pendingCols.push({ idx: i, header: (headers[i] || '') + '', dist: dist, pending: dist['待处理'], rows: rowsOf['待处理'] });
      }
    }

    out.push({
      headers: headers,
      rowCount: rows.length,
      enumCols: enumCols,
      pendingCols: pendingCols,
      anyCellPending: rows.filter((r) => r.indexOf('待处理') >= 0).length,
      firstRow: (rows[0] || []).slice(0, 12)
    });
  }

  // 分页总数：优先读可见的分页组件文本节点（精确到"哪个分页"），
  // 读不到再退回 body 正则（v9 的做法），并标注来源便于排查。
  let totalText = '';
  let totalSource = 'none';
  const totalEls = Array.from(document.querySelectorAll('.el-pagination__total'));
  for (const el of totalEls) {
    if (!isVisible(el)) continue;
    const mm = String(el.textContent || '').match(/([0-9][0-9,]*)/);
    if (mm) { totalText = mm[1].replace(/,/g, ''); totalSource = 'el-pagination__total'; break; }
  }
  if (!totalText) {
    const body = (document.body && document.body.innerText) || '';
    const m = body.match(/共\s*([0-9,]+)\s*条/);
    if (m) { totalText = m[1].replace(/,/g, ''); totalSource = 'body-regex'; }
    return JSON.stringify({
      usedElTable: usedElTable,
      containerCount: containers.length,
      skippedInvisible: skippedInvisible,
      skippedNoRows: skippedNoRows,
      tables: out,
      totalText: totalText,
      totalSource: totalSource,
      pendingTextHits: (body.match(/待处理/g) || []).length
    });
  }
  const body2 = (document.body && document.body.innerText) || '';
  return JSON.stringify({
    usedElTable: usedElTable,
    containerCount: containers.length,
    skippedInvisible: skippedInvisible,
    skippedNoRows: skippedNoRows,
    tables: out,
    totalText: totalText,
    totalSource: totalSource,
    pendingTextHits: (body2.match(/待处理/g) || []).length
  });
})()`;

// ===== 筛选区：把「状态」筛成"待处理"，读到的「共 X 条」才是全库待处理总数 =====
// 说明：本页那个 6 只是第一页 30 行里的待处理行数，拿去用是错的。
// 下面四段全部走 DOM（Element UI 的 el-select：click 冒泡到 .el-select 根节点即 toggleMenu）。

// ① 体检：把筛选区有哪些"标签 + 是否是下拉 + 当前值"全列出来（失败时的诊断依据）
const FILTER_PROBE_JS = String.raw`(() => {
  const norm = (s) => String(s == null ? '' : s).replace(/\s+/g, ' ').trim();
  const vis = (el) => {
    let n = el;
    while (n && n.nodeType === 1) {
      const cs = window.getComputedStyle ? getComputedStyle(n) : null;
      if (cs && (cs.display === 'none' || cs.visibility === 'hidden')) return false;
      n = n.parentElement;
    }
    try { const r = el.getBoundingClientRect(); if (r.width < 1 || r.height < 1) return false; } catch (e) {}
    return true;
  };
  const items = Array.from(document.querySelectorAll('.el-form-item')).filter(vis);
  const formItems = items.map((fi) => {
    const labelEl = fi.querySelector('.el-form-item__label');
    const sel = fi.querySelector('.el-select');
    const inp = fi.querySelector('.el-select .el-input__inner') || fi.querySelector('input');
    return {
      label: norm(labelEl ? labelEl.textContent : ''),
      hasSelect: !!sel,
      value: norm(inp ? (inp.value || inp.placeholder || '') : '')
    };
  }).filter((x) => x.label || x.hasSelect);
  const buttons = Array.from(document.querySelectorAll('button, .el-button'))
    .filter(vis).map((b) => norm(b.textContent)).filter(Boolean).slice(0, 20);
  return JSON.stringify({
    formItemTotal: items.length,
    formItems: formItems.slice(0, 20),
    buttons: buttons
  });
})()`;

// ② 点开「状态」下拉：优先按 el-form-item 的 label 含"状态"定位；
//    定位不到且筛选区只有一个下拉时，退而用它（多数筛选页就一个 select）。
const OPEN_STATUS_SELECT_JS = String.raw`(() => {
  const norm = (s) => String(s == null ? '' : s).replace(/\s+/g, ' ').trim();
  const vis = (el) => {
    let n = el;
    while (n && n.nodeType === 1) {
      const cs = window.getComputedStyle ? getComputedStyle(n) : null;
      if (cs && (cs.display === 'none' || cs.visibility === 'hidden')) return false;
      n = n.parentElement;
    }
    try { const r = el.getBoundingClientRect(); if (r.width < 1 || r.height < 1) return false; } catch (e) {}
    return true;
  };
  const fire = (el) => {
    const r = el.getBoundingClientRect();
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    ['mousedown', 'mouseup', 'click'].forEach((t) => el.dispatchEvent(new MouseEvent(t, {
      bubbles: true, cancelable: true, view: window, button: 0, clientX: cx, clientY: cy
    })));
  };
  const items = Array.from(document.querySelectorAll('.el-form-item')).filter(vis);
  const labels = items.map((fi) => norm((fi.querySelector('.el-form-item__label') || {}).textContent)).filter(Boolean);

  let picked = '';
  let selectEl = null;
  const byLabel = items.find((fi) => /状态/.test(norm((fi.querySelector('.el-form-item__label') || {}).textContent)));
  if (byLabel) {
    selectEl = byLabel.querySelector('.el-select');
    if (selectEl) picked = 'by-label-状态';
  }
  if (!selectEl) {
    const sels = items.map((fi) => fi.querySelector('.el-select')).filter(Boolean);
    if (sels.length === 1) { selectEl = sels[0]; picked = 'only-select-in-form'; }
  }
  if (!selectEl) {
    return JSON.stringify({ opened: false, reason: 'no-status-select', labels: labels });
  }
  // 只点一次：事件会冒泡到 .el-select 根节点上的 toggleMenu，点多反而开了又关
  const inner = selectEl.querySelector('.el-input__inner');
  fire(inner || selectEl);
  return JSON.stringify({
    opened: true, picked: picked,
    cls: String(selectEl.className || '').slice(0, 80),
    labels: labels
  });
})()`;

// ③ 在展开的下拉里点"待处理"选项（只认可见下拉；找不到就把选项名全列出来）
const PICK_PENDING_OPTION_JS = String.raw`(() => {
  const norm = (s) => String(s == null ? '' : s).replace(/\s+/g, ' ').trim();
  const vis = (el) => {
    let n = el;
    while (n && n.nodeType === 1) {
      const cs = window.getComputedStyle ? getComputedStyle(n) : null;
      if (cs && (cs.display === 'none' || cs.visibility === 'hidden')) return false;
      n = n.parentElement;
    }
    try { const r = el.getBoundingClientRect(); if (r.width < 1 || r.height < 1) return false; } catch (e) {}
    return true;
  };
  const fire = (el) => {
    const r = el.getBoundingClientRect();
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    ['mousedown', 'mouseup', 'click'].forEach((t) => el.dispatchEvent(new MouseEvent(t, {
      bubbles: true, cancelable: true, view: window, button: 0, clientX: cx, clientY: cy
    })));
  };
  const drops = Array.from(document.querySelectorAll('.el-select-dropdown')).filter(vis);
  const options = [];
  let pick = null;
  for (const d of drops) {
    const lis = Array.from(d.querySelectorAll('.el-select-dropdown__item')).filter(vis);
    lis.forEach((li) => options.push(norm(li.textContent)));
    if (!pick) pick = lis.find((li) => norm(li.textContent) === '待处理');
  }
  if (!pick) {
    return JSON.stringify({ clicked: false, dropdowns: drops.length, options: options.slice(0, 25) });
  }
  fire(pick);
  return JSON.stringify({
    clicked: true, text: norm(pick.textContent),
    dropdowns: drops.length, options: options.slice(0, 25)
  });
})()`;

// ④ 点"查询/搜索"按钮触发筛选
const CLICK_QUERY_JS = String.raw`(() => {
  const tight = (s) => String(s == null ? '' : s).replace(/\s+/g, '');
  const vis = (el) => {
    let n = el;
    while (n && n.nodeType === 1) {
      const cs = window.getComputedStyle ? getComputedStyle(n) : null;
      if (cs && (cs.display === 'none' || cs.visibility === 'hidden')) return false;
      n = n.parentElement;
    }
    try { const r = el.getBoundingClientRect(); if (r.width < 1 || r.height < 1) return false; } catch (e) {}
    return true;
  };
  const fire = (el) => {
    const r = el.getBoundingClientRect();
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    ['mousedown', 'mouseup', 'click'].forEach((t) => el.dispatchEvent(new MouseEvent(t, {
      bubbles: true, cancelable: true, view: window, button: 0, clientX: cx, clientY: cy
    })));
  };
  const btns = Array.from(document.querySelectorAll('button, .el-button')).filter(vis);
  const texts = btns.map((b) => tight(b.textContent));
  let pick = btns.find((b) => tight(b.textContent) === '查询') ||
             btns.find((b) => tight(b.textContent) === '搜索');
  if (!pick) {
    return JSON.stringify({ clicked: false, buttons: texts.filter(Boolean).slice(0, 20) });
  }
  fire(pick);
  return JSON.stringify({
    clicked: true, text: tight(pick.textContent),
    buttons: texts.filter(Boolean).slice(0, 20)
  });
})()`;

// ⑤ 确认筛选已生效：读回「状态」下拉当前值
const READ_STATUS_VALUE_JS = String.raw`(() => {
  const norm = (s) => String(s == null ? '' : s).replace(/\s+/g, ' ').trim();
  const vis = (el) => {
    let n = el;
    while (n && n.nodeType === 1) {
      const cs = window.getComputedStyle ? getComputedStyle(n) : null;
      if (cs && (cs.display === 'none' || cs.visibility === 'hidden')) return false;
      n = n.parentElement;
    }
    try { const r = el.getBoundingClientRect(); if (r.width < 1 || r.height < 1) return false; } catch (e) {}
    return true;
  };
  const items = Array.from(document.querySelectorAll('.el-form-item')).filter(vis);
  const fi = items.find((x) => /状态/.test(norm((x.querySelector('.el-form-item__label') || {}).textContent)));
  const scope = fi || document.querySelector('.el-form') || document.body;
  const inp = scope.querySelector('.el-select .el-input__inner') || scope.querySelector('input');
  return JSON.stringify({ statusValue: norm(inp ? inp.value : '') });
})()`;

function tabActive(p) {
  if (!p) return false;
  return String(p.activeTab || '').indexOf('漏洞总览') >= 0;
}

(async () => {
  const agent = new AgentOverChromeBridge();

  console.log('[bridge] 连接真实 Chrome 并【直达】系统漏洞管理页（跳过菜单点击）…');
  console.log('[bridge] 目标地址 =', HSC_VULN_URL);
  await agent.connectNewTabWithUrl(HSC_VULN_URL);
  await sleep(3200);

  // ===== ⓪ 零 AI 成本：问浏览器现在在哪一页 =====
  const at0 = parse(await readJs(agent, WHERE_EXPR));
  console.log('[check] ⓪ 直达后所在页面 =', JSON.stringify(at0));
  if (at0 && !String(at0.href).includes('assetsVuln')) {
    console.warn('[warn] 地址里没有 assetsVuln —— 可能被重定向了（未登录？）。');
  }

  // ===== ① 确保停在「漏洞总览」页签：先读，已是则跳过点击 =====
  console.log('\n[bridge] ① 确认「漏洞总览」页签（DOM，0 AI 成本）…');
  let cur = parse(await readJs(agent, ACTIVE_TAB_JS));
  console.log('[check] ① 当前页签状态 =', JSON.stringify(cur));

  if (tabActive(cur)) {
    console.log('[dom] 已在「漏洞总览」页签，跳过点击。');
  } else {
    const clickRes = parse(await readJs(agent, CLICK_TAB_JS));
    console.log('[dom] 点击结果 =', JSON.stringify(clickRes));
    if (clickRes && clickRes.clicked) {
      await sleep(1500);
      cur = parse(await readJs(agent, ACTIVE_TAB_JS));
      console.log('[check] ① 点击后页签状态 =', JSON.stringify(cur));
    }
  }

  let verified = tabActive(cur);
  if (!verified) {
    console.warn('\n[warn] DOM 未能确认页签 —— 启用 AI 兜底（deepLocate 精定位）…');
    await agent.ai(
      '在页面主区域的页签行中，点击文字为"漏洞总览"的标签/页签。' +
        '注意：页签行里相邻的"资产漏洞"不要点。' +
        '如果页面上没有"漏洞总览"这几个字，请不要点击任何位置，直接结束。',
      { deepLocate: true }
    );
    await sleep(1800);
    cur = parse(await readJs(agent, ACTIVE_TAB_JS));
    console.log('[check] ① AI 兜底后页签状态 =', JSON.stringify(cur));
    verified = tabActive(cur);
  }

  if (!verified) {
    console.error('\n[STOP] 未能确认切到「漏洞总览」页签。');
    console.error('       已停止，绝不在错误的页签上读数（避免假绿）。');
    await agent.destroy();
    process.exit(3);
  }

  const at1 = parse(await readJs(agent, WHERE_EXPR));
  console.log('[check] ① 切换后所在页面 =', JSON.stringify(at1));

  // ===== ② DOM 精确统计（权威数据源）=====
  console.log('\n[bridge] ② 用 DOM 精确统计（0 AI 成本）…');
  const dom = parse(await readJs(agent, COUNT_JS));
  console.log('[dom] 原始统计 =', JSON.stringify(dom));

  let domRows = -1;
  let domPending = -1;
  let pendingColLabel = '';
  if (dom && Array.isArray(dom.tables) && dom.tables.length) {
    domRows = dom.tables.reduce((s, t) => s + (t.rowCount || 0), 0);
    console.log('[dom] 统计单元 =', dom.usedElTable ? 'el-table 容器' : '裸 table',
      '｜容器数 =', dom.containerCount,
      '｜因不可见跳过 =', dom.skippedInvisible,
      '｜因无数据行跳过 =', dom.skippedNoRows);
    dom.tables.forEach((t, i) => {
      console.log('[dom] 表' + (i + 1) + ' 表头 =', JSON.stringify(t.headers));
      console.log('[dom] 表' + (i + 1) + ' 数据行 =', t.rowCount, '｜首行 =', JSON.stringify(t.firstRow));
      (t.enumCols || []).forEach((c) => {
        console.log('[dom] 表' + (i + 1) + ' 列[' + c.idx + '] "' + c.header + '" 取值分布 =', JSON.stringify(c.dist));
      });
    });

    const allPendingCols = [];
    dom.tables.forEach((t) => (t.pendingCols || []).forEach((c) => allPendingCols.push(c)));
    const primary =
      allPendingCols.find((c) => /状态/.test(c.header)) ||
      allPendingCols.find((c) => /处置/.test(c.header)) ||
      allPendingCols[0];
    if (primary) {
      domPending = primary.pending;
      pendingColLabel = '"' + (primary.header || '第' + (primary.idx + 1) + '列') + '"';
      console.log('[dom] 「待处理」计数列 =', pendingColLabel, '→', primary.pending, '行，行号 =', JSON.stringify(primary.rows));
    }
    if (allPendingCols.length > 1) {
      console.log('[dom] 注意：共有', allPendingCols.length, '个列含"待处理"字样 =',
        JSON.stringify(allPendingCols.map((c) => ({ col: c.header || ('列' + c.idx), n: c.pending }))));
    }
    console.log('[dom] 本页合计 =', domRows, '行；分页区「共 X 条」=', dom.totalText || '(未找到)');
  } else {
    console.warn('[warn] DOM 没找到表格结构 —— 请把上面的 [dom] 原始统计发我。');
  }

  // ===== ③ AI 交叉验证（本脚本唯一一次 AI 调用）=====
  console.log('\n[bridge] ③ AI 交叉验证（1 次调用）…');
  const ai = await agent.aiQuery(
    '返回 {activeTab: string, count: number, total: number}。' +
      'activeTab=页签行中当前处于选中的页签文字；' +
      'count=本页列表中状态列显示为"待处理"的行数量（没有状态列就返回 -1）；' +
      'total=列表底部分页区"共 X 条"的数字（没有就返回 -1）'
  );
  console.log('[ai ] AI 读取 =', JSON.stringify(ai));

  // ===== ④ 对账 =====
  console.log('\n[bridge] ④ 交叉对账…');
  const aiCount = ai && typeof ai.count === 'number' ? ai.count : -1;
  const domTotal = dom && dom.totalText ? String(dom.totalText).replace(/,/g, '') : '';
  const aiTotal = ai && typeof ai.total === 'number' ? String(ai.total) : '';

  if (domPending >= 0 && aiCount >= 0 && domPending !== aiCount) {
    console.warn(`[warn] DOM 数到 ${domPending} 行，AI 数到 ${aiCount} 行 —— 不一致，以 DOM 为准（DOM 是读列值，不是看图）。`);
  } else if (domPending >= 0 && aiCount >= 0) {
    console.log(`[ok]   两边一致：本页「待处理」= ${domPending} 行`);
  }
  if (domTotal && aiTotal && domTotal !== aiTotal) {
    console.warn(`[warn] 分页总数不一致：DOM=${domTotal}，AI=${aiTotal} —— 以 DOM 为准。`);
  }

  // ===== ⑤ 可选：筛选「状态 = 待处理」，读全库待处理总数（才是能拿去用的数）=====
  let globalPending = -1;
  let filterOk = false;
  if (FILTER_PENDING) {
    console.log('\n[bridge] ⑤ 筛选「状态 = 待处理」→ 读全库总数（DOM 优先，0 AI 成本）…');

    const probe = parse(await readJs(agent, FILTER_PROBE_JS));
    console.log('[filter] 筛选区体检 =', JSON.stringify(probe));

    const opened = parse(await readJs(agent, OPEN_STATUS_SELECT_JS));
    console.log('[filter] 展开「状态」下拉 =', JSON.stringify(opened));

    let domPathOk = !!(opened && opened.opened);
    if (domPathOk) {
      await sleep(900);
      const pickedOpt = parse(await readJs(agent, PICK_PENDING_OPTION_JS));
      console.log('[filter] 选择「待处理」选项 =', JSON.stringify(pickedOpt));
      domPathOk = !!(pickedOpt && pickedOpt.clicked);
      if (domPathOk) {
        await sleep(900);
        const q = parse(await readJs(agent, CLICK_QUERY_JS));
        console.log('[filter] 点击查询按钮 =', JSON.stringify(q));
      }
    }

    // DOM 走不通时，才动用 AI（1 次调用）——DOM 优先 + AI 兜底
    if (!domPathOk) {
      console.warn('[warn] DOM 未能完成筛选 —— 启用 AI 兜底…');
      await agent.ai(
        '在页面顶部的筛选条件区，把"状态"筛选条件选择为"待处理"，然后点击"查询"按钮。' +
          '如果页面上没有"状态"这个筛选条件，请不要点击任何位置，直接结束。'
      );
    }

    await sleep(2600);
    const sv = parse(await readJs(agent, READ_STATUS_VALUE_JS));
    console.log('[filter] 「状态」筛选当前值 =', JSON.stringify(sv));

    const dom2 = parse(await readJs(agent, COUNT_JS));
    if (dom2 && Array.isArray(dom2.tables) && dom2.tables.length) {
      const pc = [];
      dom2.tables.forEach((t) => (t.pendingCols || []).forEach((c) => pc.push(c)));
      const p2 = pc.find((c) => /状态/.test(c.header)) || pc[0];
      if (p2) console.log('[filter] 筛选后 状态列分布 =', JSON.stringify(p2.dist));
      const rowsAllPending = !!(p2 && p2.dist && Object.keys(p2.dist).length === 1 &&
        Object.prototype.hasOwnProperty.call(p2.dist, '待处理'));
      console.log('[filter] 筛选后分页「共 X 条」=',
        (dom2.totalText || '(未找到)') + '（来源 ' + (dom2.totalSource || '?') + '）');
      if (dom2.totalText) {
        globalPending = parseInt(String(dom2.totalText).replace(/,/g, ''), 10);
        filterOk = true;
      }
      if (!rowsAllPending && filterOk) {
        console.warn('[warn] 筛选后本页状态列仍有非"待处理"的值 —— 筛选可能没真正生效，总数存疑。');
        filterOk = false;
      }
    } else {
      console.warn('[warn] 筛选后 DOM 没读到表格结构，请把上方 [filter] 输出发我。');
    }
  }

  console.log('\n[result] ===== 结论 =====');
  console.log('  当前页签        : 漏洞总览');
  console.log('  本页数据行      :', domRows >= 0 ? domRows : '(DOM 未读到)');
  console.log('  「待处理」计数列:', pendingColLabel || '(未定位到状态列)');
  console.log('  本页「待处理」  :', domPending >= 0 ? domPending : '(DOM 未读到)');
  console.log('  分页「共 X 条」 :', domTotal || '(未找到)');
  if (FILTER_PENDING) {
    console.log('  ── 全库口径（已按 状态=待处理 筛选）──');
    console.log('  全库「待处理」  :',
      filterOk ? globalPending : '(未能确定，见上方 [filter]/[warn] 输出)');
  } else {
    console.log('  ↑ 注意：列表是【分页】的，"共 X 条"是整个筛选结果的总数，不是本页行数。');
    console.log('    要拿"全库待处理总数"，加 --pending 参数重跑：');
    console.log('      node bridge_hsc.mjs --pending');
  }

  await agent.destroy();
  console.log('\n[bridge] 完成，已断开桥接。');
})().catch((e) => {
  console.error('[bridge] 运行出错：', e);
  process.exit(1);
});
