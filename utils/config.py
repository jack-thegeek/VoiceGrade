"""配置的加载、保存与访问。

对应 TODO 第 26 节：config.json 保存班级、成绩项目、分数范围等设置。
"""
from __future__ import annotations

import json
import os
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "excel_path": "成绩表.xlsx",
    "sheet_name": "",
    "score_item": "第一单元",
    "min_score": 0,
    "max_score": 100,
    "auto_save": True,
    "activate_excel": True,
    "select_cell": True,
    "excel_visible": True,
    "asr_engine": "text",       # text | funasr | sherpa-onnx
    "vad_enabled": True,
    "sample_rate": 16000,
}


class Config:
    """简单的 JSON 配置文件封装。"""

    def __init__(self, path: str = "config.json") -> None:
        self.path = path
        self._data: dict[str, Any] = dict(DEFAULT_CONFIG)
        self.load()

    def load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._data.update(data)
        except (OSError, json.JSONDecodeError):
            # 配置文件损坏时静默回退到默认值
            pass

    def save(self) -> bool:
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            return True
        except OSError:
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def as_dict(self) -> dict[str, Any]:
        return dict(self._data)