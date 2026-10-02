"""统一日志配置。

对应 TODO 第 25 节：记录时间、识别文本、解析结果、学生、单元格、旧/新成绩、错误。
"""
from __future__ import annotations

import logging
import os
from datetime import datetime

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s - %(message)s"
_ROOT_NAME = "score_voice"


def setup_logger(log_dir: str = "logs", level: int = logging.INFO) -> logging.Logger:
    """创建并返回项目的根 logger，同时输出到控制台与日志文件。"""
    logger = logging.getLogger(_ROOT_NAME)
    if logger.handlers:  # 避免重复初始化
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(_LOG_FORMAT)

    # 控制台输出
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    # 文件输出
    try:
        os.makedirs(log_dir, exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")
        file_handler = logging.FileHandler(
            os.path.join(log_dir, f"score_{date_str}.log"),
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        # 日志目录不可写时，仅保留控制台输出
        pass

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """获取命名 logger（挂在 root logger 命名空间下）。"""
    if name:
        return logging.getLogger(f"{_ROOT_NAME}.{name}")
    return logging.getLogger(_ROOT_NAME)