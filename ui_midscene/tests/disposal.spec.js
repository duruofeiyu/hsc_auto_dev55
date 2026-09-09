// HSC 处置面板 —— 自然语言 UI 自动化（midscene.js）
// 全程不需要写任何 CSS 选择器，AI 看截图自己找元素
import { test, expect } from '@playwright/test';
import { PlaywrightAiFixture } from '@midscene/web/playwright';

// 用 midscene 的 Playwright fixture，自动注入 ai / aiAssert / aiQuery
const aiTest = test.extend(PlaywrightAiFixture());

// ---- 用例 1：处置面板「派单」冒烟 ----
aiTest('处置面板-派单 自然语言冒烟', async ({ page, ai, aiAssert }) => {
  await page.goto('/');

  // 让 AI 自己点进菜单，不写选择器
  await ai('进入「系统漏洞管理」菜单，等待漏洞列表加载完成');

  // 打开第一条「待处理」漏洞的处置面板
  await ai('点击列表中第一条状态为「待处理」的漏洞，打开它的处置面板');

  // 选择「派单」并填信息提交
  await ai('在处置面板中选择「派单」方式，填写必要信息后点击提交');

  // 自然语言断言：不比对 DOM 文本，让 AI 判断结果
  await aiAssert('页面提示处置/派单成功，且没有报错信息');
});

// ---- 用例 2：处理结论「提交复核」冒烟 ----
aiTest('处理结论-提交复核 自然语言冒烟', async ({ page, ai, aiAssert }) => {
  await page.goto('/');

  await ai('进入「系统漏洞管理」菜单，等待漏洞列表加载完成');
  await ai('点击列表中第一条状态为「待处理」的工单，打开处理面板');

  // 选一个处理结论 → 保存 → 提交复核
  await ai('在处理面板中选择一个处理结论（如「已修复」），点击保存，再点击提交复核并确认');

  await aiAssert('提交复核后页面提示成功，该工单不再处于可处理状态');
});

// ---- 用例 3：其它模块「误报」处置（展示跨模块广度，零选择器）----
// 这正是你担心的「其它交互逻辑」——加一个模块只需加一句中文，无需探 DOM
aiTest('网站漏洞管理-误报处置 自然语言冒烟', async ({ page, ai, aiAssert }) => {
  await page.goto('/');

  await ai('进入「网站漏洞管理」菜单，等待列表加载完成');
  await ai('点击列表中第一条状态为「待处理」的漏洞，打开它的处置面板');
  await ai('在处置面板中选择「误报」，填写误报原因后点击提交');

  await aiAssert('误报处置后页面提示成功，且该漏洞不再处于待处理状态');
});

// ---- 扩展提示 ----
// 想加新模块/新交互，照着上面写一句中文即可，例如：
//   await ai('进入「基线核查」，对第一条项执行「确认合规」');
//   await aiAssert('确认后该项状态变为已合规');
// 无需任何选择器维护 —— 这就是 midscene 相对 Page Object 的核心省时点。
