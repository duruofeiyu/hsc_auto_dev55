"""驱动层自测：不依赖内网/登录态，用本地演示页验证 Python↔YAML↔JS 链路。

CI 里可以只跑这个文件做冒烟（其余 ui/py 用例需要环境可达 + 登录态有效）：
    ./venv/bin/pytest ui/py/test_flow_driver.py -v
"""
import json

import allure
import pytest

from ui.py.ai_flow import FlowError, run_flow

REQUIRED_CARDS = ["探测任务总数", "任务执行概览", "扫描活跃度"]


@allure.feature("UI 自动化驱动层自测")
class TestFlowDriver:
    @allure.title("正向：本地演示流程全绿且提取结果可解析")
    def test_demo_flow_passes(self):
        r = run_flow("demo_local", vars={"EXPECT_TOTAL": "87"}, ensure_auth=False)
        assert r.all_passed, f"演示流程应全绿，summary={r.summary}"
        assert r.summary == (3, 0, 0)

        cards_text = r.task("TC-DEMO-001")["results"].get("cards_text")
        assert cards_text, "cards_text 未提取到"
        if isinstance(cards_text, str):
            cards_text = json.loads(cards_text)
        for name in REQUIRED_CARDS:
            assert name in cards_text, f"缺卡片 {name}"

        # DOM 读数 与 AI 读数 交叉一致（演示页固定 87）
        assert r.task("TC-DEMO-003")["results"].get("ai_read_total") == 87

    @allure.title("负向：断言真的会红（防假绿的自检）")
    def test_assertion_actually_fails(self):
        r = run_flow("demo_local", vars={"EXPECT_TOTAL": "999"}, ensure_auth=False)
        assert not r.all_passed, "期望 999 与真实值 87 不符，流程必须报红"
        assert r.task("TC-DEMO-002")["failed"], "失败的应是 TC-DEMO-002 这条比对任务"
        assert not r.task("TC-DEMO-001")["failed"], "无关任务不应被连坐标红"

    @allure.title("异常：不存在的流程文件应抛 FileNotFoundError")
    def test_missing_flow_raises(self):
        with pytest.raises(FileNotFoundError):
            run_flow("no_such_flow_xyz")
