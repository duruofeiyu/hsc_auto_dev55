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
        # 确定性任务必须绿（驱动链路本体的验证）
        assert not r.task("TC-DEMO-001")["failed"], "DOM 硬断言任务失败"
        assert not r.task("TC-DEMO-002")["failed"], "数据驱动比对任务失败"
        # AI 任务（TC-DEMO-003）为旁证层：长套件连跑时模型网关偶发抖动会失败，
        # 2026-09-16 全量回归实测过一次；按本项目"AI 旁证不阻塞"原则只提示不判红。
        if r.task("TC-DEMO-003")["failed"]:
            print("[warn] TC-DEMO-003 的 AI 判断本次失败（旁证层，不阻塞；重跑通常恢复）")

        cards_text = r.task("TC-DEMO-001")["results"].get("cards_text")
        assert cards_text, "cards_text 未提取到"
        if isinstance(cards_text, str):
            cards_text = json.loads(cards_text)
        for name in REQUIRED_CARDS:
            assert name in cards_text, f"缺卡片 {name}"

        # DOM 读数 与 AI 读数 交叉一致（演示页固定 87）——同样按旁证层处理
        if not r.task("TC-DEMO-003")["failed"]:
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
