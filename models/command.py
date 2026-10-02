"""核心数据模型。

对应 TODO 第 12、16 节：
- ParsedCommand：Parser 输出的统一结构
- HistoryItem：修改历史 / 撤销记录
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ParsedCommand:
    """一条解析后的语音命令。

    operation:
        "set"       —— 绝对成绩：base_score - 扣分项（例如 100减2减8减10）
        "subtract"  —— "再扣"：读取当前成绩后减去 deductions

    注意：Parser 只负责解析，不修改 Excel。
    """

    student_no: int
    score_item: Optional[str] = None
    operation: str = "set"
    base_score: Optional[float] = None
    deductions: list[float] = field(default_factory=list)
    final_score: Optional[float] = None
    confidence: float = 1.0
    raw_text: str = ""


@dataclass
class HistoryItem:
    """一次成功的 Excel 修改记录。"""

    sheet_name: str
    cell_address: str
    student_no: int
    student_name: str
    score_item: str
    old_value: object
    new_value: object
    recognized_text: str
    timestamp: datetime = field(default_factory=datetime.now)

    def describe(self) -> str:
        t = self.timestamp.strftime("%H:%M:%S")
        return f"{t}  {self.student_no}号  {self.cell_address}  {self.old_value} → {self.new_value}"