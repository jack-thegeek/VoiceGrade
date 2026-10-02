"""Excel 适配层（对应 TODO 第 13、21、22、23、24 节）。

通过 xlwings / COM 直接操作正在运行的 Excel，实现：
- 打开工作簿 / 连接已打开的 Excel
- 自动发现工作表与成绩列
- 依据 A 列「序号」查找学生行（原则 4，不依赖行号）
- 读取 / 写入成绩、保存、选中单元格、激活 Excel

注意：此类必须在持久的 Excel Worker 线程中实例化与调用，
线程内需先调用 pythoncom.CoInitialize()。
"""
from __future__ import annotations

import os
from typing import Optional

# 统计区域标记（第 51~53 行），遇到即停止学生数据扫描
STAT_LABELS = {"平均分", "合格率", "优秀率"}

# 读取表头/学生时的安全上限
_MAX_SCAN_ROWS = 2000
_MAX_SCAN_COLS = 52


class ExcelAdapterError(Exception):
    """Excel 操作失败，携带面向用户的中文提示。"""


def col_letter(index_1based: int) -> str:
    """1-based 列号转字母，例如 1->A、3->C。"""
    s = ""
    n = index_1based
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


class ExcelAdapter:
    def __init__(self) -> None:
        self.app = None
        self.wb = None
        self.sheet = None
        self.path: str = ""

        # 结构缓存
        self.sheet_names: list[str] = []
        self.score_items: list[str] = []            # 有序成绩列名
        self.score_column_of: dict[str, str] = {}   # 成绩项 -> 列字母
        self._no_col = 1                            # 「序号」列
        self._name_col = 2                          # 「姓名」列
        self._student_rows: dict[str, int] = {}     # 序号 -> Excel 行号
        self._student_names: dict[str, str] = {}    # 序号 -> 姓名
        self._first_data_row = 3
        self._last_data_row = 0

    # ------------------------------------------------------------------
    # 连接 / 打开
    # ------------------------------------------------------------------
    def connect(self, path: str, sheet_name: Optional[str] = None,
                visible: bool = True) -> None:
        import xlwings as xw

        path = os.path.abspath(path)
        if not os.path.exists(path):
            raise ExcelAdapterError(f"文件不存在：{path}")

        # 优先复用用户已打开的 Excel 实例
        target = None
        try:
            for app in xw.apps:
                for wb in app.books:
                    try:
                        if os.path.abspath(str(wb.fullname)).lower() == path.lower():
                            target = (app, wb)
                            break
                    except Exception:
                        continue
                if target:
                    break
        except Exception:
            target = None

        try:
            if target:
                self.app, self.wb = target
            else:
                self.app = xw.App(visible=visible, add_book=False)
                self.wb = self.app.books.open(path)
        except Exception as e:  # noqa: BLE001
            raise ExcelAdapterError(f"打开 Excel 失败：{e}") from e

        self.path = path
        self.sheet_names = [s.name for s in self.wb.sheets]

        if sheet_name and sheet_name in self.sheet_names:
            self.sheet = self.wb.sheets(sheet_name)
        elif self.sheet_names:
            self.sheet = self.wb.sheets(1)

        self.load_structure()

    # ------------------------------------------------------------------
    # 结构读取
    # ------------------------------------------------------------------
    def set_sheet(self, sheet_name: str) -> None:
        if not self.wb:
            raise ExcelAdapterError("尚未连接 Excel")
        self.sheet = self.wb.sheets(sheet_name)
        self.load_structure()

    def load_structure(self) -> None:
        """读取第 2 行表头，动态识别「序号/姓名」列与成绩列。"""
        if self.sheet is None:
            raise ExcelAdapterError("尚未选择工作表")
        self._load_headers()
        self._scan_students()

    def _read_row(self, row: int, ncols: int) -> list:
        """读取第 row 行第 1..ncols 列，返回长度 ncols 的列表（空单元格为 None）。"""
        value = self.sheet.range((row, 1), (row, ncols)).value
        if value is None:
            value = []
        elif not isinstance(value, (list, tuple)):
            value = [value]
        value = list(value)
        while len(value) < ncols:
            value.append(None)
        return value[:ncols]

    def _load_headers(self) -> None:
        values = self._read_row(2, _MAX_SCAN_COLS)
        self.score_items = []
        self.score_column_of = {}
        # 默认序号/姓名取 A/B 列；若表头换了位置则动态修正
        for i, v in enumerate(values, start=1):
            if v is None:
                continue
            s = str(v).strip()
            if s == "":
                continue
            if s == "序号":
                self._no_col = i
            elif s == "姓名":
                self._name_col = i
            else:
                self.score_items.append(s)
                self.score_column_of[s] = col_letter(i)

    def _scan_students(self) -> None:
        """扫描学生数据行（第 3 行起，直到统计区域或空行）。"""
        self._student_rows = {}
        self._student_names = {}
        row = self._first_data_row = 3
        self._last_data_row = 0
        while row <= _MAX_SCAN_ROWS:
            v_no = self.sheet.range((row, self._no_col)).value
            if v_no is None:
                break
            label = str(v_no).strip()
            if label == "":
                break
            if label in STAT_LABELS:
                break
            key = self._canonical_no(v_no)
            self._student_rows[key] = row
            name = self.sheet.range((row, self._name_col)).value
            self._student_names[key] = "" if name is None else str(name).strip()
            self._last_data_row = row
            row += 1

    # ------------------------------------------------------------------
    # 学生 / 成绩访问
    # ------------------------------------------------------------------
    @staticmethod
    def _canonical_no(value: object) -> str:
        """把序号统一为字符串键（1.0 -> "1"，保留字符串原样）。"""
        if isinstance(value, bool):
            return str(value)
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value).strip()

    @staticmethod
    def _normalize_number(value: object) -> object:
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value

    def find_student_row(self, student_no: int) -> Optional[int]:
        return self._student_rows.get(self._canonical_no(student_no))

    def student_name(self, student_no: int) -> str:
        return self._student_names.get(self._canonical_no(student_no), "")

    def get_score(self, row: int, score_item: str) -> object:
        col = self.score_column_of[score_item]
        return self._normalize_number(self.sheet.range(f"{col}{row}").value)

    def set_score(self, row: int, score_item: str, value: object) -> None:
        col = self.score_column_of[score_item]
        self.sheet.range(f"{col}{row}").value = value

    def cell_address(self, row: int, score_item: str) -> str:
        return f"{self.score_column_of[score_item]}{row}"

    # ------------------------------------------------------------------
    # 保存 / 选中 / 激活
    # ------------------------------------------------------------------
    def save(self) -> None:
        if not self.wb:
            return
        try:
            self.wb.save()
        except Exception as e:  # noqa: BLE001
            raise ExcelAdapterError(f"保存 Excel 失败：{e}") from e

    def select_cell(self, row: int, score_item: str) -> None:
        col = self.score_column_of[score_item]
        self.sheet.range(f"{col}{row}").select()

    def activate_excel(self) -> None:
        if self.app is not None:
            try:
                self.app.activate(steal_focus=True)
            except Exception:  # noqa: BLE001
                pass

    def close(self) -> None:
        """关闭连接（不保存，避免误改）。"""
        try:
            if self.app is not None:
                self.app.quit()
        except Exception:  # noqa: BLE001
            pass
        finally:
            self.app = None
            self.wb = None
            self.sheet = None


__all__ = ["ExcelAdapter", "ExcelAdapterError", "col_letter"]