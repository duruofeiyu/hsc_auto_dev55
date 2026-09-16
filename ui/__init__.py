"""UI 自动化统一入口（与接口自动化框架分区）。

py/       新用例层（pytest + Midscene 视觉，你写用例的地方）
midscene/ JS 执行内核（flows/、run-yaml、登录态/环境体检、npm 工程）
tests/    存量 Playwright 选择器用例 + 登录基建（login_page/.auth）
"""
