"""Windows 自带语音识别引擎（WinRT SpeechRecognizer）。

调用 Windows 10/11 内置的「Windows 语音识别」（zh-CN 普通话），
免费、无需下载模型。依赖（体积很小）：

    pip install winrt-Windows.Media.SpeechRecognition winrt-Windows.Globalization

要点：
- WinRT 引擎自行管理麦克风与静音切分（推模式），识别到完整句子后
  通过文本回调把结果送入命令处理链路，因此不使用 audio/ 采集与 VAD。
- 引擎在独立后台线程内运行 asyncio 事件循环，WinRT 事件回调发生在线程
  池线程；回调仅转交文本 handler（controller.submit_text），由 Qt 信号
  机制完成跨线程投递，安全。
- 持续会话可能因静音超时等原因自动结束（completed 事件），若非用户主动
  停止则自动重启，保证「持续监听」不失效。
"""
from __future__ import annotations

import asyncio
import threading
from datetime import timedelta
from typing import Optional

import numpy as np

from utils.logger import get_logger

from .engine import BaseASREngine

log = get_logger("asr.winrt")

# WinRT 首次启动（含约束编译）的等待上限（秒）
_START_TIMEOUT = 15.0


def _load_winrt():
    """加载 WinRT 依赖；未安装时抛出带安装提示的 RuntimeError。

    注意顺序：必须先加载 PySide6/Qt，再加载 winrt 原生模块。两者 DLL
    存在冲突，若 winrt 先于 Qt 加载，随后 import PySide6 会直接导致进程
    访问违规崩溃（0xC0000005）。本函数是项目内唯一加载 winrt 的入口，
    在此强制正确顺序即可保证安全。
    """
    try:
        import PySide6.QtCore  # noqa: F401
    except ImportError:  # 允许无 Qt 环境下单独使用引擎
        pass
    try:
        from winrt.windows.globalization import Language
        from winrt.windows.media.speechrecognition import SpeechRecognizer
    except ImportError as e:  # noqa: BLE001
        raise RuntimeError(
            "未安装 Windows 语音识别（WinRT）依赖。请执行："
            "pip install winrt-Windows.Media.SpeechRecognition "
            "winrt-Windows.Globalization"
        ) from e
    return SpeechRecognizer, Language


class WinRTSpeechEngine(BaseASREngine):
    """Windows 自带识别（推模式：start/stop + 文本回调）。"""

    name = "winrt"
    display_name = "Windows 自带识别"

    def __init__(self, language: str = "zh-CN") -> None:
        self._SpeechRecognizer, self._Language = _load_winrt()
        self._language = language

        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._recognizer = None
        self._stop_event = threading.Event()
        self._ready = threading.Event()
        self._start_error: Optional[BaseException] = None
        self._stopping = False
        self._restarting = False

    # ---------------- BaseASREngine 接口 ----------------
    def transcribe(self, audio: np.ndarray, sample_rate: int) -> str:  # noqa: ARG002
        """推模式引擎不消费音频数组；文本经由 set_text_handler 回调送出。"""
        return ""

    def start(self) -> None:
        """启动持续识别（阻塞直至就绪或失败）。"""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._ready.clear()
        self._start_error = None
        self._stopping = False
        self._restarting = False
        self._thread = threading.Thread(
            target=self._thread_main, name="winrt-asr", daemon=True
        )
        self._thread.start()
        if not self._ready.wait(timeout=_START_TIMEOUT):
            self.stop()
            raise RuntimeError("Windows 语音识别启动超时")
        if self._start_error is not None:
            err = self._start_error
            self.stop()
            raise RuntimeError(f"Windows 语音识别启动失败：{err}") from err

    def stop(self) -> None:
        """停止持续识别并回收线程。"""
        self._stopping = True
        self._stop_event.set()
        thread, self._thread = self._thread, None
        if thread is not None and thread.is_alive():
            thread.join(timeout=5.0)

    def shutdown(self) -> None:
        self.stop()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ---------------- 后台线程 / asyncio ----------------
    def _thread_main(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        try:
            loop.run_until_complete(self._session_main())
        except BaseException as e:  # noqa: BLE001
            self._start_error = e
            self._ready.set()
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception:  # noqa: BLE001, S110
                pass
            loop.close()
            self._loop = None

    async def _session_main(self) -> None:
        recognizer = self._SpeechRecognizer(self._Language(self._language))
        self._recognizer = recognizer
        try:
            # 无人说话时不要过早结束会话（默认约 5 秒）；结束后仍会自动重启，
            # 这里放宽以减少无谓的重启
            try:
                recognizer.timeouts.initial_silence_timeout = timedelta(seconds=60)
            except Exception:  # noqa: BLE001, S110
                pass
            await recognizer.compile_constraints_async()
            session = recognizer.continuous_recognition_session

            tok_result = session.add_result_generated(self._on_result)
            tok_done = session.add_completed(self._on_completed)
            await session.start_async()
            self._ready.set()

            # 主循环：等待用户停止信号
            while not self._stop_event.is_set():
                await asyncio.sleep(0.1)

            try:
                await session.stop_async()
            except Exception:  # noqa: BLE001, S110
                pass
            session.remove_result_generated(tok_result)
            session.remove_completed(tok_done)
        finally:
            self._recognizer = None
            try:
                recognizer.close()
            except Exception:  # noqa: BLE001, S110
                pass

    # ---------------- WinRT 事件（线程池线程）----------------
    def _on_result(self, sender, args) -> None:  # noqa: ARG002
        try:
            text = (args.result.text or "").strip()
        except Exception as e:  # noqa: BLE001
            log.warning("读取识别结果失败：%s", e)
            return
        if not text:
            return
        handler = self._handler
        if handler is None:
            return
        try:
            handler(text)
        except Exception:  # noqa: BLE001
            # 回调异常不能打断 WinRT 事件线程
            log.exception("识别文本回调异常")

    def _on_completed(self, sender, args) -> None:  # noqa: ARG002
        """会话结束：若非用户主动停止（如静音超时自动停），自动重启。"""
        if self._stopping or self._stop_event.is_set():
            return
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        log.info("识别会话结束（status=%s），准备自动重启",
                 getattr(args, "status", "?"))
        try:
            asyncio.run_coroutine_threadsafe(self._restart_session(), loop)
        except RuntimeError:
            pass

    async def _restart_session(self) -> None:
        if self._stopping or self._stop_event.is_set() or self._restarting:
            return
        self._restarting = True
        try:
            recognizer = self._recognizer
            if recognizer is None:
                return
            await recognizer.continuous_recognition_session.start_async()
            log.info("识别会话已自动重启")
        except Exception as e:  # noqa: BLE001
            log.error("识别会话重启失败：%s", e)
        finally:
            self._restarting = False


__all__ = ["WinRTSpeechEngine"]
