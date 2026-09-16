"""脆弱性管理 → 系统漏洞管理（/assetsVuln）→ 漏洞总览页签。

流程步骤在 flows/vuln_overview.yaml（DOM 主力 + AI 交叉验证）。
本文件：解析提取结果做断言、数据驱动、Allure 装饰。

跑法：
    cd ~/hsc_auto
    ./venv/bin/pytest ui/py/test_vuln_overview.py -v
    # 登录态过期会由 run_flow 前置体检自动重登（123 会话很短，实测约 10 分钟）

为什么断言以 DOM 为准（2026-09-15 实测印证方法论）：
  同一页 DOM 数到「待处理」27 行，AI 只读到 4 —— 因为 AI 看截图只有视口内可见的几行，
  DOM 遍历整个 tbody。这正是"视觉模型擅长人眼能看懂的模糊判断、但在精确计数上会漏"。
  所以计数/状态分布一律 DOM 硬断言；AI 那次调用只作旁证，不参与通过判定。
"""
import json
import re

import allure
import pytest

from ui.py.ai_flow import run_flow


@allure.epic("HSC 智慧医院网络安全驾驶舱")
@allure.feature("脆弱性管理-系统漏洞")
class TestVulnOverview:
    """TC-HSC55-VULN-001：漏洞总览页签与表格数据"""

    @pytest.fixture(scope="class")
    def flow(self):
        """整个类共用一次流程跑动（登录态体检 + 进页面 + 读数），省时间省 token。"""
        return run_flow("vuln_overview")

    @allure.title("页面健康且「漏洞总览」页签处于激活态")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_page_healthy_and_tab_active(self, flow):
        assert not flow.task("页面健康检查")["failed"], "页面体检失败（环境/登录态问题）"
        tab = flow.task("页签校验")
        assert not tab["failed"], f"页签校验失败：{tab['steps']}"
        assert "漏洞总览" in tab["results"].get("tab_active_check", ""), "激活页签不是漏洞总览"

    @allure.title("表格与状态分布（DOM 主力断言）")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_table_dom_assertions(self, flow):
        t = flow.task("表格与状态分布")
        assert not t["failed"], f"DOM 读取任务失败：{t['steps']}"
        raw = t["results"].get("dom_table")
        assert raw, "没提取到 dom_table"
        data = json.loads(raw) if isinstance(raw, str) else raw

        # ① 表头含本页关键列（落到别的页会缺列，立刻红）
        for col in ("IP地址", "漏洞名称", "状态"):
            assert any(col in h for h in data["headers"]), f"表头缺「{col}」列，当前页可能不是漏洞总览：{data['headers']}"

        # ② 状态列定位成功且分布自洽：分布总数 == 行数
        assert data["statusCol"] >= 0, "没定位到「状态」列"
        assert sum(data["statusDist"].values()) == data["rowCount"], "状态分布与行数不自洽"

        # ③ 本页行数不得超过分页全库总数（数据自洽性）
        assert data["rowCount"] <= data["paginationTotal"], \
            f"本页 {data['rowCount']} 行 > 分页总数 {data['paginationTotal']}，数据矛盾"

    @allure.title("AI 交叉验证读数（旁证，不因波动卡通过率）")
    @allure.severity(allure.severity_level.MINOR)
    def test_ai_cross_check_nonblocking(self, flow):
        """AI 数到的待处理行数只作旁证。它天然只看得到视口内的行，
        和 DOM 全表计数不一致是【预期内】的（实测 27 vs 4），
        所以这里只记录、不断言相等——把不一致摆出来供人判断，才是交叉验证的正确用法。
        """
        t = flow.task("AI 读本页待处理")
        if t["failed"]:
            allure.attach("AI 交叉验证波动，未产出（不阻塞）", name="ai_note",
                          attachment_type=allure.attachment_type.TEXT)
            pytest.skip("AI 旁证波动（已知不稳定，非阻塞）")
        ai = t["results"].get("ai_pending") or {}
        dom = flow.task("表格与状态分布")["results"].get("dom_table")
        dom = json.loads(dom) if isinstance(dom, str) else dom
        allure.attach(
            f"DOM 待处理={dom['pendingCount']}（全表） | AI 待处理={ai.get('count')}（视口内）——差异属预期",
            name="cross_check", attachment_type=allure.attachment_type.TEXT,
        )
        # 唯一硬约束：两者都得是合法非负数（AI 偶尔抽风返回负数/非数字才算异常）
        assert isinstance(ai.get("count"), int) and ai["count"] >= 0, f"AI 读数非法：{ai}"
        assert dom["pendingCount"] >= 0


