# HSC 智慧医院网络安全驾驶舱 —— 自动化测试框架

接口自动化（pytest + requests + Allure + YAML 数据驱动）与 UI 自动化（Midscene 视觉驱动 + Playwright）
共用一个仓库、一套环境开关。**55（开发）/ 123（测试）双环境一键切换**，覆盖系统管理 /
资产管理 / 脆弱性管理 / 合规运营等模块。

> 目录名 `hsc_auto` 不带环境标识——它同时跑 55 和 123，当前环境由项目根 `.env` 的 `HSC_ENV` 决定。

## 一、三十秒看懂全局（目录地图）

```
hsc_auto/
│  ──── 接口自动化（成熟，主力） ────
├── config.py                  # 唯一环境开关 + 双头认证 + 角色 token 文件 + ENV_IDS 环境化数据
├── conftest.py                # 全局 fixture（temp_user/temp_dept... 建完自动清理）
├── core/                      # base.py 请求封装、断言、重试；utils_sign.py x-sign 签名
├── system_management/         # 用户/部门/角色/菜单/登录（utils_xxx 封装层 + test_xxx + 数据驱动版）
├── asset_management/          # 资产管理
├── vuln_management/           # 脆弱性管理（主机/网站/弱口令/基线/系统漏洞）
├── compliance_operations/     # 合规运营
├── data/                      # YAML 测试数据（数据驱动与逻辑分离）
│
│  ──── UI 自动化（统一入口 ui/，与接口框架分区；内部三层各司其职，见「三、UI 自动化」） ────
├── ui/
│   ├── py/                    # ★ 新用例一律写这里（Python/pytest + AI 流程驱动层 ai_flow.py）
│   ├── midscene/              #   JS 执行内核（flows/ YAML 用例、登录态/环境体检、抓包工具，npm 工程）
│   └── tests/                 #   存量 Playwright 选择器 POM（工单 34 条）+ 登录基建（login_page、.auth）
│
│  ──── 支撑与产物 ────
├── manual_testcases/ bugs/ tools/   # 手工用例、缺陷报告、辅助脚本
├── reports/ logs/             # Allure 结果与日志（gitignore，随时可再生）
├── .github/workflows/         # CI（质量门禁 + 手动触发的内网 job）
├── .env                       # ★ 本机机密与开关（不入库）：HSC_ENV、各角色密码、token 相关
└── .secrets/                  # 运行时凭证（token_*.txt / auth_headers_*.json，gitignore，export_token.py 生成）
```

**两个 .env 别搞混**（高频踩坑）：

| 文件 | 管什么 |
|---|---|
| `hsc_auto/.env`（项目根） | `HSC_ENV=55/123` 环境开关、各 UI 角色密码（`HSC_UI_*_PASSWORD`）、接口账号 |
| `hsc_auto/ui/midscene/.env` | **Midscene 模型配置**（BASE_URL/KEY/NAME/FAMILY）、bridge 登录凭证 |

改 UI 用例行为动第一个；换 AI 模型动第二个（改完跑 `cd ui/midscene && npm run check:model` 验证）。

> **按业务模块查用例？看 [`MODULES.md`](MODULES.md)** —— 8 个模块 × 接口/UI/手工三堆的总索引（含覆盖度与缺口）。

## 二、接口自动化

### 环境准备
```bash
cd ~/hsc_auto
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
```

### 认证（不再手工 F12）
token 由 UI 登录态自动导出（链路：浏览器登录 → `export_token.py` 拦截真实请求头 →
`.secrets/auth_headers_{ENV}_{role}.json` → `config.get_headers(role)` 动态读取）：
```bash
./venv/bin/python ui/tests/export_token.py                 # 默认角色
./venv/bin/python ui/tests/export_token.py --role admin    # 指定角色（系统管理模块需要）
```
> HSC 认证靠 `Authorization` + `X-Access-Token` 双头（同一 JWT），与会话 Cookie 无关；
> token 短时会轮换，导出后尽快在同一轮里用掉。

