// HSC 处置面板 —— 自然语言 UI 自动化（midscene.js）
// 全程不需要写任何 CSS 选择器，AI 看截图自己找元素
//
// ⚠️ 防假绿约定（陈宇航要求）：所有「操作成功」不能只信 UI 即时提示，
//    必须 reload 后用 aiQuery 提取列表数值做硬断言（before/after 比对），
//    确认状态真的持久化变更，杜绝「提示成功但刷新后打回」的假绿。
// ⚠️ 合规红线默认：本文件访问 HSC 真实界面，原则上只本地/合规环境跑。
//    【已授权例外】2026-09-10 质量负责人陈宇航明确授权：55 为内部测试环境、
//    不含真实客户数据，允许用云端模型跑本文件（截图传阿里云），属 deliberate exception，
//    年审问起可追溯此授权。生产/演示环境绝不走此路径。
import { test, expect } from '@playwright/test';
import { PlaywrightAiFixture } from '@midscene/web/playwright';

// 用 midscene 的 Playwright fixture，自动注入 ai / aiAssert / aiQuery
const aiTest = test.extend(PlaywrightAiFixture());

// ---- 用例 1：处置面板「派单」冒烟 ----
aiTest('处置面板-派单 自然语言冒烟', async ({ page, ai, aiAssert, aiQuery }) => {
  await page.goto('/');
  await ai('点击左侧「脆弱性管理」菜单，在展开的子菜单中点击「系统漏洞管理」，等待漏洞列表加载完成');

  // 防假绿①：先记录「待处理」数量基准（aiQuery 提数值，硬比对）
  const before = await aiQuery('返回漏洞列表中状态为「待处理」的数量，只返回 {"count": 数字}');

  // 打开第一条「待处理」漏洞的处置面板
  await ai('点击列表中第一条状态为「待处理」的漏洞，打开它的处置面板');
  await ai('在处置面板中选择「派单」方式，填写必要信息后点击提交');

  // 即时提示断言（可能假绿，仅作第一轮）
  await aiAssert('页面提示处置/派单成功，且没有报错信息');

  // 防假绿②：刷新后复核持久性，不轻信 UI 成功提示
  await page.reload();
  await ai('点击左侧「脆弱性管理」菜单，在展开的子菜单中点击「系统漏洞管理」，等待漏洞列表加载完成');
  const after = await aiQuery('返回漏洞列表中状态为「待处理」的数量，只返回 {"count": 数字}');
  expect(after.count).toBe(before.count - 1);
});

// ---- 用例 2：处理结论「提交复核」冒烟 ----
aiTest('处理结论-提交复核 自然语言冒烟', async ({ page, ai, aiAssert, aiQuery }) => {
  await page.goto('/');

  await ai('点击左侧「脆弱性管理」菜单，在展开的子菜单中点击「系统漏洞管理」，等待漏洞列表加载完成');
  const before = await aiQuery('返回列表中状态为「待处理」的工单数量，只返回 {"count": 数字}');

  await ai('点击列表中第一条状态为「待处理」的工单，打开处理面板');
  await ai('在处理面板中选择一个处理结论（如「已修复」），点击保存，再点击提交复核并确认');

  await aiAssert('提交复核后页面提示成功，该工单不再处于可处理状态');

  // 防假绿：刷新后复核「待处理」数量是否真减 1
  await page.reload();
  await ai('点击左侧「脆弱性管理」菜单，在展开的子菜单中点击「系统漏洞管理」，等待漏洞列表加载完成');
  const after = await aiQuery('返回列表中状态为「待处理」的工单数量，只返回 {"count": 数字}');
  expect(after.count).toBe(before.count - 1);
});

// ---- 用例 3：其它模块「误报」处置（展示跨模块广度，零选择器）----
// 这正是你担心的「其它交互逻辑」——加一个模块只需加一句中文，无需探 DOM
aiTest('网站漏洞管理-误报处置 自然语言冒烟', async ({ page, ai, aiAssert, aiQuery }) => {
  await page.goto('/');

  await ai('进入「网站漏洞管理」菜单，等待列表加载完成');
  const before = await aiQuery('返回网站漏洞列表中状态为「待处理」的数量，只返回 {"count": 数字}');

  await ai('点击列表中第一条状态为「待处理」的漏洞，打开它的处置面板');
  await ai('在处置面板中选择「误报」，填写误报原因后点击提交');

  await aiAssert('误报处置后页面提示成功，且该漏洞不再处于待处理状态');

  // 防假绿：刷新后复核「待处理」数量是否真减 1
  await page.reload();
  await ai('进入「网站漏洞管理」菜单，等待列表加载完成');
  const after = await aiQuery('返回网站漏洞列表中状态为「待处理」的数量，只返回 {"count": 数字}');
  expect(after.count).toBe(before.count - 1);
});

// ---- 扩展提示 ----
// 想加新模块/新交互，照着上面写一句中文即可，例如：
//   await ai('进入「基线核查」，对第一条项执行「确认合规」');
//   await aiAssert('确认后该项状态变为已合规');
// 无需任何选择器维护 —— 这就是 midscene 相对 Page Object 的核心省时点。
