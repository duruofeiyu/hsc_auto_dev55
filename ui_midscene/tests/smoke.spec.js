// 冒烟用例：用公共示例站验证 midscene 云模型能「看见页面 + 执行指令」，
// 全程不涉及任何 HSC 数据（避免截图出境，合规要求）。
// 运行：npx playwright test tests/smoke.spec.js
const { test } = require('@playwright/test');
const { PlaywrightAiFixture } = require('@midscene/web/playwright');

const aiTest = test.extend(PlaywrightAiFixture());

aiTest('midscene 云模型连通性冒烟（公共页面，零 HSC 数据）', async ({ page, ai, aiAssert }) => {
  // 公共示例站，无任何业务数据
  await page.goto('https://example.com');
  // 用「只读」动作，避免点击触发跳转导致的 navigation 上下文警告
  await ai('读取并告诉我这个页面的主标题文本');
  // AI 断言：页面包含预期字样
  await aiAssert('页面内容中包含 "Example" 字样');
});
