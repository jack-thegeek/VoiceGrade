"""麦克风持续采集（对应 TODO 第 4 节）。

使用 sounddevice 把麦克风音频流式写入线程安全队列，
供 VAD / ASR 消费，实现「持续监听」。
"""
from __future__ import annotations

import queue
import threading
from typing import Iterator

import numpy as np


class AudioRecorder:
    """持续从默认输入设备采集 PCM 音频。"""

    def __init__(self, sample_rate: int = 16000, channels: int = 1,
                 block_ms: int = 30, dtype: str = "float32") -> None:
        import sounddevice as sd

        self._sd = sd
        self.sample_rate = sample_rate
        self.channels = channels
        self.block_size = int(sample_rate * block_ms / 1000)
        self.dtype = dtype
        self._stream = None
        self._queue: "queue.Queue[np.ndarray]" = queue.Queue()
        self._running = threading.Event()

    def start(self) -> None:
        if self._running.is_set():
            return
        # 先预热，避免第一帧为空
        self._stream = self._sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype,
            blocksize=self.block_size,
            callback=self._callback,
        )
        self._stream.start()
        self._running.set()

    def _callback(self, indata, frames, time_info, status) -> None:  # noqa: ARG002
        self._queue.put(np.asarray(indata).copy())

    def read(self, timeout: float = 1.0) -> np.ndarray | None:
        """读取一帧音频（无数据超时返回 None）。"""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def drain(self) -> None:
        """清空队列。"""
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                return

    def stop(self) -> None:
        if not self._running.is_set():
            return
        self._running.clear()
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:  # noqa: BLE001
                pass
            self._stream = None

    def __iter__(self) -> Iterator[np.ndarray]:
        while self._running.is_set():
            frame = self.read(timeout=0.5)
            if frame is not None:
                yield frame

    @property
    def is_running(self) -> bool:
        return self._running.is_set()


__all__ = ["AudioRecorder"]