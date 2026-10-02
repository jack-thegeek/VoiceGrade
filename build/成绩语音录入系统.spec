# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 打包配置（Phase 7）
# 用法：pyinstaller build/成绩语音录入系统.spec
#
# 默认打包「文本模拟」引擎，不含 FunASR/torch（体积巨大）。
# 如需内置本地语音识别，请取消下方 funasr 依赖并相应增加打包大小限制。

from PyInstaller.utils.hooks import collect_all

datas = [("config.json", ".")]
binaries = []
hiddenimports = []

# 收集第三方包的数据/二进制/隐藏导入
for pkg in ("xlwings", "numpy", "sounddevice", "PySide6"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ["main.py"],
    pathex=[],
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