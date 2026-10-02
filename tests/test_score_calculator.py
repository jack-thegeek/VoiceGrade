"""成绩计算测试（对应 TODO 第 9、10、11、29 节）。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser.score_calculator import ScoreCalculator


class TestScoreCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = ScoreCalculator(0, 100)

    def test_set(self):
        # 100 - 2 - 8 - 10 = 80
        self.assertEqual(self.calc.compute("set", base_score=100, deductions=[2, 8, 10]), 80)
        # 95 - 5 = 90
        self.assertEqual(self.calc.compute("set", base_score=95, deductions=[5]), 90)
        # 88 - 3 - 2 = 83
        self.assertEqual(self.calc.compute("set", base_score=88, deductions=[3, 2]), 83)

    def test_subtract(self):
        # 当前 92，再扣5 => 87
        self.assertEqual(self.calc.compute("subtract", current_score=92, deductions=[5]), 87)
        # 当前 87.5，再扣5 => 82.5
        self.assertEqual(self.calc.compute("subtract", current_score=87.5, deductions=[5]), 82.5)

    def test_range(self):
        self.assertTrue(self.calc.validate(0))
        self.assertTrue(self.calc.validate(100))
        self.assertFalse(self.calc.validate(-5))
        self.assertFalse(self.calc.validate(110))
        self.assertFalse(self.calc.validate("请假"))

    def test_normalize(self):
        self.assertIsInstance(self.calc.compute("set", 100, [20]), int)
        self.assertEqual(self.calc.compute("set", base_score=100, deductions=[20]), 80)


if __name__ == "__main__":
    unittest.main()