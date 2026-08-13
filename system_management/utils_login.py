"""
55 开发环境 - 系统管理 - 登录模块工具层
"""

import requests
import base64
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))
from config import BASE_URL
from system_management.base import assert_success, assert_business_fail, request_wrapper

LOGIN_BASE = f"{BASE_URL}/system/auth"


def get_captcha_image(save_path="captcha.jpg"):
    """
    获取验证码图片
    POST /system/auth/captcha
    返回 imageToken(uuid) 和保存路径
    """
    resp = request_wrapper("post", f"{LOGIN_BASE}/captcha", msg="获取验证码",
                           json={}, headers={"Content-Type": "application/json;charset=UTF-8"})
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"获取验证码失败: {data}")

    image_token = data["result"]["image"]["imageToken"]
    image_base64 = data["result"]["image"]["code"]

    # base64 可能带 data:image/jpeg;base64, 前缀，去掉
    if "," in image_base64:
        image_base64 = image_base64.split(",")[1]

    image_bytes = base64.b64decode(image_base64)
    with open(save_path, "wb") as f:
        f.write(image_bytes)

    return image_token, save_path


def login(user_account, encrypted_password, code, uuid):
    """
    用户登录
    POST /system/auth/login
    password 需要是前端加密后的密文
    """
    payload = {
        "userAccount": user_account,
        "password": encrypted_password,
        "code": code,
        "uuid": uuid
    }
    return request_wrapper("post", f"{LOGIN_BASE}/login", msg="用户登录",
                           json=payload, headers={"Content-Type": "application/json;charset=UTF-8"})


def get_user_info(token):
    """
    获取当前登录用户信息
    GET /system/user/info
    TODO: URL 待抓包确认
    """
    headers = {
        "Authorization": token,
        "X-Access-Token": token,
        "Content-Type": "application/json;charset=UTF-8"
    }
    return request_wrapper("get", f"{BASE_URL}/system/user/info", msg="获取用户信息",
                           headers=headers)


def get_user_routes(token, timestamp=None):
    """
    获取当前登录用户的菜单路由树
    GET /system/auth/routes?_t={timestamp}
    """
    if timestamp is None:
        timestamp = int(time.time() * 1000)
    headers = {
        "Authorization": token,
        "X-Access-Token": token,
        "Content-Type": "application/json;charset=UTF-8"
    }
    return request_wrapper("get", f"{LOGIN_BASE}/routes", msg="获取用户路由",
                           params={"_t": timestamp}, headers=headers)


def logout(token):
    """
    用户登出
    POST /system/auth/logout
    TODO: URL 待抓包确认
    """
    headers = {
        "Authorization": token,
        "X-Access-Token": token,
        "Content-Type": "application/json;charset=UTF-8"
    }
    return request_wrapper("post", f"{LOGIN_BASE}/logout", msg="用户登出",
                           headers=headers)
