"""合规运营 + 系统管理 只读冒烟（各 1 页）。

2026-09-16 首轮"取证-收紧"两轮式产出（首轮 loose flow 采真实文本 → 二轮钉硬断言）：
  合规预览  /ComplianceOverview（注意大写 C！菜单树实拉，猜 camelCase 必踩 500）
  模板中心  /template（实测：菜单树子节点 path 平挂根级，/system/template 是 500 错误页）
两页都在 common_admin 权限内（用户/部门管理在 admin/secadmin 下，勿用本角色测）。

跑法：./venv/bin/pytest ui/py/test_smoke_compliance_system.py -v
"""
import allure

from ui.py.ai_flow import run_flow


@allure.epic("HSC 智慧医院网络安全驾驶舱")
@allure.feature("合规运营")
class TestComplianceSmoke:
    @allure.title("合规预览页渲染且任务统计自洽")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_compliance_overview(self):
        r = run_flow("compliance_overview")
        assert not r.task("页面健康检查")["failed"], "页面体检失败（环境/登录态）"
        t = r.task("数据自洽")
        assert not t["failed"], f"合规预览断言失败：{t['steps']}"
        assert "OK" in t["results"].get("self_consistency", "")


@allure.epic("HSC 智慧医院网络安全驾驶舱")
@allure.feature("系统管理")
class TestSystemTemplateSmoke:
    @allure.title("模板中心 8 子页签齐全且表格列头正确")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_template_center(self):
        r = run_flow("system_template")
        assert not r.task("页面健康检查")["failed"], "页面体检失败（环境/登录态）"
        t = r.task("结构硬断言")
        assert not t["failed"], f"模板中心断言失败（前端可能改版）：{t['steps']}"
        assert "OK" in t["results"].get("structure_check", "")
