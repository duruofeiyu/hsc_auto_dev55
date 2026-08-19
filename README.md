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

## 注意事项

1. **Token 过期**：Token 有效期有限，过期后需重新从浏览器抓包更新 `token.txt`
2. **角色签名**：角色创建/编辑/删除接口需要 x-sign 签名，当前未实现签名算法，相关用例会 skip
3. **测试数据清理**：运行 `python system_management/cleanup_test_data.py` 可清理所有测试数据
4. **环境隔离**：当前仅支持 55 开发环境，多环境切换待实现
5. **CI 环境限制**：GitHub Actions 虚拟机无法访问内网 55 环境，CI 仅能验证用例收集和框架运行流程
