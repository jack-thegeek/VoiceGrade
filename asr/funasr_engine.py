"""FunASR（Paraformer）本地中文识别引擎（对应 TODO 第 4 节）。

依赖较重：pip install funasr modelscope torch torchaudio
并需要下载模型。未安装时创建实例会抛出带安装提示的 RuntimeError。
"""
from __future__ import annotations

import numpy as np

from .engine import BaseASREngine


class FunASREngine(BaseASREngine):
    name = "funasr"

    def __init__(self, model: str = "paraformer-zh") -> None:
        try:
            from funasr import AutoModel  # type: ignore
        except ImportError as e:  # noqa: BLE001
            raise RuntimeError(
                "未安装 FunASR。请执行：pip install funasr modelscope torch torchaudio"
            ) from e

        self._model = AutoModel(model=model)

    def warmup(self) -> None:
        pass

    def transcribe(self, audio: np.ndarray, sample_rate: int) -> str:
        if audio is None or audio.size == 0:
            return ""
        result = self._model.generate(input=audio, fs=sample_rate,)
        if not result:
            return ""
        # FunASR 常见返回：[{'key':..., 'text': '...'}]
        text = result[0].get("text", "") if isinstance(result, list) else str(result)
        return text.strip()

    def shutdown(self) -> None:
        self._model = None


__all__ = ["FunASREngine"]