@allure.epic("HSC 智慧医院网络安全驾驶舱")
@allure.feature("脆弱性管理-系统漏洞")
class TestVulnStatusFilter:
    """TC-VULN-002：资产漏洞页签-状态列筛选（在线/离线）。

    ⚠️ 本条用例诞生于一次"推翻旧假设"（2026-09-16 用真实浏览器逐帧探明）：
      1) 55 的「筛选表单区 + el-select + 查询按钮」在 123 该页【不存在】——
         bridge_hsc v10 的 DOM 路径直接搬过来必挂（"定位不到状态筛选下拉"）；
      2) 漏洞总览页签的「状态」列（待处理/修复中）在 123【没有筛选入口】，
         "筛状态=待处理→全库总数"在 123 没有产品能力支撑，不许照抄旧环境硬造；
      3) 真正的状态筛选在资产漏洞页签：列头漏斗图标（el-dropdown-link，
         click 触发、hover 无效），面板=资产在线状态（在线/离线）+ 筛选/重置。
    教训：用例必须长在当前环境的真实能力上，改版会自然把用例打红、倒逼人来核对。
    """

    @allure.title("状态列筛选「在线」后：只剩在线行且总数自洽")
    @allure.severity(allure.severity_level.NORMAL)
    def test_status_filter_online_only(self):
        r = run_flow("vuln_status_filter")
        t = r.task("状态列筛选")
        assert not t["failed"], f"筛选链路失败（前端可能改版，看 verify_filtered 报错）：{t['steps']}"

        raw = t["results"].get("verify_filtered")
        assert raw, "没提取到 verify_filtered"
        import json
        data = json.loads(raw) if isinstance(raw, str) else raw

        # ① 筛选生效：状态分布必须只有「在线」
        assert list(data["statusDist"].keys()) == ["在线"], f"筛选后混入其他状态：{data['statusDist']}"
        # ② 有数据且本页 ≤ 全库总数
        assert data["rowCount"] >= 1
        assert data["rowCount"] <= data["onlineTotal"], f"本页 {data['rowCount']} > 全库 {data['onlineTotal']}"


@allure.epic("HSC 智慧医院网络安全驾驶舱")
@allure.feature("脆弱性管理-系统漏洞")
class TestVulnPagination:
    """分页总数钉值（数据驱动）——环境数据会变，期望值按环境实测维护"""

    @allure.title("全库漏洞总数 = {{expect_total}}（数据驱动演示）")
    @allure.severity(allure.severity_level.NORMAL)
    # ⚠️ 2585 是 2026-09-16 123 实测值（9-15 为 2583，两天 +2：漏洞随扫描增长，
    # 期望值会漂。跑红先拿 flow 输出里的实际值核对：是数据漂移就更新参数，是 bug 才提单。
    # 长期方案：期望值改从接口层拿基线（vuln_management 已有查询封装），别在 UI 层钉总数。
    @pytest.mark.parametrize("expect_total", ["2585"])
    def test_total_data_driven(self, expect_total):
        r = run_flow("vuln_overview", vars={"EXPECT_TOTAL": expect_total})
        check = r.task("全库漏洞总数")
        assert not check["failed"], (
            f"分页总数不等于 {expect_total}（环境数据可能已变，重跑 flow 看实际值再更新）"
        )
