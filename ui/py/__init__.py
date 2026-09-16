"""Python 侧 UI 自动化：pytest 写用例，AI 步骤交给 ui/midscene 的 JS 内核。

为什么这样分（2026-09-15 定稿）：
- Midscene 的视觉内核只有 JS/TS（官方无 Python SDK；社区 pymidscene 0.3.0 是
  桥接包且更新滞后，不作为回归依赖）。
- 但「用例」不等于「AI 调用」：用例设计、数据驱动、断言、Allure 报告 ——
  这些全在 Python 侧做，和你接口框架同一套 pytest 肌肉记忆。
- AI 步骤用 flows/*.yaml 描述（语言中立），执行交给已调通的
  ui/midscene/scripts/run-yaml.js（自带浏览器、复用登录态、DOM 硬断言生效）。

分工一句话：**Python 管"测什么、怎么判"，YAML 管"点哪几下"，JS 只管"跑起来"。**
"""
