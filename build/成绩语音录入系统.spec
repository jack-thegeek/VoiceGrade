# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 打包配置（Phase 7）
# 用法：pyinstaller build/成绩语音录入系统.spec
#
# 默认打包「Windows 自带识别（WinRT）」+「文本模拟」引擎，不含 FunASR/torch
# （体积巨大）。WinRT 依赖为轻量原生桥接，直接纳入打包。

from PyInstaller.utils.hooks import collect_all, collect_submodules

# 项目根目录（spec 位于 <根>/build/ 下；相对路径一律基于根目录解析）
import os

ROOT = os.path.dirname(SPECPATH)

datas = [(os.path.join(ROOT, "config.json"), ".")]
binaries = []
hiddenimports = []

# 收集第三方包的数据/二进制/隐藏导入
for pkg in ("xlwings", "numpy", "sounddevice", "PySide6"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# Windows 自带识别（WinRT）：全部位于 winrt 命名空间下
# （含原生 _winrt.pyd 与自带的 msvcp140.dll；后者与 Qt 存在 DLL 冲突，
#  运行时靠 asr/winrt_engine.py 的加载顺序保护，打包时需完整收集）
try:
    d, b, h = collect_all("winrt")
    datas += d
    binaries += b
    hiddenimports += h
except Exception:
    hiddenimports += collect_submodules("winrt")

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["torch", "torchaudio", "funasr", "modelscope", "onnxruntime"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="成绩语音录入系统",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # 图形界面，无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="成绩语音录入系统",
)