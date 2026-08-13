# -*- coding: utf-8 -*-
"""
日志模块 - 只写文件，不打控制台（保持测试输出干净）
"""
import os
import logging
from datetime import datetime

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")

# 确保日志目录存在
os.makedirs(LOG_DIR, exist_ok=True)


def get_logger(name="test"):
    """
    获取日志记录器（只输出到文件）
    """
    logger = logging.getLogger(name)

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # 日志格式
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 文件 handler - 按日期命名
    log_file = os.path.join(LOG_DIR, f"test_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger
