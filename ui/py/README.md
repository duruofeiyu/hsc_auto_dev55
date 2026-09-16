# ui/py —— Python 侧 UI 自动化用例层

> 回答一个问题：**Midscene 的视觉内核只有 JS，但用例可以（也应该）用 Python 写。**
> 官方无 Python SDK（1.12 文档 Playwright 集成页纯 TypeScript）；社区 pymidscene 0.3.0
> 是桥接包、更新滞后，不作为回归依赖。所以分工是：
>
> - **Python（pytest）**：用例设计、数据驱动、断言、Allure —— 和接口框架同一套写法；
> - **YAML（flows/）**：描述"点哪几下"（语言中立，不写选择器）；
> - **JS（ui/midscene/scripts/run-yaml.js）**：只负责把 YAML 跑起来（浏览器/登录态/DOM 硬断言）。

## 目录

```
ui/py/
├── ai_flow.py              ★ 驱动封装：run_flow() + FlowResult（解析任务块/提取结果/退出码）
├── test_flow_driver.py     ★ 驱动自测（离线可跑，CI 冒烟用）
├── test_asset_discover.py  ★ 真实用例示例（资产发现页 SCAN-002/003/004）
└── README.md
```

## 跑法

```bash
cd ~/hsc_auto
./venv/bin/pytest ui/py/test_flow_driver.py -v      # 离线自测（不需要内网/登录态）
./venv/bin/pytest ui/py/test_asset_discover.py -v   # 真实环境用例
HSC_ENV=55 ./venv/bin/pytest ui/py -v               # 切环境（默认读项目根 .env 的 HSC_ENV）
allure serve reports/allure-results                  # 报告（flow 完整输出已 attach）
```

## 写一条新用例（3 步）

1. **流程**：复用 `ui/midscene/flows/*.yaml`，或新建一个 YAML（照 asset_discover.yaml 抄结构：
   第 0 步环境体检 + `javascript` 硬断言 + `aiQuery/aiAssert` 旁证；`name:` 给提取结果起名）。
2. **用例**：在 ui/py/ 下写 test_xxx.py：

   ```python
   from ui/py.ai_flow import run_flow

   def test_something():
       r = run_flow("asset_discover", vars={"EXPECT_TOTAL": "87"})  # 数据驱动靠 vars
       assert r.all_passed
       cards = r.task("统计卡片")["results"]["cards_text"]           # 提取结果在 Python 里断言
       assert "探测任务总数" in cards
   ```

3. **跑**：`./venv/bin/pytest ui/py/test_xxx.py -v`。

## FlowResult 契约（ai_flow.py 解析自 run-yaml.js 输出）

| 字段 | 含义 |
|---|---|
| `r.all_passed` | 退出码 0 且无任务 failed |
| `r.summary` | (passed, failed, skipped) |
| `r.task("关键字")` | 取任务块：`{title, steps, results, failed}` |
| `task["results"]` | YAML 里带 `name:` 的步骤提取出的值（javascript 返回 / aiQuery 结果） |
| `FlowError` | 退出码 2 = **环境问题**（登录态/页面报错），与用例失败分开报 |

## 与 ui/midscene/tests/*.spec.js 的关系

JS spec 是早期 PoC 的写法（Playwright + midscene fixture，全 JS）。新用例一律走 ui/py；
JS spec 不删（留着对照与 bridge 场景），但不再新增。
