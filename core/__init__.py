"""
HSC 自动化测试框架 - 核心公共封装（被多模块复用）

统一放置跨模块共享的基础设施：
  - base.py        : 请求封装（request_wrapper / assert_success / assert_business_fail /
                     retry_on_failure / load_yaml_data / request_no_auth）
  - utils_sign.py  : x-sign 签名算法（复刻前端 axios 拦截器）
  - utils_common.py: 唯一值生成 / 树查找 / 签名校验工具 / 清理关键字

说明：原位于 system_management/ 下，但被 system_management / asset_management /
vuln_management / compliance_operations 四大模块共同 import，语义上属于框架核心层，
故提升至独立 core/ 包。system_management 仅保留其业务专属的 utils_* / test_* 文件。
"""
