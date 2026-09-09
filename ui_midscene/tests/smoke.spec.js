// 冒烟用例：用公共示例站验证 midscene 云模型能「看见页面 + 执行指令」，
// 全程不涉及任何 HSC 数据（避免截图出境，合规要求）。
// 运行：npx playwright test tests/smoke.spec.js
const { test } = require('@playwright/test');
const { PlaywrightAiFixture } = require('@midscene/web/playwright');

const aiTest = test.extend(PlaywrightAiFixture());

aiTest('midscene 云模型连通性冒烟（公共页面，零 HSC 数据）', async ({ page, ai, aiAssert }) => {
  // 公共示例站，无任何业务数据
  await page.goto('https://example.com');

  // 让 AI 自己找到并点击页面上的链接（自然语言，零选择器）
  await ai('点击页面上的链接');

  // AI 断言：页面内容已发生变化（跳转到 iana 页面）
  await aiAssert('页面内容已经发生变化，不再是 example.com 的初始内容');
});
