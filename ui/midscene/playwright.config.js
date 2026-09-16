// midscene + Playwright 配置
// 登录态由 scripts/ensure_auth.js 在跑用例前统一体检/刷新（与 pytest 框架共用 ui/tests/.auth）
const { defineConfig } = require('@playwright/test');
const env = require('./scripts/hsc-env');   // 内部已加载 ui/midscene/.env

module.exports = defineConfig({
  testDir: './tests',
  timeout: 120000,
  expect: { timeout: 10000 },

  // 关键：跑用例前先体检登录态。token 过期就自动重登，
  // 避免整个 test run 停在 /login 上、报一堆与真正测试目标无关的错。
  globalSetup: require.resolve('./scripts/ensure_auth.js'),

  reporter: [
    ['list'],
    // midscene 自带报告器：跑完生成 HTML 报告，可回看 AI 每一步点了哪个元素
    ['@midscene/web/playwright-reporter', { type: 'merged' }],
  ],
  use: {
    // 有头模式：你能亲眼看到 AI 操作浏览器（调试时推荐）
    // 无头跑（如 CI）用 HSC_HEADLESS=1
    headless: process.env.HSC_HEADLESS === '1',
    // HSC 55 用自签且已过期的证书，chromium 默认不信任，必须忽略证书错误才能打开
    ignoreHTTPSErrors: true,
    viewport: { width: 1600, height: 900 },
    // 复用 pytest 框架的登录态文件（state_{ENV}_{role}.json），省去每轮登录
    storageState: env.STORAGE_STATE,
    // HSC 55 环境地址（123 环境用 HSC_ENV=123 覆盖）
    baseURL: env.ORIGIN,
    trace: 'on-first-retry',
  },
});
