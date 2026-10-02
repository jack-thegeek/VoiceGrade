"""程序入口。

用法：
    python main.py

启动 GUI 后：选择成绩表 -> 选择成绩项目 -> 输入命令（模拟语音）-> 自动修改 Excel。
"""
from __future__ import annotations

import os
import sys


def main() -> int:
    # 保证项目根目录在 sys.path 中，便于相对导入
    root = os.path.dirname(os.path.abspath(__file__))
    if root not in sys.path:
        sys.path.insert(0, root)

    from PySide6.QtWidgets import QApplication

    from core.controller import ScoreVoiceController
    from ui.main_window import MainWindow
    from utils.config import Config
    from utils.logger import setup_logger

    setup_logger(log_dir=os.path.join(root, "logs"))

    app = QApplication(sys.argv)

    config = Config(os.path.join(root, "config.json"))
    controller = ScoreVoiceController(config)
    controller.start()

    window = MainWindow(controller)
    window.show()

    exit_code = app.exec()
    controller.shutdown()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())