// midscene + Playwright 配置
// 复用 pytest 框架已经生成好的登录态（storage_state），无需重新登录
require('dotenv').config();
const { defineConfig } = require('@playwright/test');

// 按环境挑选复用哪个登录态文件（与 pytest 框架 .auth 目录命名一致）
//   55 环境  -> state_55_common_admin.json
//   123 环境 -> state_123_common_admin.json
// 也可用 HSC_STORAGE_STATE 强制指定任意路径
const ENV = process.env.HSC_ENV || '55';
const DEFAULT_STATE = ENV === '123'
  ? '../ui_tests/.auth/state_123_common_admin.json'
  : '../ui_tests/.auth/state_55_common_admin.json';

module.exports = defineConfig({
  testDir: './tests',
  timeout: 120000,
  expect: { timeout: 10000 },
  reporter: [
    ['list'],
    // midscene 自带报告器：跑完生成 HTML 报告，可回看 AI 每一步点了哪个元素
    ['@midscene/web/playwright-reporter', { type: 'merged' }],
  ],
  use: {
    // 有头模式：你能亲眼看到 AI 操作浏览器（调试时推荐）
    headless: false,
    // HSC 55 用自签证书，chromium 默认不信任，必须忽略证书错误才能打开
    ignoreHTTPSErrors: true,
    viewport: { width: 1600, height: 900 },
    // 直接复用 pytest 框架的登录态文件，省去登录步骤
    storageState: process.env.HSC_STORAGE_STATE || DEFAULT_STATE,
    // HSC 55 环境地址（123 环境用 HSC_BASE_URL 覆盖）
    baseURL: process.env.HSC_BASE_URL || 'https://192.168.124.55:26400',
    trace: 'on-first-retry',
  },
});
