// 环境解析：ui/midscene 侧统一从这里取「环境 / 地址 / 登录态文件」，避免多处写死产生漂移。
// 与根 config.py 的口径保持一致（同一个 state 文件、同一套环境地址）。
const path = require('path');
const fs = require('fs');

const ROOT = path.resolve(__dirname, '..');            // hsc_auto/ui/midscene/
const UI_ROOT = path.resolve(ROOT, '..');              // hsc_auto/ui/（2026-09-15 目录重组）
const PROJECT_ROOT = path.resolve(UI_ROOT, '..');      // hsc_auto/

// 环境变量的读取顺序（都不覆盖已存在的环境变量，等价 config.py 的 _load_dotenv）：
//   1) 项目根 .env   —— 与 pytest 框架共用的「唯一环境开关」（HSC_ENV=55/123）
//   2) ui/midscene/.env —— 本侧专有配置（MIDSCENE_* 模型 key 等），同名时以它为准
// 这样 `HSC_ENV=123` 一改，接口框架和 midscene 会一起切过去，不会再出现
// 「Python 跑 123、Node 偷偷跑 55」的错位。
require('dotenv').config({ path: path.join(PROJECT_ROOT, '.env') });
require('dotenv').config({ path: path.join(ROOT, '.env') });

const ENV = process.env.HSC_ENV || '55';

const ORIGINS = {
  '55': 'https://192.168.124.55:26400',
  '123': 'https://192.168.124.123:26400',
};

// HSC_BASE_URL 可覆盖；若误填成接口地址（带 /hsc-system-api），这里自动剥掉
const ORIGIN = (process.env.HSC_BASE_URL || ORIGINS[ENV] || ORIGINS['55'])
  .replace(/\/+$/, '')
  .replace(/\/hsc-system-api$/, '');

// ⚠️ HSC 前端部署在【根路径】，不是 /hsc-system-web。
// 2026-09-10 实测踩坑：/hsc-system-web/xxx 虽然也能取到 index.html，
// 但 Vue Router 的 base 是 /，path 变成 /hsc-system-web/xxx → 命中未匹配路由
// → 前端渲染「500 非常抱歉，服务器出错了」错误组件（看着像后端挂了，其实不是）。
// 症状：手动浏览器访问正常、自动化全红。别再往前面加路径前缀。
const WEB_BASE_URL = process.env.HSC_UI_WEB_BASE_URL || ORIGIN;
const API_BASE_URL = `${ORIGIN}/hsc-system-api`;

// 用例用哪个账号的登录态（与根 config.py 的 UI_ROLE_USERS 对齐）
const AUTH_ROLE = process.env.HSC_AUTH_ROLE || 'common_admin';

// 与 pytest 框架共用同一份 storage_state（谁先跑谁刷新，互相受益）
const STORAGE_STATE = process.env.HSC_STORAGE_STATE
  || path.resolve(UI_ROOT, 'tests', '.auth', `state_${ENV}_${AUTH_ROLE}.json`);

module.exports = {
  ROOT,
  UI_ROOT,
  PROJECT_ROOT,
  ENV,
  ORIGIN,
  WEB_BASE_URL,
  API_BASE_URL,
  AUTH_ROLE,
  STORAGE_STATE,
  hasState: () => fs.existsSync(STORAGE_STATE),
};
