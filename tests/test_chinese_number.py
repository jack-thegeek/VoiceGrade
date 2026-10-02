"""中文数字解析测试（对应 TODO 第 8、29 节）。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser.chinese_number import chinese_to_int, parse_int, parse_number_or_none


class TestChineseNumber(unittest.TestCase):
    def test_basic_digits(self):
        self.assertEqual(chinese_to_int("一"), 1)
        self.assertEqual(chinese_to_int("二"), 2)
        self.assertEqual(chinese_to_int("九"), 9)
        self.assertEqual(chinese_to_int("十"), 10)

    def test_tens(self):
        self.assertEqual(chinese_to_int("二十"), 20)
        self.assertEqual(chinese_to_int("二十一"), 21)
        self.assertEqual(chinese_to_int("九十五"), 95)

    def test_hundreds(self):
        self.assertEqual(chinese_to_int("一百"), 100)
        self.assertEqual(chinese_to_int("一百零五"), 105)
        self.assertEqual(chinese_to_int("一百二十三"), 123)

    def test_liang(self):
        self.assertEqual(chinese_to_int("两"), 2)

    def test_parse_int(self):
        self.assertEqual(parse_int("42"), 42)
        self.assertEqual(parse_int("100"), 100)
        self.assertEqual(parse_int("二十一"), 21)
        self.assertEqual(parse_int("１０"), 10)  # 全角

    def test_parse_none(self):
        self.assertIsNone(parse_number_or_none("abc"))
        self.assertEqual(parse_number_or_none("五"), 5)


if __name__ == "__main__":
    unittest.main()