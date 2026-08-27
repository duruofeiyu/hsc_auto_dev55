"""
55 开发环境 - 系统管理 - 公共基础模块
抽取各 utils_*.py 中重复的 assert_success / assert_business_fail / request_wrapper
注意：get_headers() 统一在 config.py 中定义，此处不再重复
"""
import time
import logging
import requests
from functools import wraps

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))
from config import BASE_URL, load_token, get_headers
from logger import get_logger
from system_management.utils_sign import compute_sign

logger = get_logger("base")

# 默认请求超时时间（连接超时, 读取超时）
DEFAULT_TIMEOUT = (5, 30)


def assert_success(response, msg=""):
    """
    断言业务成功
    - success == True
    - code == 200
    失败时自动打印响应内容
    返回：响应 JSON 中的 result 字段（业务数据部分）
    """
    data = response.json()
    if data.get("success") != True or data.get("code") != 200:
        logger.error(f"{msg} 业务失败: success={data.get('success')}, code={data.get('code')}, message={data.get('message')}")
    assert data.get("success") == True, f"{msg} 业务失败: {data.get('message')}"
    assert data.get("code") == 200, f"{msg} code 非200: {data.get('code')}"
    logger.info(f"{msg} 成功")
    return data.get("result")


def assert_business_fail(response, msg=""):
    """
    断言业务失败（success=False 或 code!=200）
    返回：完整响应 JSON（方便调用方获取错误详情）
    """
    data = response.json()
    if data.get("success") == False or data.get("code") != 200:
        logger.info(f"{msg} 业务失败符合预期: code={data.get('code')}, message={data.get('message')}")
    else:
        logger.error(f"{msg} 应业务失败，实际: success={data.get('success')}, code={data.get('code')}")
    assert data.get("success") == False or data.get("code") != 200, \
        f"{msg} 应业务失败，实际: {data}"
    return data


def request_wrapper(method, url, msg="", **kwargs):
    """
    统一请求封装：自动添加 timeout、日志、异常处理
    用法: request_wrapper("post", url, msg="新增用户", json=payload, headers=get_headers())
    """
    # 默认超时
    if "timeout" not in kwargs:
        kwargs["timeout"] = DEFAULT_TIMEOUT
    # 默认不验证 SSL
    if "verify" not in kwargs:
        kwargs["verify"] = False

    # 复刻 HSC 前端 x-sign 签名：基于 url + params + data 计算
    headers = kwargs.get("headers") or {}
    if isinstance(headers, dict):
        sign_params = kwargs.get("params")
        sign_data = kwargs.get("json") or kwargs.get("data")
        try:
            headers["x-sign"] = compute_sign(url, sign_params, sign_data)
        except Exception as e:
            logger.warning(f"[{msg}] x-sign 计算失败: {e}")
        kwargs["headers"] = headers

    start = time.time()
    try:
        resp = requests.request(method, url, **kwargs)
        elapsed = time.time() - start
        logger.info(f"[{msg}] {method.upper()} {url} -> status={resp.status_code}, elapsed={elapsed:.3f}s")
        return resp
    except requests.exceptions.Timeout:
        elapsed = time.time() - start
        logger.error(f"[{msg}] {method.upper()} {url} -> TIMEOUT after {elapsed:.3f}s")
        raise
    except requests.exceptions.ConnectionError as e:
        logger.error(f"[{msg}] {method.upper()} {url} -> ConnectionError: {e}")
        raise
    except Exception as e:
        logger.error(f"[{msg}] {method.upper()} {url} -> Error: {e}")
        raise


def retry_on_failure(max_retries=1, delay=1.0):
    """
    失败重试装饰器
    用法:
        @retry_on_failure(max_retries=2, delay=1.0)
        def flaky_api_call():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"[retry] 第 {attempt + 1} 次失败，{delay}s 后重试: {e}")
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator


def load_yaml_data(yaml_file):
    """
    加载 YAML 测试数据
    用法: data = load_yaml_data("user_data.yaml")
    """
    import yaml
    data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', yaml_file)
    with open(data_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def request_no_auth(method, url, msg="", **kwargs):
    """
    无认证请求封装（用于测试无 Token 场景）
    自动添加 Content-Type 和 timeout，但不添加 Token
    用法: request_no_auth("post", url, msg="无Token测试", json=payload)
    """
    headers = kwargs.pop("headers", {})
    if "Content-Type" not in headers:
        headers["Content-Type"] = "application/json;charset=UTF-8"
    return request_wrapper(method, url, msg=msg, headers=headers, **kwargs)
