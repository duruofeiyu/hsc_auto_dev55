# HSC UI 自动化 PoC —— midscene.js

用**自然语言 + 视觉**写 UI 自动化，代码里不再有会烂掉的 CSS 选择器。
与现有 `pytest` 接口框架**并存互补**，不互相替代。

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
| 免登录 | 天然免登录，不受 token 轮换影响 | 依赖 `../ui_tests/.auth/` 里的登录态文件 |
| 适合 | 探索、取数、跑一次性流程 | 沉淀成可回归的正式用例 |

**注意**：桥接脚本进哪个账号，取决于你 Chrome 里当前登录的是谁 ——
权限不够的账号看不到目标菜单，脚本会导航失败（这不是脚本 bug）。

## 快速开始

### 方式一：桥接脚本（推荐，最省事）

```bash
cd ui_midscene
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

前置：pytest 框架的登录态已生成（跑过 pytest UI 用例就会在
`../ui_tests/.auth/` 下产出 `state_55_common_admin.json`）。
切 123 环境设 `HSC_ENV=123`。

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
| `playwright.config.js` | 复用 pytest 的 storage_state；自签证书 `ignoreHTTPSErrors` |
| `tests/disposal.spec.js` | 处置面板派单 / 提交复核 样例（含防假绿断言） |
| `.env.example` | 模型配置模板（`.env` 已在 .gitignore 中） |
| `midscene_run/` | 运行产物：HTML 报告 + 日志（已 gitignore） |

**每次跑完的 HTML 报告**在 `midscene_run/report/`，打开可回看 AI 每一步的
截图和它实际点击的位置 —— 觉得"没做对却打勾"时，点开看框落在哪，一秒定位。

**排错取证**：`midscene_run/log/ai-call.log` 里有模型每次调用的原始输入输出
（含 `<observation>` 原文）。判断是不是假绿，读这个比反复重跑快得多：

```bash
sed -n '/2026-09-10T15:1[6-9]/,$p' midscene_run/log/ai-call.log
```
