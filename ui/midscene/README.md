# HSC UI 自动化 PoC —— midscene.js

用**自然语言 + 视觉**写 UI 自动化，代码里不再有会烂掉的 CSS 选择器。
与现有 `pytest` 接口框架**并存互补**，不互相替代。

## 目录速览（先认路，再干活）

```
ui/midscene/
├── tests/        ★ 正式用例（npm test 跑的就是这里）asset_dashboard / disposal / smoke
├── flows/        ★ YAML 用例（node scripts/run-yaml.js flows/xxx.yaml）
├── scripts/        工具脚本：ensure_auth 登录体检 / check-env 环境体检 /
│                   capture-api 抓接口 / run-yaml YAML 执行器 / hsc-env 环境解析
├── templates/      参数化用例模板（不参与执行，看懂后拷进 tests/）
├── demo/           本地演示页（不依赖内网）
├── bridge_hsc.mjs / bridge_login.mjs / check_model.mjs   根目录 3 个散装脚本
│                   （bridge=连你真实 Chrome 免登录取数 / check_model=模型连通性探针）
├── .env            ★ 模型配置 + bridge 登录凭证（注意：环境开关和 UI 密码在项目根 hsc_auto/.env）
├── playwright.config.js / package.json
├── midscene_run/   运行产物：HTML 报告 + 日志（看 AI 点了哪，就在这）
├── test-results/   playwright 失败产物
└── node_modules/   依赖，永远不用看
```

只有打 ★ 的 4 处是日常打交道的；`midscene_run/` `test-results/` `node_modules/` 是产物和依赖，Finder 里乱就乱在这三个。

**写用例请去隔壁 `../ui/py/`（Python + pytest）**：本目录的 JS/YAML/脚本只是执行内核，
用例设计、断言、数据驱动、Allure 全在 Python 侧 —— 见 `ui/py/README.md`。
`tests/*.spec.js` 是早期 PoC 写法，保留对照，不再新增。

## 核心结论（几天踩坑换来的，先看这个）

> **DOM 读得到的，别交给 AI；DOM 读不到的，才用 AI。**
>
> 视觉模型擅长"人眼能看懂"的模糊定位，但在**密集相邻小目标**上会看偏，
> 而且它"点了个坐标并执行完"就会在报告里打勾 —— **打勾 ≠ 做对**。
> 因此定稿写法是：**DOM 干确定的事，AI 只兜底 + 交叉验证**。

实测数据（系统漏洞管理页「漏洞总览」页签）：

| 环节 | 谁做 | 结果 |
|---|---|---|
| 打开页面 | 深链接直达 `/assetsVuln` | 跳过全部菜单点击，最不稳的一环直接省掉 |
| 确认页签 | DOM 读 `is-active` class | 确定性，不通过就 `[STOP]` 退出，绝不带病读数 |
| 数「待处理」行数 | DOM 遍历 `.el-table` 状态列 | **6 行**（附行号与逐列取值分布自证） |
| 交叉验证 | `aiQuery` 1 次 | 也读到 6 → 两边一致 |

对比：早期版本 9 次 AI 调用、又慢又点不准；现在 **1 次调用、约 5 秒、结果可核对**。

## 两种用法，别搞混

| | 桥接脚本 `bridge_*.mjs` | Playwright 用例 `tests/*.spec.js` |
|---|---|---|
| 控制谁 | 你**日常在用的真实 Chrome**（复用已登录 HSC 的会话） | 另起一个干净的 chromium + `storageState` |
| 免登录 | 天然免登录，不受 token 轮换影响 | 依赖 `../ui/tests/.auth/` 里的登录态文件 |
| 适合 | 探索、取数、跑一次性流程 | 沉淀成可回归的正式用例 |

**注意**：桥接脚本进哪个账号，取决于你 Chrome 里当前登录的是谁 ——
权限不够的账号看不到目标菜单，脚本会导航失败（这不是脚本 bug）。

