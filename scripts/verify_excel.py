"""本机验证脚本：使用临时副本验证 Excel 读写链路，不触碰原始成绩表。

运行：
    python scripts/verify_excel.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from excel.excel_adapter import ExcelAdapter  # noqa: E402


def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = os.path.join(root, "成绩表.xlsx")
    if not os.path.exists(src):
        print(f"[失败] 找不到 {src}")
        return 1

    tmp_dir = tempfile.mkdtemp(prefix="score_verify_")
    dest = os.path.join(tmp_dir, "成绩表_验证副本.xlsx")
    shutil.copy2(src, dest)

    adapter = ExcelAdapter()
    adapter.connect(dest, visible=False)
    print(f"[OK] 已连接（副本）：{dest}")
    print(f"     工作表：{adapter.sheet_names}")
    print(f"     成绩列：{adapter.score_items}")
    print(f"     学生数：{len(adapter._student_rows)}")

    # 按序号查找
    r1 = adapter.find_student_row(1)
    print(f"[OK] 序号1 -> 行 {r1}，姓名 {adapter.student_name(1)}")

    # 验证非数字（请假）
    old42 = adapter.get_score(adapter.find_student_row(42), "第一单元")
    print(f"[OK] 序号42 当前成绩 = {old42!r}（应为「请假」）")

    # 写 -> 读 -> 回滚
    old1 = adapter.get_score(r1, "第一单元")
    adapter.set_score(r1, "第一单元", 80)
    assert adapter.get_score(r1, "第一单元") == 80, "写入后读取不一致"
    print(f"[OK] 写入 C{r1} = 80 -> 读回 80")
    adapter.set_score(r1, "第一单元", old1)  # 回滚
    assert adapter.get_score(r1, "第一单元") == old1, "回滚失败"
    print(f"[OK] 回滚 C{r1} = {old1}")
    adapter.save()
    adapter.close()
    shutil.rmtree(tmp_dir, ignore_errors=True)

    print("\n[全部通过] Excel 读写链路验证成功")
    return 0


if __name__ == "__main__":
    sys.exit(main())