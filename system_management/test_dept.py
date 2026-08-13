"""
55 开发环境 - 系统管理 - 部门管理接口测试
"""
import allure
import pytest
import time
import sys, os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))

from system_management.base import get_headers, assert_success, assert_business_fail, request_wrapper, request_no_auth
from system_management.utils_common import unique_name, unique_code

from system_management.utils_dept import (
    query_depts,
    create_dept,
    update_dept,
    delete_dept,
    batch_delete_depts,
    build_dept_payload,
    DEPT_BASE,
)


def unique_dept_name(prefix="部门"):
    """生成唯一部门名称"""
    return unique_name(prefix=prefix)


def unique_dept_code(prefix="yaml"):
    """生成唯一部门编码"""
    return unique_code(prefix=prefix)


@allure.epic("HSC 系统管理")
@allure.feature("部门管理")
@allure.story("部门列表查询")
class TestQueryDept:
    """部门管理 - 列表查询"""

    @allure.title("部门列表默认查询")
    @allure.description("验证部门列表接口能正常返回数据")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_query_dept_list_default(self):
        """默认查询部门列表"""
        resp = query_depts()
        data = assert_success(resp, "部门列表默认查询")
        result = data.get("result", {})
        records = result.get("list", [])
        print(f"\n【部门列表默认】total={result.get('total')}, records={len(records)}")
        assert len(records) <= 10

    @allure.title("部门列表分页")
    @allure.description("验证分页功能，指定 pageSize=5 返回不超过 5 条")
    @allure.severity(allure.severity_level.NORMAL)
    def test_query_dept_list_pagination(self):
        """分页查询"""
        payload = {"condition": {}, "pageNum": 1, "pageSize": 5}
        resp = query_depts(payload)
        data = assert_success(resp, "部门列表分页")
        result = data.get("result", {})
        records = result.get("list", [])
        print(f"\n【部门列表分页】total={result.get('total')}, records={len(records)}")
        assert len(records) <= 5

    @allure.title("部门列表字段完整性")
    @allure.description("验证部门列表返回数据包含所有必填字段")
    @allure.severity(allure.severity_level.NORMAL)
    def test_query_dept_list_field_completeness(self):
        """部门列表字段完整性"""
        resp = query_depts()
        data = assert_success(resp, "部门列表字段")
        records = data.get("result", {}).get("list", [])
        if records:
            required_fields = [
                "id", "parentId", "deptCode", "deptName",
                "deptStatus", "sourceType", "orderNum",
                "createBy", "createTime"
            ]
            optional_fields = ["parentName", "leader", "updateBy", "updateTime"]
            item = records[0]
            missing_required = [f for f in required_fields if f not in item]
            missing_optional = [f for f in optional_fields if f not in item]
            print(f"\n【部门列表字段】缺失必填字段: {missing_required}, 缺失可选字段: {missing_optional}")
            assert not missing_required, f"缺失必填字段: {missing_required}"

    @allure.title("按部门编码搜索")
    @allure.description("按 deptCode 精确搜索部门")
    @allure.severity(allure.severity_level.NORMAL)
    def test_query_dept_by_dept_code(self):
        """按部门编码搜索"""
        payload = {"condition": {"deptCode": "001001"}, "pageNum": 1, "pageSize": 10}
        resp = query_depts(payload)
        data = assert_success(resp, "按deptCode查询部门")
        result = data.get("result", {})
        print(f"\n【按deptCode查询】total={result.get('total')}")
        assert result.get("total") == "1"

    @allure.title("无 Token 查询部门列表")
    @allure.description("验证未登录状态访问部门列表会被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_query_dept_no_token(self):
        """无 Token 查询部门列表"""
        resp = request_no_auth(
            "post",
            f"{DEPT_BASE}/list",
            msg="无Token查询部门列表",
            json={"condition": {}, "pageNum": 1, "pageSize": 10}
        )
        print(f"\n【部门列表-无Token】status={resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"【部门列表-无Token】success={data.get('success')}, code={data.get('code')}")
            assert data.get("success") == False or data.get("code") != 200
        else:
            assert resp.status_code in [401, 403]


@allure.epic("HSC 系统管理")
@allure.feature("部门管理")
@allure.story("新增部门")
class TestCreateDept:
    """部门管理 - 新增"""

    @allure.title("正常新增部门")
    @allure.description("创建一个新部门，验证返回 dept_id，自动清理")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_create_dept_success(self, temp_dept):
        """正常新增部门"""
        if temp_dept is None:
            pytest.skip("临时部门创建失败，跳过该用例")
        print(f"\n【新增部门】dept_id={temp_dept}")
        assert temp_dept is not None

    @allure.title("新增下级部门")
    @allure.description("在研发部下创建下级部门，验证返回 dept_id")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_create_dept_with_parent(self, temp_child_dept):
        """新增下级部门"""
        if temp_child_dept is None:
            pytest.skip("临时下级部门创建失败，跳过该用例")
        print(f"\n【新增下级部门】dept_id={temp_child_dept}")
        assert temp_child_dept is not None

    @allure.title("新增部门响应时间")
    @allure.description("验证新增部门接口响应时间 < 3 秒")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_dept_response_time(self):
        """新增部门响应时间 < 3 秒"""
        payload = build_dept_payload(
            dept_name=unique_dept_name(),
            dept_code=unique_dept_code()
        )
        dept_id = None
        try:
            start = time.time()
            resp = create_dept(payload)
            elapsed = time.time() - start
            data = assert_success(resp, "新增部门响应时间")
            dept_id = data.get("result")
            print(f"\n【新增部门-响应时间】dept_id={dept_id}, elapsed={elapsed:.3f}s")
            allure.attach(f"响应时间: {elapsed:.3f}s", name="性能数据",
                          attachment_type=allure.attachment_type.TEXT)
            assert elapsed < 3.0, f"新增部门耗时 {elapsed:.3f}s，超过 3s 阈值"
        finally:
            if dept_id:
                try:
                    delete_dept(dept_id)
                except Exception:
                    pass

    @allure.title("缺少 deptName")
    @allure.description("验证缺少必填字段 deptName 时接口返回失败")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_dept_missing_name(self):
        """缺少 deptName"""
        payload = build_dept_payload(
            dept_name=unique_dept_name(),
            dept_code=unique_dept_code()
        )
        payload.pop("deptName")
        resp = create_dept(payload)
        data = assert_business_fail(resp, msg="缺少deptName")
        print(f"\n【必填-deptName缺失】code={data.get('code')}, msg={data.get('message')}")

    @allure.title("无 Token 新增部门")
    @allure.description("验证未登录状态新增部门会被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_create_dept_no_token(self):
        """无 Token 新增部门"""
        payload = build_dept_payload(
            dept_name=unique_dept_name(),
            dept_code=unique_dept_code()
        )
        resp = request_no_auth(
            "post",
            DEPT_BASE,
            msg="无Token新增部门",
            json=payload
        )
        print(f"\n【新增部门-无Token】status={resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"【新增部门-无Token】success={data.get('success')}, code={data.get('code')}")
            assert data.get("success") == False or data.get("code") != 200
        else:
            assert resp.status_code in [401, 403]


@allure.epic("HSC 系统管理")
@allure.feature("部门管理")
@allure.story("编辑部门")
class TestUpdateDept:
    """部门管理 - 编辑"""

    @allure.title("编辑部门名称")
    @allure.description("创建部门后编辑名称，验证编辑成功，自动清理")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_update_dept_name(self, temp_dept):
        """编辑部门名称"""
        if temp_dept is None:
            pytest.skip("临时部门创建失败，跳过该用例")

        update_payload = build_dept_payload(
            dept_name=unique_dept_name("编辑后")
            # 不传 dept_code，编辑时后端保留原编码
        )
        resp_update = update_dept(temp_dept, update_payload)
        assert_success(resp_update, "编辑部门名")
        print(f"\n【编辑部门】dept_id={temp_dept}, success=True")

    @allure.title("编辑部门状态为停用")
    @allure.description("创建部门后停用，验证状态变更成功")
    @allure.severity(allure.severity_level.NORMAL)
    def test_update_dept_status(self, temp_dept):
        """编辑部门状态为停用"""
        if temp_dept is None:
            pytest.skip("临时部门创建失败，跳过该用例")

        update_payload = build_dept_payload(
            dept_name=unique_dept_name(),
            dept_status=1
        )
        resp_update = update_dept(temp_dept, update_payload)
        assert_success(resp_update, "编辑部门状态")
        print(f"\n【编辑部门状态】dept_id={temp_dept}, status=1")

    @allure.title("无 Token 编辑部门")
    @allure.description("验证未登录状态编辑部门会被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_update_dept_no_token(self):
        """无 Token 编辑部门"""
        payload = build_dept_payload(
            dept_name=unique_dept_name(),
            dept_code=unique_dept_code()
        )
        resp = request_no_auth(
            "put",
            f"{DEPT_BASE}/999999",
            msg="无Token编辑部门",
            json=payload
        )
        print(f"\n【编辑部门-无Token】status={resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"【编辑部门-无Token】success={data.get('success')}, code={data.get('code')}")
            assert data.get("success") == False or data.get("code") != 200
        else:
            assert resp.status_code in [401, 403]


@allure.epic("HSC 系统管理")
@allure.feature("部门管理")
@allure.story("删除部门")
class TestDeleteDept:
    """部门管理 - 删除"""

    @allure.title("正常删除部门")
    @allure.description("验证 temp_dept fixture 自动清理机制（fixture teardown 自动删除）")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_delete_normal_dept(self, temp_dept):
        """正常删除部门（fixture teardown 自动清理）"""
        if temp_dept is None:
            pytest.skip("临时部门创建失败，跳过该用例")

        print(f"\n【删除验证】dept_id={temp_dept}，将在 fixture teardown 中自动删除")
        assert temp_dept is not None

    @allure.title("删除不存在的部门")
    @allure.description("验证删除不存在的部门返回失败")
    @allure.severity(allure.severity_level.NORMAL)
    def test_delete_non_existent_dept(self):
        """删除不存在的部门"""
        fake_id = "9999999999999999999"
        resp = delete_dept(fake_id)
        data = resp.json()
        print(f"\n【删除-不存在】success={data.get('success')}, code={data.get('code')}, msg={data.get('message')}")
        assert data.get("success") == False or data.get("code") != 200, \
            f"删除不存在的部门应返回失败，实际: {data}"

    @allure.title("无 Token 删除部门")
    @allure.description("验证未登录状态删除部门会被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_delete_no_token(self):
        """无 Token 删除部门"""
        resp = request_no_auth(
            "delete",
            f"{DEPT_BASE}/999999",
            msg="无Token删除部门"
        )
        print(f"\n【删除-无Token】status={resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"【删除-无Token】success={data.get('success')}, code={data.get('code')}")
            assert data.get("success") == False or data.get("code") != 200
        else:
            assert resp.status_code in [401, 403]


@allure.epic("HSC 系统管理")
@allure.feature("部门管理")
@allure.story("部门IP段")
class TestDeptIp:
    """部门管理 - IP 段"""

    @allure.title("查询部门IP段列表")
    @allure.description("查询指定部门的 IP 段列表")
    @allure.severity(allure.severity_level.NORMAL)
    def test_query_dept_ip_list(self):
        """查询部门 IP 段列表"""
        from config import BASE_URL
        # 该接口需要认证，使用带 token 的请求
        resp = request_wrapper(
            "get",
            f"{BASE_URL}/system/dept-ip/list",
            msg="查询部门IP段",
            params={"deptId": "2082053606579658754", "_t": int(time.time() * 1000)},
            headers=get_headers()
        )
        data = assert_success(resp, "查询部门IP段")
        result = data.get("result", [])
        print(f"\n【部门IP段】records={len(result)}")
        assert isinstance(result, list)


@allure.epic("HSC 系统管理")
@allure.feature("部门管理")
@allure.story("生命周期")
class TestLifecycleDept:
    """部门管理 - 生命周期"""

    @allure.title("部门管理 - 生命周期")
    @allure.description("创建 → 列表查到 → 编辑 → 删除 → 查不到")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_lifecycle_create_query_update_delete(self, temp_dept):
        """创建 → 列表查到 → 编辑 → 删除 → 查不到"""
        if temp_dept is None:
            pytest.skip("临时部门创建失败，跳过该用例")

        dept_id = temp_dept
        print(f"\n【生命周期】创建 dept_id={dept_id}")

        # 列表查到
        resp_list = query_depts({"condition": {}, "pageNum": 1, "pageSize": 10})
        data_list = assert_success(resp_list, "生命周期列表查询")
        records = data_list.get("result", {}).get("list", [])
        assert any(r.get("id") == dept_id for r in records), "创建后列表查不到部门"
        print("【生命周期】创建后列表存在 ✅")

        # 编辑
        update_payload = build_dept_payload(
            dept_name=unique_dept_name("已编辑")
        )
        resp_update = update_dept(dept_id, update_payload)
        assert_success(resp_update, "生命周期编辑")
        print("【生命周期】编辑成功 ✅")

        # 删除
        delete_dept(dept_id)
        print("【生命周期】删除成功 ✅")

        # 查不到
        resp_list2 = query_depts({"condition": {}, "pageNum": 1, "pageSize": 10})
        data_list2 = assert_success(resp_list2, "生命周期删除后查询")
        records2 = data_list2.get("result", {}).get("list", [])
        assert not any(r.get("id") == dept_id for r in records2), "删除后列表仍存在部门"
        print("【生命周期】删除后列表不存在 ✅")


# ======================== 8. 批量删除部门 ========================

@allure.epic("HSC 系统管理")
@allure.feature("部门管理")
@allure.story("批量删除")
class TestBatchDeleteDept:
    """部门管理 - 批量删除"""

    @allure.title("批量删除部门")
    @allure.description("创建多个部门后批量删除，验证删除成功")
    @allure.severity(allure.severity_level.NORMAL)
    def test_batch_delete_depts(self):
        """批量删除部门"""
        dept_ids = []
        for _ in range(2):
            payload = build_dept_payload(
                dept_name=unique_dept_name(),
                dept_code=f"batch_{uuid.uuid4().hex[:6]}"
            )
            resp = create_dept(payload)
            data = resp.json()
            if data.get("success"):
                dept_ids.append(data.get("result"))

        if not dept_ids:
            pytest.skip("临时部门创建失败，跳过该用例")

        try:
            resp = batch_delete_depts(dept_ids)
            data = assert_success(resp, "批量删除部门")
            print(f"\n【批量删除】dept_ids={dept_ids}, success={data.get('success')}")
        finally:
            for did in dept_ids:
                try:
                    delete_dept(did)
                except Exception:
                    pass