## 快速开始

### 方式一：桥接脚本（推荐，最省事）

```bash
cd ui/midscene
npm install
cp .env.example .env          # 填模型配置，见下方
npm run check:model           # ① 先探模型连通性（3 秒，不开浏览器）
npm run bridge                # ② 只读：进漏洞总览，统计本页待处理行数
npm run bridge:pending        # ③ 追加：筛选 状态=待处理，读全库总数
```

运行后 Chrome 会弹「Allow」→ 点允许（可勾 Remember）。
脚本连的是本机 `ws://127.0.0.1:3766`，**必须在你自己的终端跑**。

`npm run bridge:login` 是登录页的兜底脚本（含验证码视觉读取 + 失败自动刷新重试 3 次 +
DOM 硬校验）。但**登录页有验证码，本来就不适合全自动**，桥接复用会话才是正解。

### 方式二：Playwright 用例

```bash
npx playwright install chromium   # 首次需要
npm test                          # 默认有头，能看到 AI 操作
HSC_HEADLESS=1 npm test           # 无头跑（CI 用）
```

**登录态不用你操心**：`playwright.config.js` 里挂了 `globalSetup`，每次 `npm test`
之前会自动体检登录态（先拿 token 打一次鉴权接口，约 0.3 秒；有效就直接开跑）。
过期了会自动重新登录（复用 pytest 侧 `ddddocr` 那套验证码识别），刷完再验一次。

```bash
npm run auth          # 手动体检 + 按需重登
npm run auth:force    # 无条件重新登录一次
HSC_AUTH_ROLE=admin npm run auth    # 换角色账号（默认 common_admin / ceshi）
HSC_ENV=123 npm test                # 切 123 环境
```

**为什么要有这个体检**：登录态过期时，页面一打开就被踹回 `/login`，
报错却是 midscene 那句「当前页面是登录界面，不是 XX 页面」—— 完全看不出真正原因，
一整轮用例会全军覆没在登录页上。现在这类问题会在开跑前 0.3 秒内被发现并自愈。

### 方式三：YAML 流程（不想写 JS 就走这条）

YAML 里只描述**步骤**，一行选择器都不用写；`{{变量}}` + `--var` 做数据驱动。

```bash
npm run yaml:demo                              # 本地演示页，不依赖内网，立刻看到全绿
npm run check:env                              # 先体检环境（约 20 秒，判定是不是环境故障）
node scripts/run-yaml.js flows/asset_discover.yaml                       # 跑真实环境
node scripts/run-yaml.js flows/asset_discover.yaml --var EXPECT_TOTAL=87 # 传变量
```

**跑红了先别改用例，先跑 `npm run check:env`**（约 20 秒，逐页判定并给结论）。

⚠️ **但先记住一个坑：HSC 前端部署在【根路径】，地址里不要加 `/hsc-system-web`。**

```
https://192.168.124.55:26400/assetDiscover                  ✅ 正常
https://192.168.124.55:26400/hsc-system-web/assetDiscover    ❌ 500 错误页
```

带前缀时 nginx 照样返回 index.html，但 Vue Router 的 base 是 `/`，
path 变成 `/hsc-system-web/assetDiscover` → 命中未匹配路由 → 前端渲染
「500 非常抱歉，服务器出错了」。**症状极具迷惑性：手动浏览器访问完全正常、
自动化全红、接口还全是 200**（2026-09-10 实测，为此误判过一整轮"环境故障"）。
`/#/xxx` 这种 hash 路由同样已废弃，会被踢回登录页。

环境正常时，体检脚本应输出：

```
[env] 环境=55  UI=https://192.168.124.55:26400
=== 逐页结果 ===
✅ 正常页  /                智慧大屏 资产管理 … 资产概览 核心统计指标 近7天 …
✅ 正常页  /assetDiscover   智慧大屏 资产管理 … 资产发现 探测任务总数 88 …
✅ 正常页  /assetsOverview  智慧大屏 资产管理 … 资产概览 核心统计指标 近7天 …

=== 结论 ===
✅ 环境正常，页面可测。用例若仍跑红，那就是用例本身的问题。
```