### 运行
```bash
pytest                                        # 全部接口用例（testpaths 只含 4 个接口模块）
pytest system_management/test_user.py -v      # 单模块
pytest system_management/test_user_data_driven.py -v   # 数据驱动
pytest -m smoke                               # 冒烟标记
allure serve reports/allure-results           # 看报告
```

### 环境切换与数据隔离
```bash
export HSC_ENV=55    # 或 123；也写死在项目根 .env（当前默认 123）
```
- 跨环境不同的业务 ID 集中在 `config.py::ENV_IDS`，YAML 里用 `__PARENT_DEPT_ID__` 占位符，加载时自动替换；
- 断言约定：HSC HTTP 恒 200，业务结果看 JSON 的 `code/success`（用 `assert_success`/`assert_business_fail`）。

### x-sign 签名
系统管理写接口需 `x-sign`（防篡改）。已在 `core` 请求层按前端算法自动计算（
`MD5(按key升序的{query+params+data}剔除_t + SALT)` 大写），用例无感。盐值与算法见
`system_management/utils_sign.py` 与提交历史。55 环境暂不强制校验，其他环境会。

### conftest 提供的 fixture（建完自动清理）

| Fixture | 作用 | | Fixture | 作用 |
|---|---|---|---|---|
| `temp_user` | 临时用户 | | `temp_role` | 临时角色（签名失败返回 None） |
| `temp_user_with_role` | 带角色临时用户 | | `temp_menu` / `temp_menu_page` | 目录/页面菜单 |
| `temp_dept` / `temp_child_dept` | 部门/下级部门 | | `headers` / `token` / `base_url` | session 级配置 |

## 三、UI 自动化（三层架构 —— 为什么有三个目录）

```
你写用例的层        ui/py/        Python + pytest：用例设计、数据驱动、断言、Allure
      │ run_flow("xxx", vars={...}) 经 subprocess 调 JS 内核（跑前自动体检登录态）
流程描述层          ui/midscene/flows/*.yaml   自然语言写"点哪几下"，零选择器
      │
执行内核层          ui/midscene/  Playwright + Midscene(视觉模型) + DOM 硬断言 + 各种体检工具
```

另有一层**不属于 Midscene 体系**的存量：`ui/tests/` 是早期纯选择器的 Playwright POM 用例
（工单流程 34 条，`workorder_page.py` 那套），继续可跑、不再新增；它的**基础设施是共用的**：
登录页对象、验证码识别（2026-09 起视觉模型优先 + ddddocr 兜底）、storage_state 登录态、
`export_token.py` 都住在 ui/tests，被 ui/py/ui/midscene 复用。

**一句话：新 UI 用例写 `ui/py/`；`ui/midscene/` 里只加 YAML 流程和内核工具；`ui/tests/` 维持存量 + 提供登录基建。**

### 跑法
```bash
cd ~/hsc_auto
./venv/bin/pytest ui/py -v                          # 全部 UI 用例（真实环境，需内网可达）
./venv/bin/pytest ui/py/test_flow_driver.py -v      # 离线自测（不碰内网，CI 冒烟用）
./venv/bin/pytest ui/py/test_vuln_overview.py -v    # 单模块

# 内核直跑（调试 YAML 用）
cd ui/midscene
npm run check:model      # 模型连通性 3 秒定性
npm run check:env        # 环境体检：用例跑红先分清"环境问题"还是"用例问题"
npm run auth             # 登录态体检 + 过期自动重登
npm run capture -- /assetDiscover   # 抓页面接口（F12 替身）
node scripts/run-yaml.js flows/vuln_overview.yaml --var EXPECT_TOTAL=2583
```

### 方法论（详见 `ui/midscene/README.md` 与学习笔记《Midscene UI 自动化》）
- **DOM 干确定的事，AI 只兜底 + 交叉验证**：读数/计数/激活态用 `javascript` DOM 硬断言（0 成本、
  精确），视觉模型只负责"人眼才看得懂"的部分——实测同页 DOM 数到 27 行待处理、AI 只看到 4 行，
  断言权永远归 DOM。
