# Excel 成绩语音连续录入系统

通过中文普通话连续语音修改 Excel 成绩表。默认使用 **Windows 自带语音识别**
（WinRT，中文普通话，免费、无需下载模型），点「开始监听」后直接说话即可；
也支持「文本模拟」输入与可插拔的本地引擎（FunASR）。

## 功能

- **Windows 自带语音识别**（Windows 10/11 内置 zh-CN，WinRT 接入）
- 依据 A 列「序号」查找学生（不依赖行号，序列号不连续也能正确定位）
- 依据第 2 行表头自动发现成绩列（不硬编码 C、D、E）
- 支持命令：
  - `1号，100减2减8减10` → 计算 80 写入
  - `100扣2扣8扣10` / `100-2-8-10` / `100分，扣2分、8分、10分`
  - `5号，再扣5分` → 读取当前成绩减 5
  - 学号多种表达：`1号` `第1号` `序号1` `学号1` `二十一号`
- 安全机制：不确定不修改；单元格非数字（请假）、结果越界、学号不存在等一律拒绝写入
- 修改历史 / 撤销
- 实时状态指示与操作日志

## 环境要求

- Windows 10 / 11，已安装 Microsoft Excel
- Python 3.11+
- 麦克风可用（设置 → 隐私和安全性 → 麦克风）
- 系统支持中文语音识别（中文版系统自带；其他语言版本需在
  设置 → 时间和语言 → 语言 → 中文（简体）→ 语言选项 中添加「语音包」）

## 安装

```powershell
pip install -r requirements.txt
```

（可选）本地离线识别 FunASR：

```powershell
# FunASR（中文普通话，依赖较重）
pip install funasr modelscope torch torchaudio
```

## 运行

```powershell
python main.py
```

1. 点击「打开成绩表」选择 `成绩表.xlsx`
2. 选择班级（工作表）与「成绩项目」
3. 点击「开始监听」，**直接说出命令**（如：*1号，100减2减8减10*），
   识别为整句后自动解析并修改 Excel；也可在「命令输入」框手动输入（回车发送）
4. 「暂停」可随时停止监听

> 说明：切换引擎改 `config.json` 的 `asr_engine`：
> `winrt`（Windows 自带，默认）/ `text`（纯文本模拟）/ `funasr`（本地模型）。
> 引擎依赖缺失时自动回退到文本模拟并在界面上提示。

## 已知约束

- winrt 原生模块与 PySide6/Qt 存在 DLL 冲突：**必须先加载 Qt 再加载 winrt**，
  否则进程崩溃（0xC0000005）。`main.py` 与 `asr/winrt_engine.py` 的
  `_load_winrt()` 已强制该顺序，勿在项目外先行 `import winrt`。

## 目录结构

```
├── main.py                 入口
├── config.json             配置
├── requirements.txt        依赖
├── ui/                     GUI
├── audio/                  麦克风采集 + VAD
├── asr/                    ASR 引擎（Windows 自带 / 文本模拟 / FunASR）
├── parser/                 中文数字、成绩计算、命令解析
├── excel/                  Excel 适配层（xlwings）
├── history/                修改历史 / 撤销
├── core/                   控制器（Worker 线程编排）
├── models/                 数据模型
├── utils/                  配置 / 日志
├── tests/                  单元测试
└── scripts/                验证脚本
```

## 测试

```powershell
python -m unittest discover -s tests -v
python scripts/verify_excel.py

# 麦克风识别自检（对麦克风说「1号，100减2减8减10」，验证 Windows 自带识别）
python scripts/check_voice.py
```