退出码：`0` 正常 / `2` 页面报错（**先查 URL 前缀**，再怀疑环境）/ `3` 登录态失效（先跑 `npm run auth`）。
也可指定路由：`node scripts/check-env.js /assetsVuln /system/user`。

**为什么不用官方 `@midscene/cli`**：一是本机装不上（npm 被拦截），二是实测
`agent.runYaml()` 在这版有两个硬伤 ——

| 坑 | 现象 | 后果 |
|---|---|---|
| `javascript` 指令不生效 | 返回值不进 result，里面 **throw 也不让任务失败** | DOM 硬断言失效 → **假绿** |
| aiAssert 失败详情被吞 | 只剩一句 `Error(s) occurred in running yaml script:` | 排查全靠猜 |

`javascript` 恰恰是防假绿的关键（确定性断言靠它），所以本项目**自己实现指令分发**
（`scripts/run-yaml.js`，30 行），断言一定生效、报错一定清楚。
支持：`ai/aiAct`、`aiTap`、`aiHover`、`aiInput`、`aiKeyboardPress`、`aiScroll`、
`aiQuery/aiNumber/aiString/aiBoolean/aiAsk`、`aiAssert`、`aiWaitFor`、
`javascript`、`sleep`、`recordToReport`。

进页面后还会先做一次**环境体检**：识别到「服务器出错」错误页就等它恢复
（HSC 55 是开发环境，后端会抖），避免把环境问题算成用例失败。

## 抓接口（F12 替身）

排查页面行为、或想把某个页面背后的接口捞出来做接口测试时，不用手动翻 Network：

```bash
npm run capture -- /assetDiscover                 # 抓该页全部请求
npm run capture -- /assetDiscover --wait 10       # 多等一会（慢接口）
npm run capture -- /assetDiscover --filter asset  # 只看 URL 含 asset 的接口
npm run capture -- /assetDiscover --detail 5      # 打印前 5 条的请求体 / 响应体
npm run capture -- /assetDiscover --out disc.json # 导出 JSON（token 已脱敏）
npm run capture -- /assetDiscover --no-auth       # 未登录视角（对比用）
```

输出：Document 请求 + 接口清单（方法 / 状态 / 耗时 / 大小）+ 页面状态判定 + 控制台报错。
退出码 `0` 正常 / `2` 环境不可用（打不开或错误页）/ `1` 脚本异常。
导出文件落在 `midscene_run/capture/`（已 gitignore，token 脱敏）。

**两个典型用途**：① 页面表现不对时先抓一遍，看是哪个接口没返回、返回了什么；
② 把某页接口清单导出，照着写接口测试用例。

## 新增路由必须先核对菜单树（别信文档和用例备注）

深链接是这里最省事的一招，但**路径必须从真实菜单树里取**，不能靠猜：

```bash
# 用当前登录态拉一次菜单路由树，找真实 path
curl -sk -H "X-Access-Token: <token>" -H "Authorization: <token>" \
  "https://192.168.124.55:26400/hsc-system-api/system/auth/routes"
```

实测踩坑：手工用例备注写的是 `/AssetDiscovery`，但菜单树里真实路由是
**`assetDiscover`**（小写 d）；按错路径打开只有一个「500 服务器出错了」错误页。

## 模型配置

当前用**智谱 GLM 视觉模型**（国产，`glm-v` 家族）：

```
MIDSCENE_MODEL_BASE_URL="https://open.bigmodel.cn/api/paas/v4"
MIDSCENE_MODEL_API_KEY="<智谱 key，形如 xxx.yyy>"
MIDSCENE_MODEL_NAME="glm-4.6v"
MIDSCENE_MODEL_FAMILY="glm-v"        # 智谱必须用 FAMILY，不存在 MIDSCENE_USE_GLM_VL
```

