"""麦克风识别自检：真实调用 Windows 自带识别，打印听到的文本。

用法：
    python scripts/check_voice.py [监听秒数，默认 10]

对麦克风清晰说出（例如）：「1号，100减2减8减10」，
若控制台打印出该文本即表示 Windows 自带语音识别链路正常。

注意：本脚本需在项目根目录或任意位置运行均可（自动定位项目根）。
"""
from __future__ import annotations

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from utils.logger import setup_logger  # noqa: E402

setup_logger()


def main() -> int:
    seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 10

    from asr import create_engine

    print(f"正在启动 Windows 自带语音识别（监听 {seconds} 秒）...")
    print("请现在对着麦克风说话，例如：1号，100减2减8减10")
    texts: list[str] = []

    engine = create_engine("winrt")
    engine.set_text_handler(texts.append)
    try:
        engine.start()
    except RuntimeError as e:
        print(f"[失败] {e}")
        print("提示：检查 设置 → 隐私 → 麦克风，以及中文语音包是否安装。")
        return 1

    try:
        deadline = time.time() + seconds
        while time.time() < deadline:
            time.sleep(0.2)
    finally:
        engine.stop()

    if texts:
        print(f"\n[通过] 共识别 {len(texts)} 句：")
        for t in texts:
            print(f"  - {t}")
        return 0
    print("\n[未识别到语音] 未听到任何内容。请检查：")
    print("  1) 麦克风是否可用、音量是否正常（设置 → 隐私 → 麦克风）")
    print("  2) 是否安装了中文（简体）语音包")
    print("  3) 说话是否在监听时间内、距离麦克风是否过远")
    return 2


if __name__ == "__main__":
    sys.exit(main())
