// 冒烟用例：用公共示例站验证 midscene 能「看见页面 + 执行指令」。
// 仅用公共页面，不涉及 HSC 数据。可在云端(阿里云 qwen-vl)或本地模型下运行。
// 运行：npx playwright test tests/smoke.spec.js
// 前置：`.env` 配置好可用的模型端点（云端 key 或本地 ollama 服务）
const { test } = require('@playwright/test');
const { PlaywrightAiFixture } = require('@midscene/web/playwright');

const aiTest = test.extend(PlaywrightAiFixture());

aiTest('midscene 模型连通性冒烟（公共页面，不涉及 HSC 数据）', async ({ page, ai, aiAssert }) => {
  // 公共示例站，无任何业务数据
  await page.goto('https://example.com');
  // 用「只读」动作，避免点击触发跳转导致的 navigation 上下文警告
  await ai('读取并告诉我这个页面的主标题文本');
  // AI 断言：页面包含预期字样
  await aiAssert('页面内容中包含 "Example" 字样');
});