排错对照：

| 报错 | 含义 |
|---|---|
| `401 令牌已过期或验证不正确` | key 无效（最常见：占位符没替换、改错文件） |
| `400 Arrearage` | 阿里云账户欠费 |
| `Replanned 20 times` | 定位失败反复重规划 → 是页面结构/提示词问题，不是 key 问题 |
| `403 Free quota exhausted` | 免费额度用尽 |

**先跑 `npm run check:model`**，3 秒分清是 key 问题、模型名问题还是网络问题，
不用每次都白等一整轮浏览器自动化。

## 合规说明

界面截图会发送到**公有云多模态模型**（当前为智谱）。HSC 是医院安全驾驶舱，
本项目定位为**内部测试环境的 PoC**；若要用于正式/生产环境评估，需先按公司
数据出境要求评估，或改用本地部署的视觉模型（`OPENAI_BASE_URL` 指向 localhost）。

另：登录页验证码是**反自动化**设计，测试用途下不应做打码对抗；
正规做法是让开发在测试环境关闭验证码或提供万能码。

## 文件说明

| 文件 | 作用 |
|---|---|
| `bridge_hsc.mjs` | **主力**。DOM 优先 + AI 兜底，进漏洞总览统计待处理；`--pending` 读全库总数 |
| `bridge_login.mjs` | 登录页兜底（验证码视觉读取 + 重试 + DOM 硬校验）；凭证读 `.env`，脚本内无明文 |
| `check_model.mjs` | 模型连通性探针：打印实际生效配置 + 发一次最小视觉请求 |
| `scripts/hsc-env.js` | 环境/地址/登录态文件的唯一出处，避免多处写死漂移 |
| `scripts/ensure_auth.js` | **登录态体检 + 自动重登**（`globalSetup`，也可 `npm run auth` 单独跑） |
| `scripts/check-env.js` | **环境体检**（`npm run check:env`）：判定"用例跑红"是环境故障还是用例问题，退出码 0/2/3 |
| `scripts/capture-api.js` | **抓接口（F12 替身）**（`npm run capture -- /路径`）：抓页面全部请求，可导出 JSON |
| `scripts/run-yaml.js` | **YAML 流程执行器**（自实现指令分发：`javascript` 硬断言确定生效） |
| `flows/*.yaml` | YAML 用例：只写步骤不写选择器，`{{变量}}` + `--var` 数据驱动 |
| `demo/demo_asset_discover.html` | 本地演示页（离线可跑，用来验证链路本身是否正常） |
| `playwright.config.js` | 复用 pytest 的 storage_state；自签证书 `ignoreHTTPSErrors` |
| `tests/asset_dashboard.spec.js` | 资产发现页统计卡片 + 趋势图浮层（SCAN-002/003/004），DOM 主力 + AI 交叉验证 |
| `tests/disposal.spec.js` | 处置面板派单 / 提交复核 样例（含防假绿断言） |
| `templates/asset_new_task.param.spec.js` | 参数化用例骨架：一个流程 × N 行数据（放在 templates/ 不参与执行） |
| `.env.example` | 模型配置模板（`.env` 已在 .gitignore 中） |
| `midscene_run/` | 运行产物：HTML 报告 + 日志（已 gitignore） |

**每次跑完的 HTML 报告**在 `midscene_run/report/`，打开可回看 AI 每一步的
截图和它实际点击的位置 —— 觉得"没做对却打勾"时，点开看框落在哪，一秒定位。

**排错取证**：`midscene_run/log/ai-call.log` 里有模型每次调用的原始输入输出
（含 `<observation>` 原文）。判断是不是假绿，读这个比反复重跑快得多：

```bash
sed -n '/2026-09-10T15:1[6-9]/,$p' midscene_run/log/ai-call.log
```
