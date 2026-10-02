"""Qt 全链路集成测试：文本 -> 解析 -> Excel（临时副本，不碰原表）。

    python scripts/verify_e2e.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QCoreApplication

from core.controller import ScoreVoiceController
from utils.config import Config

results: list[dict] = []
errors: list[str] = []
structures: list[dict] = []


def _wait(predicate, timeout=15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return False


def main() -> int:
    global app
    app = QCoreApplication(sys.argv)

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = os.path.join(root, "成绩表.xlsx")
    tmp_dir = tempfile.mkdtemp(prefix="score_e2e_")
    dest = os.path.join(tmp_dir, "成绩表_集成副本.xlsx")
    shutil.copy2(src, dest)

    config = Config()
    config.set("excel_visible", False)
    config.set("excel_path", dest)
    config.set("auto_save", True)
    config.set("activate_excel", False)

    controller = ScoreVoiceController(config)

    def on_result(r):
        results.append(r)

    def on_error(e):
        errors.append(e)

    def on_structure(s):
        structures.append(s)

    controller.result_ready.connect(on_result)
    controller.error.connect(on_error)
    controller.structure_loaded.connect(on_structure)

    controller.start()
    controller.open_excel(dest)

    ok = _wait(lambda: structures, 20)
    if not ok:
        print("[失败] 打开 Excel 超时")
        controller.shutdown()
        return 1
    struct = structures[-1]
    print(f"[OK] 连接：工作表 {struct['sheet_names']} 成绩列 {struct['score_items']} "
          f"学生 {struct['student_count']} 名")
    controller.set_score_item("第一单元")

    checks = []

    def check(text, expect_has, label, target="new"):
        results.clear()
        errors.clear()
        controller.submit_text(text)
        finished = _wait(lambda: results or errors, 10)
        if not finished:
            checks.append((label, False, "超时无响应"))
            return
        if errors:
            checks.append((label, False, f"错误：{errors[-1]}"))
            return
        r = results[-1]
        got = r.get(target if target == "new" else "error")
        actual = r.get("new_value") if target == "new" else None
        checks.append((label, True, f"{r.get('cell')} {r.get('old_value')} -> {r.get('new_value')}"))

    # 期望成功：80
    results.clear(); errors.clear()
    controller.submit_text("1号，100减2减8减10")
    _wait(lambda: results or errors, 10)
    checks.append((
        "100减2减8减10=80", not errors and results
        and results[-1].get("new_value") == 80,
        f"cell={results[-1].get('cell')} new={results[-1].get('new_value')} "
        f"err={errors}" if results or errors else "无响应"
    ))

    # 再扣：当前 80 -> 80-5=75
    results.clear(); errors.clear()
    controller.submit_text("1号，再扣5分")
    _wait(lambda: results or errors, 10)
    checks.append((
        "再扣5分 80->75", not errors and results
        and results[-1].get("new_value") == 75,
        f"new={results[-1].get('new_value')} err={errors}" if results or errors else "无响应"
    ))

    # 非数字：42 号请假
    results.clear(); errors.clear()
    controller.submit_text("42号，再扣5分")
    _wait(lambda: results or errors, 10)
    checks.append(("请假拒改", bool(errors) and not results, errors[-1] if errors else "未拒绝"))

    # 未找到学生：99
    results.clear(); errors.clear()
    controller.submit_text("99号，100减5")
    _wait(lambda: results or errors, 10)
    checks.append(("99号不存在拒改", bool(errors), errors[-1] if errors else "未拒绝"))

    # 越界：100 减 200
    results.clear(); errors.clear()
    controller.submit_text("1号，100减200")
    _wait(lambda: results or errors, 10)
    checks.append(("越界拒改", bool(errors), errors[-1] if errors else "未拒绝"))

    # 撤销：把 75 恢复到 80
    results.clear(); errors.clear()
    controller.undo_last()
    _wait(lambda: results or errors, 10)
    checks.append((
        "撤销恢复80", not errors and results
        and results[-1].get("operation") == "undo"
        and results[-1].get("new_value") == 80,
        f"new={results[-1].get('new_value')} err={errors}" if results or errors else "无响应"
    ))

    controller.shutdown()
    shutil.rmtree(tmp_dir, ignore_errors=True)

    print("\n=== 结果 ===")
    passed = 0
    for label, okk, detail in checks:
        mark = "PASS" if okk else "FAIL"
        print(f"[{mark}] {label}  {detail}")
        passed += okk

    print(f"\n{passed}/{len(checks)} 通过")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())