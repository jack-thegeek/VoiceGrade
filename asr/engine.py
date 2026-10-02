"""ASR 引擎接口与工厂（对应 TODO 第 4、5 节）。

通过统一接口隔离「文本模拟」与「真实语音识别」，后续接入 FunASR
等本地引擎时无需改动命令处理链路。
"""
from __future__ import annotations

import numpy as np


class BaseASREngine:
    """ASR 引擎基类。"""

    name = "base"

    def transcribe(self, audio: np.ndarray, sample_rate: int) -> str:
        raise NotImplementedError

    def warmup(self) -> None:
        """可选：加载/预热模型。"""

    def shutdown(self) -> None:
        """可选：释放资源。"""


class TextASREngine(BaseASREngine):
    """文本模拟引擎：不识别音频，仅返回空文本。

    语音文本由 GUI 的输入框直接注入命令处理链路，本引擎用于
    保持接口统一与「开始监听」状态展示。
    """

    name = "text"

    def transcribe(self, audio: np.ndarray, sample_rate: int) -> str:  # noqa: ARG002
        return ""


def create_engine(engine_name: str, **kwargs) -> BaseASREngine:
    """按名称创建 ASR 引擎。"""
    engine_name = (engine_name or "text").lower()
    if engine_name in ("text", "mock", "simulate"):
        return TextASREngine()
    if engine_name in ("funasr", "paraformer"):
        from .funasr_engine import FunASREngine

        return FunASREngine(**kwargs)
    raise ValueError(f"未知的 ASR 引擎：{engine_name}")


__all__ = ["BaseASREngine", "TextASREngine", "create_engine"]