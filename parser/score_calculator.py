"""成绩计算与范围校验（对应 TODO 第 9、11 节）。

数学运算必须使用确定性代码（原则 1），不允许用 LLM 计算分数。
"""
from __future__ import annotations

from typing import Iterable


class ScoreCalculator:
    """根据 operation 计算最终成绩，并校验 0~100 范围。"""

    def __init__(self, min_score: float = 0, max_score: float = 100) -> None:
        self.min_score = min_score
        self.max_score = max_score

    # ---- 计算 ----

    def compute(self, operation: str, base_score: float | None = None,
                deductions: Iterable[float] = (),
                current_score: float | None = None) -> float:
        """计算最终成绩。

        operation == "set"：
            final = base_score - sum(deductions)
        operation == "subtract"：
            final = current_score - sum(deductions)   （再扣模式）
        """
        deduct = sum(float(d) for d in deductions)
        if operation == "subtract":
            if current_score is None:
                raise ValueError("再扣模式缺少当前成绩")
            result = float(current_score) - deduct
        else:
            if base_score is None:
                raise ValueError("缺少基准成绩")
            result = float(base_score) - deduct
        return self._normalize(result)

    def set_exact(self, value: float) -> float:
        """直接设置成绩（无扣分项）。"""
        return self._normalize(value)

    # ---- 校验 ----

    def validate(self, score: object) -> bool:
        """成绩是否在合法范围内（且是数字）。"""
        if not self._is_number(score):
            return False
        return self.min_score <= float(score) <= self.max_score

    @staticmethod
    def _is_number(value: object) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    # ---- 内部 ----

    @staticmethod
    def _normalize(value: float) -> float:
        """四舍五入到 1 位小数；若为整数则返回 int。"""
        v = round(float(value) + 1e-9, 1)
        if abs(v - round(v)) < 1e-6:
            return int(round(v))
        return v


__all__ = ["ScoreCalculator"]