- **防假绿三件套**：断言钉本页专有文案（落错页立刻红）、成功操作后刷新回查（不轻信 toast）、
  每流程第 0 步页面体检（登录守卫 + 错误页识别）。
- **123 会话很短**（实测约 10 分钟且疑有单点互踢）：`run_flow` 跑前自动体检登录态并自愈，
  不要手工长期复用旧 state 文件。
- 路由以菜单树接口为准（`/hsc-system-api/system/auth/routes`），前端在根路径、**别加 `/hsc-system-web` 前缀**。

### 登录与验证码（ui/tests 基建，被全体系复用）
- 视觉大模型优先（复用 `ui/midscene/.env` 的模型，实测 qwen3.8-max 对 123 弧线扭曲码稳定），
  ddddocr 兜底：`ui/tests/utils_captcha.py`。2026-09-15 曾因 ddddocr 对 123 验证码 12 连败，
  教训与诊断脚本见 `ui/tests/diagnose_login_once.py`（抓登录接口响应原文定性，别猜）。
- 各角色登录态：`ui/tests/.auth/state_{ENV}_{role}.json`（gitignore）。

### 模型配置（ui/midscene/.env）
当前：公司 token-plan 网关 OpenAI 兼容入口 + `qwen3.8-max`（`MIDSCENE_MODEL_FAMILY=qwen3`）。
```bash
MIDSCENE_MODEL_BASE_URL="https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
MIDSCENE_MODEL_API_KEY="sk-..."
MIDSCENE_MODEL_NAME="qwen3.8-max"
MIDSCENE_MODEL_FAMILY="qwen3"
```
> 注意：该网关另有 `/apps/anthropic` 入口（Anthropic 协议），Midscene 用不了，别配错。
> Chrome 插件的 Config 面板与 `.env` 是**两套独立配置**，改模型要各改各的。
> 备用（已注释在 .env）：智谱 GLM-4.6V。调试嫌慢可临时换网关里的 `qwen3.8-flash`。

## 四、CI/CD

`.github/workflows/pytest.yml` 两个 job：
- **push 触发（job1）**：装依赖 → 全量跑接口 pytest → 上传 allure-results/报告/日志。
  注意 GitHub 托管 Runner **访问不到公司内网**，此 job 的用例通过率不代表真实结果，
  它的价值是验证"收集得起来、跑测流程与报告管线不坏"。
- **UI E2E（job2，仅手动 `Run workflow`）**：内网可达环境下跑 `pytest ui/tests`（存量选择器用例）。
- 真实回归（接口 + `ui/py` 视觉用例）目前主要**本地跑**（公司 55/123 环境不允许 CI 批量创建类操作）。
  可自动化的部分（`ui/py/test_flow_driver.py` 离线自测）后续可挂进 job1。

## 五、常见故障速查

| 症状 | 处置 |
|---|---|
| UI 用例挂在登录页 | `cd ui/midscene && npm run auth`（123 会话 ~10min 一换）；ui/py 会自动体检，不用管 |
| 登录 12 连败、页面"无提示" | 十有八九验证码识别失效 → `./venv/bin/python ui/tests/diagnose_login_once.py` 看接口原文 |
| 用例跑红但不知道谁的锅 | 先 `npm run check:env`（环境问题）再看 `midscene_run/report/`（AI 框选落点）|
| 模型 401 / Invalid URL | key 或地址被引号/注释污染，对照本文「模型配置」四行 |
| 接口用例 401 | token 过期 → `export_token.py` 重导（按角色 `--role`） |
| 数据驱动断言"总数不符" | 环境业务数据本身变了：先拿实际值核对，是 bug 提 bug，是数据漂移改期望值 |

## 六、数据清理
```bash
./venv/bin/python system_management/cleanup_test_data.py   # 清理接口测试脏数据
```
UI 用例产生的数据按"接口造数、接口清理"原则处理（见 `ui/py/test_asset_discover.py` 注释）。
