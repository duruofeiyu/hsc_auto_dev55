# 模块 × 三堆 总索引

> 以 HSC 8 个一级业务模块为主线，横切接口/UI/手工三堆。新增用例先查这张表，
> 保证命名与归属一致。最后更新：2026-09-16。

图例：✅ 已有 · ⬜ 暂无（待补） · 路径均相对 `hsc_auto/`

| 模块 | 一级路由 | 接口堆（pytest） | UI 堆（ui/） | 手工堆（manual_testcases/） |
|------|----------|------------------|--------------|------------------------------|
| 智慧大屏 | `overView` | ⬜ 暂无 | ⬜ 暂无 | ⬜ 暂无 |
| 资产管理 | `assetsManage` | ✅ `asset_management/` | ✅ `ui/py/test_asset_discover.py`<br>`flows/asset_discover.yaml` | ✅ 资产管理-测试用例.xlsx<br>资产管理-资产探测-新建任务测试用例.xlsx |
| 脆弱性管理 | `risk` | ✅ `vuln_management/` | ✅ `ui/py/test_vuln_overview.py`<br>`flows/vuln_overview.yaml`、`vuln_status_filter.yaml` | ✅ 脆弱性管理-测试用例.xlsx<br>系统漏洞管理-漏洞编号合并…xlsx<br>脆弱性管理-工单审批流程…xlsx |
| 合规运营 | `safe` | ✅ `compliance_operations/` | ✅ `ui/py/test_smoke_compliance_system.py`<br>`flows/compliance_overview.yaml` | ✅ 合规运营-测试用例.xlsx |
| 安服流程管理 | `securityService` | ⬜ 暂无 | ⬜ 暂无 | ✅ 新安服流程管理模块-…v1.7.xlsx<br>安服流程管理-项目管理.xlsx |
| 安全知识库 | `knowledge` | ⬜ 暂无 | ⬜ 暂无 | ⬜ 暂无 |
| 系统管理 | `system` | ✅ `system_management/` | ✅ `flows/system_menu.yaml`、`system_template.yaml`、`org_page.yaml` | ✅ 系统管理-平台设置页…xlsx<br>系统管理-扫描配置…xlsx<br>系统管理-操作日志…xlsx<br>系统管理-系统维护-系统升级…xlsx |
| 工单管理 | `tickets` | ⬜ 暂无 | ⬜ 旧选择器用例：`ui/tests/test_workorder_*.py`（存量，未迁 Midscene） | ⬜ 暂无（工单审批流程那份归在脆弱性下） |

## 覆盖度小结

- **接口**：4/8（资产、脆弱性、合规、系统管理）。
- **UI（新，Midscene）**：4/8（同上四个模块）；工单只有存量选择器用例在 `ui/tests/`。
- **手工**：5/8（多了安服流程管理）；智慧大屏、安全知识库、工单管理 三块手工也缺。

## 命名规范（新增用例时照此对齐，别再发散）

| 堆 | 位置 | 命名 |
|----|------|------|
| 接口 | `<module>_management/`（英文，pytest testpaths 依赖，勿改中文） | `test_<页面>.py` + `utils_<页面>.py` + `data/<页面>_data.yaml` |
| UI 流程 | `ui/midscene/flows/` | `<模块>_<页面>.yaml`（如 `vuln_overview.yaml`） |
| UI 用例 | `ui/py/` | `test_<模块>_<页面>.py` |
| 手工 | `manual_testcases/` | `<模块>-<页面/主题>.xlsx`（中文模块名，与本表列名一致） |

## 缺口优先级（下次补用例看这里）

1. **工单管理**：手工 + 新 UI 都缺，且存量选择器用例还没迁到 Midscene —— 覆盖面最大的空白。
2. **智慧大屏 / 安全知识库**：三堆全空，至少补一份手工用例打底。
3. **安服流程管理**：只有手工，缺接口 + UI。
4. 接口缺的 4 个模块里，安服流程/工单是业务重点，值得补接口自动化。
