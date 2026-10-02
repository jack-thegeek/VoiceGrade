"""中文数字解析（对应 TODO 第 8 节）。

不依赖 LLM，使用确定性代码把普通话常见数字表达转换为整数。

支持：
- 阿拉伯数字：1、21、100
- 中文数字：一、二、三、十、二十、二十一、一百、一百零五、九十五
- 大小写兼容：零/〇、二/两
"""
from __future__ import annotations

import re

_CN_DIGITS = {
    "零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}
_CN_SECTION_UNITS = {"十": 10, "百": 100, "千": 1000}
_CN_BIG_UNITS = {"万": 10000, "亿": 100000000}

_FULLWIDTH_DIGITS = str.maketrans(
    "０１２３４５６７８９", "0123456789"
)


def normalize_digits(text: str) -> str:
    """把全角数字转半角，方便后续正则匹配。"""
    return text.translate(_FULLWIDTH_DIGITS)


def chinese_to_int(text: str) -> int:
    """把纯中文数字字符串转换为 int。

    例如：二十一 -> 21；一百零五 -> 105；九十五 -> 95；十 -> 10；二十 -> 20。

    失败时抛出 ValueError。
    """
    s = str(text).strip()
    if not s:
        raise ValueError("空的中文数字")

    total = 0       # 万及以上单位累加的结果
    section = 0     # 当前节（万以内）的累加值
    number = 0      # 当前读到的单个数字
    for ch in s:
        if ch in _CN_DIGITS:
            number = _CN_DIGITS[ch]
        elif ch in _CN_SECTION_UNITS:
            unit = _CN_SECTION_UNITS[ch]
            if number == 0:
                number = 1
            section += number * unit
            number = 0
        elif ch in _CN_BIG_UNITS:
            unit = _CN_BIG_UNITS[ch]
            section = (section + number) * unit
            total += section
            section = 0
            number = 0
        else:
            # 忽略无关字符（如空格）
            continue
    total += section + number
    return total


def parse_int(text: object) -> int:
    """把阿拉伯数字或中文数字统一转换为 int。

    例如：42 -> 42；"100" -> 100；"二十一" -> 21。

    失败时抛出 ValueError。
    """
    s = str(text).strip()
    if not s:
        raise ValueError("空数字")
    s = normalize_digits(s)
    if re.fullmatch(r"[0-9]+", s):
        return int(s)
    # 只允许中文数字字符，避免把其它中文误判
    if re.fullmatch(r"[零〇一二两三四五六七八九十百千万亿]+", s):
        return chinese_to_int(s)
    raise ValueError(f"无法解析数字：{text}")


def parse_number_or_none(text: object) -> int | None:
    """解析数字，失败返回 None（不抛出）。"""
    try:
        return parse_int(text)
    except ValueError:
        return None


__all__ = ["chinese_to_int", "parse_int", "parse_number_or_none", "normalize_digits"]