"""Windows 自带识别（WinRT）引擎测试。

通过替换模块级 _load_winrt 注入假 WinRT 实现，不访问真实麦克风。
"""
import os
import sys
import time
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from asr import create_engine
from asr import winrt_engine
from asr.winrt_engine import WinRTSpeechEngine


# ---------------- 假 WinRT 实现 ----------------
class FakeSession:
    def __init__(self):
        self.result_handlers = []
        self.completed_handlers = []
        self.started = 0
        self.stopped = 0

    def add_result_generated(self, cb):
        self.result_handlers.append(cb)
        return cb

    def remove_result_generated(self, tok):
        self.result_handlers.remove(tok)

    def add_completed(self, cb):
        self.completed_handlers.append(cb)
        return cb

    def remove_completed(self, tok):
        self.completed_handlers.remove(tok)

    async def start_async(self):
        self.started += 1

    async def stop_async(self):
        self.stopped += 1

    # 测试辅助：模拟 WinRT 线程池触发事件
    def fire_result(self, text):
        args = types.SimpleNamespace(
            result=types.SimpleNamespace(text=text))
        for cb in list(self.result_handlers):
            cb(None, args)

    def fire_completed(self, status=0):
        args = types.SimpleNamespace(status=status)
        for cb in list(self.completed_handlers):
            cb(None, args)


class FakeRecognizer:
    def __init__(self, language, fail_compile=False):
        self.language = language
        self.session = FakeSession()
        self.closed = False
        self.compiled = False
        self._fail_compile = fail_compile

    async def compile_constraints_async(self):
        if self._fail_compile:
            raise RuntimeError("语言包缺失")
        self.compiled = True

    @property
    def continuous_recognition_session(self):
        return self.session

    def close(self):
        self.closed = True


# 可由测试调整的开关
_FAIL_COMPILE = False


def fake_load_winrt():
    def make_recognizer(lang):
        return FakeRecognizer(lang, fail_compile=_FAIL_COMPILE)

    return make_recognizer, lambda tag: f"Language({tag})"


# ---------------- 测试 ----------------
class TestWinRTEngine(unittest.TestCase):
    def setUp(self):
        global _FAIL_COMPILE
        _FAIL_COMPILE = False
        self._orig = winrt_engine._load_winrt
        winrt_engine._load_winrt = fake_load_winrt

    def tearDown(self):
        winrt_engine._load_winrt = self._orig

    def test_factory_registers_winrt(self):
        engine = create_engine("winrt")
        self.assertIsInstance(engine, WinRTSpeechEngine)
        self.assertEqual(engine.name, "winrt")
        self.assertEqual(engine.display_name, "Windows 自带识别")

    def test_lifecycle_and_text_callback(self):
        engine = WinRTSpeechEngine(language="zh-CN")
        received = []
        engine.set_text_handler(received.append)

        engine.start()
        self.assertTrue(engine.is_running)
        recognizer = engine._recognizer
        self.assertIsNotNone(recognizer)
        self.assertTrue(recognizer.compiled)
        self.assertEqual(recognizer.session.started, 1)
        self.assertEqual(recognizer.language, "Language(zh-CN)")

        # 模拟 WinRT 线程池回调 -> 文本进入 handler
        recognizer.session.fire_result("1号，100减2减8减10")
        self.assertEqual(received, ["1号，100减2减8减10"])

        # 空白结果被忽略
        recognizer.session.fire_result("   ")
        self.assertEqual(len(received), 1)

        engine.stop()
        self.assertFalse(engine.is_running)
        self.assertEqual(recognizer.session.stopped, 1)
        self.assertTrue(recognizer.closed)
        # 停止后事件已反注册
        self.assertEqual(recognizer.session.result_handlers, [])

    def test_restart_on_unexpected_completion(self):
        engine = WinRTSpeechEngine()
        engine.set_text_handler(lambda _t: None)
        engine.start()
        recognizer = engine._recognizer
        session = recognizer.session

        # 模拟静音超时等意外结束 -> 应自动重启
        session.fire_completed()
        deadline = time.time() + 3.0
        while session.started < 2 and time.time() < deadline:
            time.sleep(0.02)
        self.assertEqual(session.started, 2)

        engine.stop()

    def test_no_restart_after_stop(self):
        engine = WinRTSpeechEngine()
        engine.set_text_handler(lambda _t: None)
        engine.start()
        recognizer = engine._recognizer
        session = recognizer.session

        # 先触发一次「意外结束」，但在重启落地前用户停止
        session.fire_completed()
        engine.stop()
        time.sleep(0.2)
        self.assertFalse(engine.is_running)

    def test_start_failure_raises(self):
        global _FAIL_COMPILE
        _FAIL_COMPILE = True
        engine = WinRTSpeechEngine()
        with self.assertRaises(RuntimeError):
            engine.start()
        self.assertFalse(engine.is_running)

    def test_restartable_after_stop(self):
        engine = WinRTSpeechEngine()
        engine.set_text_handler(lambda _t: None)
        engine.start()
        engine.stop()
        engine.start()
        self.assertTrue(engine.is_running)
        engine.stop()
        self.assertFalse(engine.is_running)

    def test_transcribe_returns_empty(self):
        # 推模式引擎不消费音频数组
        engine = WinRTSpeechEngine()
        self.assertEqual(engine.transcribe(None, 16000), "")


class TestEngineFallback(unittest.TestCase):
    """配置了不存在的引擎时应能回退（工厂层验证）。"""

    def test_unknown_engine_raises(self):
        with self.assertRaises(ValueError):
            create_engine("no-such-engine")

    def test_text_engine_still_available(self):
        engine = create_engine("text")
        self.assertEqual(engine.name, "text")
        # 文本引擎 start/stop 为空实现，不抛异常
        engine.start()
        engine.stop()


if __name__ == "__main__":
    unittest.main()
