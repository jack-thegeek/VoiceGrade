"""语音命令解析器（对应 TODO 第 3、6、7、9、10、12、15 节）。

把识别出的中文文本解析为 ParsedCommand。解析失败抛出 ParseError，
调用方据此拒绝修改 Excel（原则 2、3：宁可不修改，也不能误修改）。
"""
from __future__ import annotations

import re
from typing import Iterable, Optional

from models.command import ParsedCommand
from . import chinese_number as cn
from .score_calculator import ScoreCalculator

_NUM_TOKEN = r"[0-9]+(?:\.[0-9]+)?|[零〇一二两三四五六七八九十百千万亿]+"

# 学号表达形式：
#   第5号 / 第5个 / 第5名 / 第五号 / 序号1 / 学号1 / 5号 / 1号
_STUDENT_PATTERNS: list[re.Pattern] = [
    re.compile(r"第\s*(" + _NUM_TOKEN + r")\s*(?:号|个|名|位)"),
    re.compile(r"(?:序号|学号)\s*[:：]?\s*(" + _NUM_TOKEN + r")"),
    re.compile(r"(" + _NUM_TOKEN + r")\s*号"),
]

# 再扣 / 再减 / 又扣 / 又减 / 继续扣 等相对操作标记
_RELATIVE_MARK = re.compile(r"(?:再|又|还|继续)?\s*[扣减]", re.IGNORECASE)

# 数字提取
_NUM_RE = re.compile(_NUM_TOKEN)

# 需要清除的分隔/标点/量词字符
_SEPARATORS = " \t\r\n,，、。;；:：·・"


class ParseError(Exception):
    """命令解析失败，携带面向用户的中文原因。"""


def _strip_separators(text: str) -> str:
    return text.translate(str.maketrans("", "", _SEPARATORS))


def _extract_numbers(text: str) -> list[float]:
    """按顺序提取文本中所有数字（阿拉伯/中文）。"""
    out: list[float] = []
    for m in _NUM_RE.finditer(text):
        raw = m.group()
        try:
            out.append(float(cn.parse_int(raw)))
        except ValueError:
            continue
    return out


def _extract_student(text: str) -> tuple[Optional[int], tuple[int, int]]:
    """提取学号，返回 (学号, 匹配区间)。未匹配返回 (None, (0,0))。"""
    for pat in _STUDENT_PATTERNS:
        m = pat.search(text)
        if m:
            try:
                return cn.parse_int(m.group(1)), m.span()
            except ValueError:
                continue
    # 兜底：句首「裸数字 + 分隔符」，例如 "1，100减2"
    m = re.match(r"^\s*([0-9]{1,3})\s*(?=[\s,，、;；:：]|$)", text)
    if m:
        return int(m.group(1)), m.span()
    return None, (0, 0)


def _extract_score_item(text: str, known_items: Iterable[str]) -> Optional[str]:
    """在文本中查找显式指定的成绩项目。"""
    items = sorted((i for i in known_items if i), key=len, reverse=True)
    for item in items:
        if item in text:
            return item
    return None


class CommandParser:
    """文本 -> ParsedCommand。"""

    def __init__(self, calculator: Optional[ScoreCalculator] = None) -> None:
        self.calculator = calculator or ScoreCalculator()

    def parse(self, text: str, context_score_item: Optional[str] = None,
              known_score_items: Optional[Iterable[str]] = None) -> ParsedCommand:
        raw = (text or "").strip()
        if not raw:
            raise ParseError("未识别到语音内容")

        normalized = cn.normalize_digits(raw)

        # 1. 学号
        student_no, span = _extract_student(normalized)
        if student_no is None:
            raise ParseError("未识别学号（请使用「1号」「序号1」「学号1」等）")
        rest = normalized[: span[0]] + normalized[span[1]:]

        # 2. 成绩项目（语音显式指定优先于界面上下文中）
        known = list(known_score_items or [])
        score_item = _extract_score_item(rest, known)
        if score_item is None:
            score_item = context_score_item
        if not score_item:
            raise ParseError("未识别成绩项目（请先在界面选择「成绩项目」）")
        if score_item in rest:
            rest = rest.replace(score_item, "", 1)

        # 3. 表达式
        expr = _strip_separators(rest)

        relative = _RELATIVE_MARK.match(expr.lstrip())
        if relative:
            nums = _extract_numbers(expr)
            if not nums:
                raise ParseError("扣分金额不完整（例如「再扣5分」）")
            return ParsedCommand(
                student_no=student_no,
                score_item=score_item,
                operation="subtract",
                deductions=[float(n) for n in nums],
                raw_text=raw,
            )

        nums = _extract_numbers(expr)
        if not nums:
            raise ParseError("未识别成绩表达式")

        if len(nums) == 1:
            # 只有一个数字：直接设置该成绩，例如 "98分"
            base_score: Optional[float] = nums[0]
            deductions: list[float] = []
        else:
            base_score = nums[0]
            deductions = [float(n) for n in nums[1:]]

        final = self.calculator.compute("set", base_score=base_score, deductions=deductions)

        return ParsedCommand(
            student_no=student_no,
            score_item=score_item,
            operation="set",
            base_score=base_score,
            deductions=deductions,
            final_score=final,
            raw_text=raw,
        )


__all__ = ["CommandParser", "ParseError"]