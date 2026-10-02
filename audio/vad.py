"""语音活动检测 VAD（对应 TODO 第 4 节）。

优先使用 Silero VAD（本地，精度高）；若未安装则回退到基于能量的
简单端点检测，保证 MVP 可运行。
"""
from __future__ import annotations

import numpy as np


class EnergyVAD:
    """基于短时能量的简单 VAD。"""

    def __init__(self, threshold: float = 0.02) -> None:
        self.threshold = threshold

    def is_speech(self, frame: np.ndarray) -> bool:
        if frame is None or frame.size == 0:
            return False
        rms = float(np.sqrt(np.mean(np.square(frame, dtype=np.float64))))
        return rms > self.threshold


class SileroVAD:
    """Silero VAD 封装（需要安装 silero-vad / onnxruntime）。"""

    def __init__(self, threshold: float = 0.5) -> None:
        try:
            import torch  # noqa: F401
            from silero_vad import load_silero_vad  # type: ignore

            self._model = load_silero_vad()
            self.threshold = threshold
            self._use_threshold = True
        except ImportError as e:  # noqa: BLE001
            raise RuntimeError("未安装 silero-vad，请安装后重试") from e

    def is_speech(self, frame: np.ndarray) -> bool:
        if frame is None or frame.size == 0:
            return False
        import torch

        x = torch.from_numpy(frame.astype(np.float32))
        prob = self._model(x, 16000).item()
        return prob > self.threshold


def create_vad(method: str = "energy", **kwargs) -> object:
    """工厂方法：按名称创建 VAD 实例。"""
    if method in ("silero", "auto"):
        try:
            return SileroVAD(**kwargs)
        except RuntimeError:
            return EnergyVAD(**kwargs)
    return EnergyVAD(**kwargs)


__all__ = ["EnergyVAD", "SileroVAD", "create_vad"]