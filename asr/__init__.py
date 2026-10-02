"""语音识别（ASR）包。

提供统一的 BaseASREngine 接口，以及：
- TextEngine：文本模拟（直接充当「语音文本」来源）
- WinRTSpeechEngine：Windows 自带识别（WinRT，中文普通话，默认）
- FunASREngine：本地中文识别（可选，需安装 funasr）
"""
from .engine import BaseASREngine, TextASREngine, create_engine

__all__ = ["BaseASREngine", "TextASREngine", "create_engine"]