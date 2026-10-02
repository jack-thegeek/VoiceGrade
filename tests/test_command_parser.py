"""命令解析测试（对应 TODO 第 3、9、10、29 节）。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser.command_parser import CommandParser, ParseError


class TestCommandParser(unittest.TestCase):
    def setUp(self):
        self.parser = CommandParser()
        self.ctx = "第一单元"
        self.items = ["第一单元", "第二单元", "期中考试"]

    def test_set_ban(self):
        cmd = self.parser.parse("1号，100减2减8减10", self.ctx, self.items)
        self.assertEqual(cmd.student_no, 1)
        self.assertEqual(cmd.operation, "set")
        self.assertEqual(cmd.base_score, 100)
        self.assertEqual(cmd.deductions, [2, 8, 10])
        self.assertEqual(cmd.final_score, 80)
        self.assertEqual(cmd.score_item, "第一单元")

    def test_set_ban_two_words(self):
        cmd = self.parser.parse("2号，100减5", self.ctx, self.items)
        self.assertEqual(cmd.student_no, 2)
        self.assertEqual(cmd.final_score, 95)

    def test_set_kai(self):
        cmd = self.parser.parse("3号，100扣2扣8扣10", self.ctx, self.items)
        self.assertEqual(cmd.deductions, [2, 8, 10])
        self.assertEqual(cmd.final_score, 80)

    def test_set_minus(self):
        cmd = self.parser.parse("4号，100-2-8-10", self.ctx, self.items)
        self.assertEqual(cmd.final_score, 80)

    def test_set_with_fen(self):
        cmd = self.parser.parse("1号，100分，扣2分、8分、10分", self.ctx, self.items)
        self.assertEqual(cmd.final_score, 80)

    def test_subtract(self):
        cmd = self.parser.parse("5号，再扣5分", self.ctx, self.items)
        self.assertEqual(cmd.student_no, 5)
        self.assertEqual(cmd.operation, "subtract")
        self.assertEqual(cmd.deductions, [5])

    def test_sequence_forms(self):
        # 序号 / 学号 / 第N号
        self.assertEqual(self.parser.parse("序号7，100减3", self.ctx, self.items).student_no, 7)
        self.assertEqual(self.parser.parse("学号8，95减5", self.ctx, self.items).student_no, 8)
        self.assertEqual(self.parser.parse("第9号，100减10", self.ctx, self.items).student_no, 9)

    def test_chinese_student_no(self):
        cmd = self.parser.parse("二十一号，100减10", self.ctx, self.items)
        self.assertEqual(cmd.student_no, 21)

    def test_explicit_score_item(self):
        cmd = self.parser.parse("1号期中考试，100减5", self.ctx, self.items)
        self.assertEqual(cmd.score_item, "期中考试")

    def test_error_no_student(self):
        with self.assertRaises(ParseError):
            self.parser.parse("100减2", self.ctx, self.items)

    def test_error_no_item(self):
        with self.assertRaises(ParseError):
            self.parser.parse("1号，100减2", None, [])


if __name__ == "__main__":
    unittest.main()