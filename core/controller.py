"""核心控制器（对应 TODO 第 5、8、14、18~20 节）。

职责：
- ExcelWorker：独立线程内拥有 ExcelAdapter（COM 线程安全），
  通过线程安全队列接收命令，避免阻塞 GUI（原则 8）。
- ScoreVoiceController：QObject，串起「文本 -> 解析 -> Excel -> 历史」，
  通过 Qt Signal/Slot 与 GUI 通信，主线程不直接触碰 xlwings。
"""
from __future__ import annotations

import queue
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from excel.excel_adapter import ExcelAdapter, ExcelAdapterError
from history.history_manager import HistoryManager
from models.command import HistoryItem, ParsedCommand
from parser.command_parser import CommandParser, ParseError
from parser.score_calculator import ScoreCalculator
from utils.logger import get_logger

log = get_logger("controller")


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class ExcelWorker(QThread):
    """独占线程：所有 xlwings / COM 操作都在此线程执行。"""

    sig_status = Signal(str)
    sig_result = Signal(dict)
    sig_error = Signal(str)
    sig_structure = Signal(dict)

    def __init__(self, config, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._queue: "queue.Queue" = queue.Queue()
        self._running = True
        self.adapter: Optional[ExcelAdapter] = None

    # ---- 线程入口 ----
    def run(self) -> None:
        try:
            import pythoncom  # pywin32，随 xlwings 安装

            pythoncom.CoInitialize()
        except ImportError:
            pass

        try:
            self.adapter = ExcelAdapter()
            while self._running:
                try:
                    task = self._queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                if task is None:
                    break
                self._handle(task)
        finally:
            try:
                import pythoncom

                pythoncom.CoUninitialize()
            except ImportError:
                pass

    # ---- 对外接口（线程安全）----
    def submit(self, task: tuple) -> None:
        self._queue.put(task)

    def stop(self) -> None:
        self._running = False
        self._queue.put(None)

    # ---- 任务处理（本线程内）----
    def _handle(self, task: tuple) -> None:
        action = task[0]
        try:
            if action == "open":
                self._do_open(task[1], task[2] if len(task) > 2 else None)
            elif action == "set_sheet":
                self.adapter.set_sheet(task[1])
                self._emit_structure()
            elif action == "process":
                self._do_process(task[1])
            elif action == "undo":
                self._do_undo(task[1])
        except ExcelAdapterError as e:
            log.error("Excel 错误：%s", e)
            self.sig_error.emit(str(e))
        except Exception as e:  # noqa: BLE001
            log.exception("Excel 未预期异常")
            self.sig_error.emit(f"Excel 操作异常：{e}")

    def _do_open(self, path: str, sheet_name: Optional[str]) -> None:
        self.sig_status.emit("正在连接 Excel ...")
        self.adapter.connect(
            path, sheet_name=sheet_name,
            visible=bool(self._config.get("excel_visible", True)),
        )
        self._emit_structure()
        self.sig_status.emit("已连接 Excel")

    def _emit_structure(self) -> None:
        self.sig_structure.emit({
            "sheet_names": list(self.adapter.sheet_names),
            "score_items": list(self.adapter.score_items),
            "student_count": len(self.adapter._student_rows),
        })

    def _do_process(self, cmd: ParsedCommand) -> None:
        adapter = self.adapter
        if adapter is None or adapter.sheet is None:
            self.sig_error.emit("尚未连接 Excel，请先打开成绩表")
            return

        row = adapter.find_student_row(cmd.student_no)
        if row is None:
            self.sig_error.emit(f"未找到学生：序号 {cmd.student_no}")
            return

        score_item = cmd.score_item
        if score_item not in adapter.score_column_of:
            self.sig_error.emit(f"未找到成绩列：{score_item}")
            return

        old_value = adapter.get_score(row, score_item)
        calc = ScoreCalculator(self._config.get("min_score", 0),
                               self._config.get("max_score", 100))

        # 计算新成绩
        if cmd.operation == "subtract":
            if not _is_number(old_value):
                self.sig_error.emit(f"当前成绩不是数字：{old_value}")
                return
            final = calc.compute("subtract", current_score=float(old_value),
                                 deductions=cmd.deductions)
        else:
            final = calc.compute("set", base_score=cmd.base_score,
                                 deductions=cmd.deductions)

        # 范围校验
        if not calc.validate(final):
            self.sig_error.emit(
                f"计算结果超出 {self._config.get('min_score', 0)}~"
                f"{self._config.get('max_score', 100)} 范围：{final}"
            )
            return

        cell = adapter.cell_address(row, score_item)
        adapter.set_score(row, score_item, final)
        if self._config.get("auto_save", True):
            adapter.save()
        if self._config.get("select_cell", True):
            adapter.select_cell(row, score_item)
        if self._config.get("activate_excel", True):
            adapter.activate_excel()

        name = adapter.student_name(cmd.student_no)
        result = {
            "sheet_name": adapter.sheet.name if adapter.sheet else "",
            "raw_text": cmd.raw_text,
            "student_no": cmd.student_no,
            "student_name": name,
            "score_item": score_item,
            "operation": cmd.operation,
            "base_score": cmd.base_score,
            "deductions": list(cmd.deductions),
            "final_score": final,
            "old_value": old_value,
            "new_value": final,
            "cell": cell,
        }
        log.info("voice=%r student=%s name=%s item=%s cell=%s old=%s new=%s",
                 cmd.raw_text, cmd.student_no, name, score_item, cell,
                 old_value, final)
        self.sig_result.emit(result)

    def _do_undo(self, item: HistoryItem) -> None:
        adapter = self.adapter
        if adapter is None:
            self.sig_error.emit("尚未连接 Excel")
            return
        row = adapter.find_student_row(item.student_no)
        if row is None:
            self.sig_error.emit(f"撤销失败：未找到序号 {item.student_no}")
            return
        adapter.set_score(row, item.score_item, item.old_value)
        if self._config.get("auto_save", True):
            adapter.save()
        if self._config.get("select_cell", True):
            adapter.select_cell(row, item.score_item)
        sel_address = adapter.cell_address(row, item.score_item)
        self.sig_result.emit({
            "sheet_name": adapter.sheet.name if adapter.sheet else "",
            "raw_text": f"[撤销] {item.recognized_text}",
            "student_no": item.student_no,
            "student_name": item.student_name,
            "score_item": item.score_item,
            "operation": "undo",
            "base_score": None,
            "deductions": [],
            "final_score": item.old_value,
            "old_value": item.new_value,
            "new_value": item.old_value,
            "cell": sel_address,
        })


class ScoreVoiceController(QObject):
    """面向 GUI 的控制器。"""

    status_changed = Signal(str)
    recognized = Signal(str)
    result_ready = Signal(dict)
    error = Signal(str)
    structure_loaded = Signal(dict)
    history_changed = Signal(list)

    def __init__(self, config, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self.calculator = ScoreCalculator(config.get("min_score", 0),
                                          config.get("max_score", 100))
        self.parser = CommandParser(self.calculator)
        self.history = HistoryManager()

        self.context_score_item: Optional[str] = config.get("score_item")
        self.known_score_items: list[str] = []
        self.connected = False

        self._worker = ExcelWorker(config)
        self._worker.sig_status.connect(self._on_worker_status)
        self._worker.sig_result.connect(self._on_worker_result)
        self._worker.sig_error.connect(self._on_worker_error)
        self._worker.sig_structure.connect(self._on_structure)

        # 听写状态（文本模拟模式下主要控制界面指示）
        self._listening = False

    # ---------------- 生命周期 ----------------
    def start(self) -> None:
        self._worker.start()

    def shutdown(self) -> None:
        self._worker.stop()
        self._worker.wait(3000)

    # ---------------- Excel ----------------
    def open_excel(self, path: str, sheet_name: Optional[str] = None) -> None:
        self._worker.submit(("open", path, sheet_name))

    def set_sheet(self, sheet_name: str) -> None:
        self._worker.submit(("set_sheet", sheet_name))

    def score_items(self) -> list[str]:
        return list(self.known_score_items)

    # ---------------- 命令处理 ----------------
    def submit_text(self, text: str) -> None:
        """处理一条「语音文本」（来自识别结果或文本模拟输入）。"""
        self.recognized.emit(text)
        try:
            cmd = self.parser.parse(
                text,
                context_score_item=self.context_score_item,
                known_score_items=self.known_score_items,
            )
        except ParseError as e:
            log.warning("解析失败：%s (voice=%r)", e, text)
            self.error.emit(str(e))
            return
        self._worker.submit(("process", cmd))

    def set_score_item(self, score_item: str) -> None:
        self.context_score_item = score_item
        self._config.set("score_item", score_item)

    # ---------------- 听写状态 ----------------
    def start_listening(self) -> None:
        self._listening = True
        self.status_changed.emit("正在监听")

    def pause_listening(self) -> None:
        self._listening = False
        self.status_changed.emit("已暂停")

    def stop_listening(self) -> None:
        self._listening = False
        self.status_changed.emit("未监听")

    @property
    def is_listening(self) -> bool:
        return self._listening

    # ---------------- Undo ----------------
    def undo_last(self) -> bool:
        item = self.history.undo_last()
        if item is None:
            self.error.emit("没有可撤销的操作")
            return False
        self._worker.submit(("undo", item))
        return True

    # ---------------- Worker 信号回调（GUI 线程）----------------
    def _on_worker_status(self, status: str) -> None:
        self.status_changed.emit(status)

    def _on_worker_error(self, message: str) -> None:
        self.error.emit(message)

    def _on_structure(self, struct: dict) -> None:
        self.known_score_items = struct.get("score_items", [])
        self.connected = True
        self.structure_loaded.emit(struct)

    def _on_worker_result(self, result: dict) -> None:
        if result.get("operation") == "undo":
            self.result_ready.emit(result)
            self._emit_history()
            return
        item = HistoryItem(
            sheet_name=result.get("sheet_name", ""),
            cell_address=result.get("cell", ""),
            student_no=result.get("student_no", 0),
            student_name=result.get("student_name", ""),
            score_item=result.get("score_item", ""),
            old_value=result.get("old_value"),
            new_value=result.get("new_value"),
            recognized_text=result.get("raw_text", ""),
        )
        self.history.push(item)
        self.result_ready.emit(result)
        self._emit_history()

    def _emit_history(self) -> None:
        self.history_changed.emit([it.describe() for it in reversed(self.history.all())])


__all__ = ["ScoreVoiceController", "ExcelWorker"]