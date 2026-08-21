# HSC 55 开发环境 - 接口自动化测试框架

基于 pytest + requests + Allure 的接口自动化测试框架，覆盖 HSC 系统管理模块。

## 环境准备

### 1. Python 版本
- Python 3.8+

### 2. 创建虚拟环境
```bash
cd /Users/a1-6/hsc_auto_dev55
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 配置 Token
从浏览器 F12 抓包获取 Token，粘贴到 `token.txt` 文件：
```bash
echo "你的token" > token.txt
```
> 也可在跑完 UI 登录后，用 `./venv/bin/python ui_tests/export_token.py` 自动从登录态导出（详见下方 UI 章节），免去手工抓包。

## 运行测试

### 运行全部用例
```bash
pytest
```

### 运行指定模块
```bash
pytest system_management/test_user.py
pytest system_management/test_dept.py
pytest system_management/test_role.py
pytest system_management/test_menu.py
pytest system_management/test_login.py
```

### 运行数据驱动用例
```bash
pytest system_management/test_user_data_driven.py
pytest system_management/test_dept_data_driven.py
pytest system_management/test_role_data_driven.py
pytest system_management/test_menu_data_driven.py
pytest system_management/test_login_data_driven.py
```

### 运行冒烟测试
```bash
pytest -m smoke
```

### 生成 Allure 报告
```bash
# 先运行测试
pytest

# 生成并打开报告
allure serve reports/allure-results
# 或生成静态报告
allure generate reports/allure-results -o reports/allure-report --clean
```

### 运行指定优先级
```bash
pytest -m p1    # 优先级1
pytest -m p2    # 优先级2
```

## 目录结构

```
hsc_auto_dev55/
├── config.py                  # 全局配置（BASE_URL、Token 加载）
├── conftest.py                # pytest 全局 fixture
├── logger.py                  # 日志模块
├── pytest.ini                 # pytest 配置
├── requirements.txt           # 依赖列表
├── .gitignore                 # Git 忽略规则
├── .pre-commit-config.yaml    # pre-commit 配置
├── pyproject.toml             # 项目配置
├── token.txt                  # Token 文件（不提交到 Git）
│
├── data/                      # 数据驱动测试数据
│   ├── user_data.yaml         # 用户模块测试数据
│   ├── dept_data.yaml         # 部门模块测试数据
│   ├── role_data.yaml         # 角色模块测试数据
│   ├── menu_data.yaml         # 菜单模块测试数据
│   └── login_data.yaml        # 登录模块测试数据
│
├── system_management/         # 系统管理模块
│   ├── base.py                # 公共基础模块（请求封装、断言）
│   ├── utils_user.py          # 用户管理工具层
│   ├── utils_dept.py          # 部门管理工具层
│   ├── utils_role.py          # 角色管理工具层
│   ├── utils_menu.py          # 菜单管理工具层
│   ├── utils_login.py         # 登录管理工具层
│   ├── test_user.py           # 用户模块测试（手工版）
│   ├── test_dept.py           # 部门模块测试（手工版）
│   ├── test_role.py           # 角色模块测试（手工版）
│   ├── test_menu.py           # 菜单模块测试（手工版）
│   ├── test_login.py          # 登录模块测试（手工版）
│   ├── test_user_data_driven.py    # 用户模块测试（数据驱动版）
│   ├── test_dept_data_driven.py    # 部门模块测试（数据驱动版）
│   ├── test_role_data_driven.py    # 角色模块测试（数据驱动版）
│   ├── test_menu_data_driven.py    # 菜单模块测试（数据驱动版）
│   ├── test_login_data_driven.py   # 登录模块测试（数据驱动版）
│   ├── test_menu_allure_advanced.py # Allure 进阶演示
│   ├── cleanup_test_data.py    # 测试数据清理脚本
│   └── generate_manual_testcases.py # 手工测试用例生成
│
├── reports/                   # 测试报告
│   └── allure-results/        # Allure 原始数据
│
└── logs/                      # 日志文件
    └── test_YYYYMMDD.log      # 按日期命名的日志
