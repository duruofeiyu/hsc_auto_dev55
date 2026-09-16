# ui/tests —— 存量选择器用例 + 全套登录基建

> 2026-09-15 定位声明（当时框架"看不懂"的根源之一就是这里没说清楚）：
> 本目录有**双重身份**，别和 `ui/py`/`ui/midscene` 混为一谈。

## 身份一：存量 UI 用例（选择器 POM 风格，维持可跑、不再新增）

工单流程等 34 条 Playwright 选择器用例（`test_workorder_flow.py`、`test_disposal_modes.py`、
`workorder_page.py` 那套）。新写的 UI 用例请去 **`../ui/py/`**（Python 断言 + Midscene 视觉定位）。

```bash
cd ~/hsc_auto && ./venv/bin/pytest ui/tests -v -s          # 跑存量用例
./venv/bin/pytest ui/tests/test_login.py -v -s             # 只跑登录冒烟（验证验证码链路）
```

## 身份二：登录基建（被 ui/py / ui/midscene / 接口 token 导出全体系复用，是"活的地基"）

| 文件 | 作用 | 谁在用 |
|---|---|---|
| `login_page.py` | 登录页对象（验证码重试、state_path 保存） | refresh_state、存量用例 |
| `utils_captcha.py` | 验证码识别：**视觉大模型优先**（复用 ui/midscene/.env 模型），ddddocr 兜底 | login_page |
| `refresh_state.py` | 强制刷新某角色登录态 storage_state | ui/midscene/scripts/ensure_auth.js（npm run auth） |
| `export_token.py` | UI 登录态 → 接口 token（拦真实请求头） | 接口框架 get_headers |
| `conftest.py` / `base_page.py` | page fixture / 页面对象基类 | 本目录用例 |
| `.auth/state_{ENV}_{role}.json` | 各角色登录态（gitignore） | 全 UI 体系 |
| `diagnose_login_once.py` | 登录异常诊断：抓登录接口响应原文定性 | 人工排查 |

## 关键经验（别再踩）

- **123 会话 ~10 分钟即失效**（JWT 无 exp、服务端控制，疑有单点互踢）。别长期复用旧 state 文件；
  `run_flow`/`npm run auth` 都有自动体检自愈。
- **ddddocr 对 123 弧线扭曲验证码识别率不可用**（曾 12 连败、服务器只回"验证码错误"而页面无提示），
  所以识别升级为视觉模型优先。登录异常先跑 `diagnose_login_once.py`，看接口原文，别猜。
- **HSC 认证与会话 Cookie 无关**（Cookie 只有百度统计），token 在浏览器实际发出的
  `Authorization`/`X-Access-Token` 双头里；localStorage 顶层直接读会拿到无效令牌。
- **登录失败 ≠ 有提示**：HSC 登录失败前端 toast 经常抓不到（`_read_error` 为空），
  判断真实原因以接口响应为准。
