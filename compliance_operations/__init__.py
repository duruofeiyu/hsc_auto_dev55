"""合规运营 - 接口自动化测试包

覆盖 13 个子模块（14 目录中 top3_review 为空目录，忽略）：
- 通用任务线（复用 /compliance/task，11 个 typeCode）：
  网络安全任务书 / 个人信息保护 / 等保测评 / 国密合规 / 三甲评审 /
  数据安全 / 电子病历评级 / 网络安全成熟度 / 智慧医院评级 / 互联互通 / 互联网诊疗
- 合规总览（GET /compliance/overview/recent-tasks）
- 管理系统（/compliance/system + /asset/options + /asset/list-by-ids）
- 个人信息保护 PIA 多步骤（/personal-info-protection/pia + /compliance/result）
"""