```

## 模块说明

### 公共基础模块 (base.py)
- `get_headers()` — 构建请求头（动态读取 token）
- `assert_success()` — 断言业务成功
- `assert_business_fail()` — 断言业务失败
- `request_wrapper()` — 统一请求封装（含 timeout、日志、异常处理）
- `retry_on_failure()` — 失败重试装饰器

### conftest.py 提供的 fixture

| Fixture | 作用 | 自动清理 |
|---------|------|---------|
| `temp_user` | 创建临时用户 | ✅ |
| `temp_user_with_role` | 创建带角色的临时用户 | ✅ |
| `temp_dept` | 创建临时部门 | ✅ |
| `temp_child_dept` | 创建临时下级部门 | ✅ |
| `temp_role` | 创建临时角色（签名失败返回 None） | ✅ |
| `temp_menu` | 创建临时目录菜单 | ✅ |
| `temp_menu_page` | 创建临时页面菜单 | ✅ |
| `headers` | 获取请求头（session 级别） | - |
| `token` | 获取 token（session 级别） | - |
| `base_url` | 获取 BASE_URL（session 级别） | - |

## 数据驱动

测试数据与测试逻辑分离，通过 YAML 文件管理测试数据。

**运行数据驱动用例：**
```bash
pytest system_management/test_user_data_driven.py -v
```

**YAML 数据结构示例：**
```yaml
test_create_user:
  - name: "正常新增用户"
    input:
      userAccount: "test_001"
      userName: "测试用户"
    expected:
      success: true
      code: 200
```

## CI/CD 持续集成

本项目已配置 GitHub Actions，每次 push 到 main 分支自动触发测试。

### 流水线功能

- 自动安装依赖
- 自动运行 pytest
- 自动生成 Allure 测试报告
- 测试日志和报告自动上传（保留 7 天）

### 查看 CI 运行结果

访问 GitHub 仓库 → Actions 标签页，可查看每次 push 的：

- 用例执行结果（通过/失败数量）
- 完整 pytest 输出日志
- Allure 测试报告

### 本地模拟 CI 环境

由于 55 环境为内网 IP，GitHub Actions 虚拟机无法直接访问接口，CI 运行时接口请求会失败。

本地验证 CI 流程：

```bash
# 安装 allure（macOS）
brew install allure

# 本地运行测试
pytest

# 生成报告
allure serve reports/allure-results
```

## UI 自动化测试（Playwright）

除接口自动化外，本框架也支持 UI 自动化（选修方向），目录为 `ui_tests/`。

### 目录结构

```
ui_tests/
├── conftest.py             # 自定义 page fixture（headless chromium，忽略 https 错误）
├── base_page.py            # 页面对象基类（通用导航 / 断言）
├── login_page.py           # 登录页对象（含验证码 OCR 识别）
├── utils_captcha.py        # 验证码识别封装（ddddocr）
├── test_login.py           # 登录冒烟用例
├── export_token.py         # UI 登录态 → 接口 Token 自动导出工具
└── test_demo.py            # Playwright 本地 demo（访问 test.html）
```

### 安装依赖

```bash
cd /Users/a1-6/hsc_auto_dev55
./venv/bin/pip install playwright ddddocr
```

> 浏览器已缓存（位于 `~/Library/Caches/ms-playwright`），无需再执行 `playwright install`。
>
> ⚠️ **zsh 行内注释坑**：macOS 默认 zsh 在交互模式下不会把行内 `#` 当作注释。若在同一行命令后写 `# 说明`，`#` 及其后的中文会被当成参数传给 pip，报 `Invalid requirement: '#'`。请使用项目 venv 路径、把注释单独成行，或直接不写注释。

### 配置账号密码

UI 登录需要 55 环境账号的**真实明文密码**（接口侧用的是加密串，UI 登录不能用）：

```bash
export HSC_UI_USER=chenyh
export HSC_UI_PASSWORD='你的55环境真实明文密码'   # 必填，无默认值
```

> 密码仅存在于环境变量，不会写入代码或入库；未设置时用例会立即报错提示。

### 登录验证码（ddddocr 本地 OCR）

HSC 登录页有图形验证码。UI 登录用例用 **ddddocr 本地离线 OCR** 自动识别：

- `ui_tests/utils_captcha.py` 封装识别逻辑（未装 ddddocr 会给出清晰安装提示）。
- `LoginPage.login_with_captcha` 读取验证码图片 base64 → 识别 → 填入 → 提交，识别错误**点击验证码图片刷新**后重试（默认 12 次，并通过 4~5 位字母数字格式校验）。
- **会话复用（storage_state）**：首次登录成功后把会话存到 `ui_tests/.auth/state.json`，后续业务用例用 `authed_page` fixture 直接带状态进入，**不再重复识别验证码**。会话过期时用 `HSC_FORCE_LOGIN=1` 强制重登。

### 运行 UI 测试

```bash
./venv/bin/pytest ui_tests -v -s
./venv/bin/pytest ui_tests/test_login.py -v -s          # 只跑登录冒烟（含验证码识别）
HSC_FORCE_LOGIN=1 ./venv/bin/pytest ui_tests/test_login.py -v -s   # 强制重新登录
```

