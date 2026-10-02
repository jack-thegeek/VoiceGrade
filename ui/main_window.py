"""主窗口（对应 TODO 第 17、18、20 节）。

布局：
- 文件 / 班级 / 成绩项目选择
- 监听状态指示 + 实时识别文本
- 文本模拟输入（充当语音来源）
- 解析结果 / Excel 修改结果
- 开始 / 暂停 / 撤销 / 打开 Excel
- 最近操作历史
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.controller import ScoreVoiceController
from utils.logger import get_logger
from .widgets import StatusDot

log = get_logger("ui")

# 状态 -> 圆点颜色
_STATUS_COLORS = {
    "未连接": "#999999",
    "已连接 Excel": "#2e86de",
    "正在监听": "#10ac84",
    "正在识别": "#e1b12c",
    "正在处理": "#e1b12c",
    "修改成功": "#10ac84",
    "修改失败": "#e84118",
    "已暂停": "#f5a623",
    "未监听": "#999999",
}


class MainWindow(QMainWindow):
    def __init__(self, controller: ScoreVoiceController) -> None:
        super().__init__()
        self.controller = controller
        self.setWindowTitle("Excel 成绩语音录入系统")
        self.resize(720, 640)

        self._build_ui()
        self._connect_signals()

        # 启动后若配置了路径则自动打开（首次为空则不处理）
        default_path = controller._config.get("excel_path", "")
        if default_path:
            self._path_edit.setText(default_path)

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        # 文件
        file_box = QGroupBox("成绩表文件")
        fl = QHBoxLayout(file_box)
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("请选择成绩表 .xlsx")
        self._open_btn = QPushButton("打开成绩表")
        fl.addWidget(self._path_edit, 1)
        fl.addWidget(self._open_btn)
        root.addWidget(file_box)

        # 班级 / 成绩项目
        ctx_box = QGroupBox("当前上下文")
        cl = QGridLayout(ctx_box)
        cl.addWidget(QLabel("班级（工作表）："), 0, 0)
        self._sheet_combo = QComboBox()
        cl.addWidget(self._sheet_combo, 0, 1)
        cl.addWidget(QLabel("成绩项目："), 0, 2)
        self._score_combo = QComboBox()
        cl.addWidget(self._score_combo, 0, 3)
        root.addWidget(ctx_box)

        # 状态 + 识别文本
        status_box = QGroupBox("监听状态")
        sl = QVBoxLayout(status_box)
        top = QHBoxLayout()
        self._status_dot = StatusDot()
        self._status_label = QLabel("未连接")
        top.addWidget(self._status_dot)
        top.addWidget(self._status_label)
        top.addStretch(1)
        sl.addLayout(top)

        self._recognized_label = QLabel("实时识别：")
        self._recognized_label.setStyleSheet("color:#555;")
        sl.addWidget(self._recognized_label)
        root.addWidget(status_box)

        # 文本模拟输入
        sim_box = QGroupBox("命令输入（模拟语音）")
        il = QHBoxLayout(sim_box)
        self._input_edit = QLineEdit()
        self._input_edit.setPlaceholderText("例如：1号，100减2减8减10")
        self._send_btn = QPushButton("发送")
        il.addWidget(self._input_edit, 1)
        il.addWidget(self._send_btn)
        root.addWidget(sim_box)

        # 结果
        result_box = QGroupBox("解析 / 修改结果")
        rl = QGridLayout(result_box)
        self._result_student = QLabel("—")
        self._result_old = QLabel("—")
        self._result_calc = QLabel("—")
        self._result_new = QLabel("—")
        self._result_cell = QLabel("—")
        self._result_error = QLabel("")
        self._result_error.setStyleSheet("color:#e84118;")
        self._result_error.setWordWrap(True)

        rl.addWidget(QLabel("学生："), 0, 0)
        rl.addWidget(self._result_student, 0, 1)
        rl.addWidget(QLabel("原成绩："), 0, 2)
        rl.addWidget(self._result_old, 0, 3)
        rl.addWidget(QLabel("计算："), 1, 0)
        rl.addWidget(self._result_calc, 1, 1, 1, 3)
        rl.addWidget(QLabel("新成绩："), 2, 0)
        rl.addWidget(self._result_new, 2, 1)
        rl.addWidget(QLabel("单元格："), 2, 2)
        rl.addWidget(self._result_cell, 2, 3)
        rl.addWidget(self._result_error, 3, 0, 1, 4)
        root.addWidget(result_box)

        # 操作按钮
        btn_row = QHBoxLayout()
        self._listen_btn = QPushButton("开始监听")
        self._pause_btn = QPushButton("暂停")
        self._undo_btn = QPushButton("撤销")
        btn_row.addWidget(self._listen_btn)
        btn_row.addWidget(self._pause_btn)
        btn_row.addWidget(self._undo_btn)
        btn_row.addStretch(1)
        root.addLayout(btn_row)

        # 历史
        hist_box = QGroupBox("最近操作")
        hl = QVBoxLayout(hist_box)
        self._history_list = QListWidget()
        hl.addWidget(self._history_list)
        root.addWidget(hist_box, 1)

        self.setCentralWidget(central)

    def _connect_signals(self) -> None:
        c = self.controller

        self._open_btn.clicked.connect(self._choose_file)
        self._send_btn.clicked.connect(self._send)
        self._input_edit.returnPressed.connect(self._send)
        self._listen_btn.clicked.connect(self._start_listening)
        self._pause_btn.clicked.connect(self._pause_listening)
        self._undo_btn.clicked.connect(c.undo_last)

        self._sheet_combo.currentTextChanged.connect(self._on_sheet_changed)
        self._score_combo.currentTextChanged.connect(self._on_score_item_changed)

        c.status_changed.connect(self._on_status)
        c.recognized.connect(self._on_recognized)
        c.result_ready.connect(self._on_result)
        c.error.connect(self._on_error)
        c.structure_loaded.connect(self._on_structure)
        c.history_changed.connect(self._on_history)

    # ------------------------------------------------------------------
    def _choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择成绩表", "", "Excel 文件 (*.xlsx *.xlsm *.xls)"
        )
        if not path:
            return
        self._path_edit.setText(path)
        self.controller._config.set("excel_path", path)
        self.controller._config.save()
        self.controller.open_excel(path)

    def _send(self) -> None:
        text = self._input_edit.text().strip()
        if not text:
            return
        self._input_edit.clear()
        self.controller.submit_text(text)

    def _start_listening(self) -> None:
        self.controller.start_listening()
        self._input_edit.setFocus()

    def _pause_listening(self) -> None:
        self.controller.pause_listening()

    # ------------------------------------------------------------------
    def _on_sheet_changed(self, name: str) -> None:
        if name:
            self.controller.set_sheet(name)
            self.controller._config.set("sheet_name", name)
            self.controller._config.save()

    def _on_score_item_changed(self, item: str) -> None:
        if item:
            self.controller.set_score_item(item)
            self.controller._config.save()

    def _on_status(self, status: str) -> None:
        self._status_label.setText(status)
        self._status_dot.set_color(_STATUS_COLORS.get(status, "#999999"))

    def _on_recognized(self, text: str) -> None:
        self._recognized_label.setText(f"实时识别：{text}")

    def _on_structure(self, struct: dict) -> None:
        sheets = struct.get("sheet_names", [])
        items = struct.get("score_items", [])

        self._sheet_combo.blockSignals(True)
        self._sheet_combo.clear()
        self._sheet_combo.addItems(sheets)
        saved_sheet = self.controller._config.get("sheet_name", "")
        if saved_sheet in sheets:
            self._sheet_combo.setCurrentText(saved_sheet)
        self._sheet_combo.blockSignals(False)

        self._score_combo.blockSignals(True)
        self._score_combo.clear()
        self._score_combo.addItems(items)
        saved_item = self.controller._config.get("score_item", "")
        if saved_item in items:
            self._score_combo.setCurrentText(saved_item)
            self.controller.set_score_item(saved_item)
        elif items:
            self._score_combo.setCurrentIndex(0)
        self._score_combo.blockSignals(False)

    def _on_result(self, result: dict) -> None:
        op = result.get("operation")
        student = f"{result.get('student_no')} - {result.get('student_name')}"
        self._result_student.setText(student)
        self._result_old.setText(self._fmt(result.get("old_value")))
        self._result_new.setText(self._fmt(result.get("new_value")))
        self._result_cell.setText(result.get("cell", "—"))

        if op == "undo":
            self._result_calc.setText("撤销：已恢复原成绩")
        elif op == "subtract":
            self._result_calc.setText(
                f"当前成绩 − " + " − ".join(self._fmt(d) for d in result.get("deductions", []))
            )
        else:
            base = result.get("base_score")
            parts = [self._fmt(base)]
            parts += ["− " + self._fmt(d) for d in result.get("deductions", [])]
            self._result_calc.setText("  ".join(parts) if len(parts) > 1 else self._fmt(base))

        self._result_error.setText("")
        self._on_status("修改成功")

    def _on_error(self, message: str) -> None:
        self._result_error.setText(f"⚠ {message}")
        self._on_status("修改失败")

    def _on_history(self, lines: list[str]) -> None:
        self._history_list.clear()
        self._history_list.addItems(lines)

    @staticmethod
    def _fmt(value: object) -> str:
        if value is None:
            return "—"
        return str(value)

    def closeEvent(self, event) -> None:  # noqa: N802
        self.controller._config.save()
        self.controller.shutdown()
        super().closeEvent(event)


__all__ = ["MainWindow"]