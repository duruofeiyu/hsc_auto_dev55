"""多角色权限 UI 用例 —— 菜单可见性 + 深链接越权拦截（UI 层独有价值）。

为什么属于 UI 层：菜单/入口可见性与前端路由守卫都是纯前端行为，接口层验不了；
权限配错是安全类产品的红线（该隐的没隐 = 越权入口暴露）。

数据（2026-09-16 实测，均从真实界面/路由接口取证）：
- 路径实锤（admin 点菜单验证）：组织权限 = /organization，页面含「用户管理/部门管理」页签。
  路由树：系统管理 → 组织权限(organization) → 用户管理(user)/部门管理(dept)。
- admin（系统管理员）：路由表【含】organization；侧边栏含「组织权限」入口；直达正常渲染。
- common_admin（普通管理员，账号 ceshi）：路由表【不含】organization；无入口；
  直达被拦（形态 a：停在 /organization 渲染通用「500 服务器出错」页；
  形态 b：被重定向到默认页——两种形态都出现过，断言按"页面不可用"语义写）。

★ 如何确定性区分「权限拦截」与「路径写错」（两者页面长得一模一样，都是通用 500 页）：
  判据 = 该角色的【授权路由表】（/system/auth/routes）里有没有这个 path：
    - 表里有 + 页面可用   → 正常
    - 表里有 + 页面不可用 → 路径/前端问题（对照历史 /hsc-system-web 前缀事故排查）
    - 表里无 + 页面不可用 → 权限拦截（预期行为；本轮 common_admin 即此情形）
    - 表里无 + 页面可用   → 越权漏洞（安全缺陷，提 bug）
  反过来说：光看页面报 500 无法下结论，必须跑一次路由表判据（本文件 test_route_table_*）。

★ UX 缺陷（待提前端）：越权访问应给 403/无权限提示，而非"服务器出错"，后者会
  被误读为系统故障（本次排查就差点被带偏）。修复后本用例可升级为断言明确文案。

跑法：./venv/bin/pytest ui/py/test_role_permission.py -v
"""
import json

import allure

from ui.py.ai_flow import run_flow
from ui.py.api_baseline import role_has_route

# 仅系统管理员可见的入口（组织权限下挂 用户管理/部门管理，见上方路由树）
ADMIN_ONLY_ENTRY = "组织权限"


def _side_menus(role):
    r = run_flow("system_menu", role=role)
    assert not r.task("页面健康检查")["failed"], f"{role} 页面体检失败（环境/登录态）"
    t = r.task("侧边栏菜单采集")
    assert not t["failed"], f"{role} 菜单采集失败：{t['steps']}"
    raw = t["results"].get("side_menus")
    return json.loads(raw) if isinstance(raw, str) else raw


def _org_page_state(role):
    """跑 org_page 流程并返回最终快照。

    两段单次快照（A@1.5s / B@5s），取最后一次成功的：
    越权拦截会触发整页跳转，跳转瞬间执行的 JS 会被打断（context destroyed），
    单段快照有窗口期风险，两段互备才稳（2026-09-16 修 flaky 的结论）。
    """
    r = run_flow("org_page", role=role)
    assert not r.task("登录守卫")["failed"], f"{role} 登录态失效"
    snapshots = []
    for kw, key in (("快照A", "org_state_a"), ("快照B", "org_state_b")):
        t = r.task(kw)
        if t["failed"]:
            continue
        raw = t["results"].get(key)
        if raw:
            snapshots.append(json.loads(raw) if isinstance(raw, str) else raw)
    assert snapshots, f"{role} 两段快照均失败（流程级问题，非页面问题）"
    return snapshots[-1]


@allure.epic("HSC 智慧医院网络安全驾驶舱")
@allure.feature("权限-菜单可见性 + 深链接拦截（UI 层）")
class TestRoleMenuVisibility:
    @allure.title("系统管理员侧边栏含「组织权限」入口")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_admin_sees_org_entry(self):
        menus = _side_menus("admin")["menus"]
        assert any(ADMIN_ONLY_ENTRY in m for m in menus), \
            f"admin 侧边栏缺少「{ADMIN_ONLY_ENTRY}」入口；实际={menus}"

    @allure.title("普通管理员侧边栏无「组织权限」入口（权限收口）")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_common_admin_has_no_org_entry(self):
        menus = _side_menus("common_admin")["menus"]
        # 反向对照：先确保菜单本身采到了（防"页面挂了导致空列表"式的假通过）
        assert any("模板" in m for m in menus), f"common_admin 连自己该有的菜单都没有，采集可疑：{menus}"
        leaked = [m for m in menus if ADMIN_ONLY_ENTRY in m]
        assert not leaked, f"权限泄漏：common_admin 不该看到 {leaked}；实际={menus}"


@allure.epic("HSC 智慧医院网络安全驾驶舱")
@allure.feature("权限-菜单可见性 + 深链接拦截（UI 层）")
class TestRouteTableJudgement:
    """路由表判据：区分"权限拦截"与"路径写错"的确定性证据（详见模块 docstring 的判据表）。"""

    @allure.title("判据：organization 在 admin 授权路由表内")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_org_path_authorized_for_admin(self):
        # 表里有 + 页面可用 = 正常（页面可用性由 TestDeepLinkGuard 验证）
        assert role_has_route("admin", "organization"), \
            "admin 的授权路由表里没有 organization——若页面同时不可用，是路径/前端问题"

    @allure.title("判据：organization 不在 common_admin 授权路由表内（故其 500 页 = 权限拦截，非路径错）")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_org_path_unauthorized_for_common_admin(self):
        # 表里无 + 页面不可用 = 权限拦截（预期）。若这里失败（表里居然有），
        # 说明权限设计变了，common_admin 的拦截用例前提失效，需人工重核。
        assert not role_has_route("common_admin", "organization"), \
            "common_admin 路由表里出现了 organization——权限设计变化，需重新核对用例前提"


@allure.epic("HSC 智慧医院网络安全驾驶舱")
@allure.feature("权限-菜单可见性 + 深链接拦截（UI 层）")
class TestDeepLinkGuard:
    @allure.title("系统管理员直达 /organization 正常渲染")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_admin_can_open_org_page(self):
        state = _org_page_state("admin")
        assert state["landedPath"] == "/organization", f"admin 未能停留在组织权限页：{state}"
        assert not state["errPage"], f"admin 打开组织权限页出现错误页：{state}"
        assert state["hasTable"], f"组织权限页没渲染出表格：{state}"
        # 页面身份确认（别只验"有表格"就过——落到别的页也有一堆表格）
        assert "用户管理" in state["tabs"] and "部门管理" in state["tabs"], \
            f"组织权限页缺少子页签：{state['tabs']}"

    @allure.title("普通管理员直达 /organization 被前端拦截（重定向离开目标页）")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_common_admin_blocked_on_org_page(self):
        state = _org_page_state("common_admin")
        # 实测（2026-09-16，多次复现）：common_admin 直达 /organization【两种形态】——
        #   a) 停在 /organization，渲染通用「500 服务器出错」页；
        #   b) 被路由守卫重定向到默认页（/assetsOverview）。
        # 两者均为"不可用"，且**每次跑哪个形态不固定**（前端行为不一致，本身就是
        # 值得记录的现象）。断言只用跨形态都成立的语义：页面不可用。
        # ★ UX 缺陷（待提前端）：权限不足应给 403/无权限提示，"服务器出错"会误导用户。
        usable = (state["landedPath"] == "/organization") and state["hasTable"] and not state["errPage"]
        assert not usable, f"越权拦截失效？common_admin 可用组织权限页：{state}"