- 第一条跑全部 UI 用例；第二条只跑登录冒烟（验证验证码识别链路）。
- 用例失败时，`ui_tests/conftest.py` 会自动截图并附加到 Allure 报告（与接口侧「失败有迹可循」一致）。

查看 UI 的 Allure 报告：

```bash
allure serve reports/allure-results
```

### UI 登录态 → 接口 Token 自动导出（export_token.py）

UI 登录成功后，会话已存到 `ui_tests/.auth/state.json`。`export_token.py` 用 Playwright 加载该登录态、在浏览器里真实触发一次 API 请求，**拦截浏览器发出的真实 `Authorization` 和 `X-Access-Token` 两个头**并写入项目根，**免去手工 F12 抓包粘贴**：

```bash
# 前提：先跑过 UI 登录冒烟，生成登录态
./venv/bin/pytest ui_tests/test_login.py -v -s
# 导出认证信息（Mac 用 python3 或 ./venv/bin/python，没有 python 命令）
./venv/bin/python ui_tests/export_token.py
```

- 采用**实时拦截请求头**方式：HSC 的 token 不在 localStorage 顶层（实测直接读 localStorage 会得到无效令牌、调接口 401），只有浏览器实际发出的 `Authorization` 头才是服务器认可的 token，故直接拦截最可靠。
- **同时抓取 `Authorization` 与 `X-Access-Token`**：HSC 接口认证同时验这两个头（值同 JWT）。脚本一并抓取写入 `auth_headers.json`，`config.get_headers()` 优先读取 `auth_headers.json`、不存在时回退到 `token.txt`。
- **不依赖 Cookie**：HSC 浏览器会话 cookie 里只有 `HMACCOUNT`/`Hm_lvt` 等统计类 cookie，**无任何认证 cookie**（已用 Playwright `context.cookies()` 实测确认）。`base.py` 的裸 `requests.request` 不带 Cookie 也不影响认证，故无需附加 Cookie 头（v3 曾错误地附加 Cookie，沙箱对照实验证明 Cookie 与认证无关）。
- 依赖 Playwright（与登录冒烟同一套），需能访问 55 内网；token 原样写入（不篡改前缀）。
- `auth_headers.json` / `token.txt` 已纳入 `.gitignore`，不会入库。
- 若拦截不到（登录态失效），脚本会提示重新跑 UI 登录冒烟后再试。
- 导出后接口用例 `get_headers()` 自动读取，实现「一次登录，两边通用」。

### 设计说明

- 采用 **Page Object 模式**：页面交互封装在 `base_page.py` / `login_page.py` / `utils_captcha.py` 中，用例只关心业务步骤与断言（与接口侧 `base.py` + `utils_*.py` 风格一致）。
- 账号密码从环境变量读取（`HSC_UI_USER` / `HSC_UI_PASSWORD`）。账号默认 `chenyh`，**密码无默认值、必须显式设置**（UI 登录需要 55 环境 chenyh 的真实明文密码，不能用接口侧的加密串；未设置时用例会立即报错提示）。不硬编码。
- 登录验证码用 **ddddocr 本地 OCR** 自动识别（`login_with_captcha`），并通过 **storage_state 会话复用**（`authed_page` fixture）避免每条用例重复过验证码。

### CI 中的 UI 测试

接口主流程（`.github/workflows/pytest.yml` 的 `test` job）只跑 `system_management`，保持绿色、不依赖内网可达性。

UI 测试单独放在 `ui-e2e` job，**仅手动触发**（`Actions` 页面 → `Run workflow`）。原因：UI 目标环境为内网 `192.168.124.55`，GitHub 托管 Runner 无法访问，仅在具备可达环境（自托管 Runner / VPN / 本地 `act`）时运行。该 job 会自动安装 Playwright 浏览器（`playwright install --with-deps chromium`）并执行 `pytest ui_tests`，产物含 `ui-allure-results`。

## 注意事项

1. **Token 过期**：Token 有效期有限，过期后需重新跑 UI 登录冒烟后执行 `./venv/bin/python ui_tests/export_token.py` 自动导出（无需手工抓包）
2. **角色签名**：角色创建/编辑/删除接口需要 x-sign 签名，当前未实现签名算法，相关用例会 skip
3. **测试数据清理**：运行 `python system_management/cleanup_test_data.py` 可清理所有测试数据
4. **环境隔离**：当前仅支持 55 开发环境，多环境切换待实现
5. **CI 环境限制**：GitHub Actions 虚拟机无法访问内网 55 环境，CI 仅能验证用例收集和框架运行流程
