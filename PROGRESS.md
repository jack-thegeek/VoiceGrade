# 开发进度记录（实时）

> 项目：Excel 成绩语音连续录入系统
> 依据：《成绩语音录入系统.md》（TODO） + 《成绩表.xlsx》实际模板
> 开始时间：2026-10-02 22:11

---

## 需求与模板分析（已完成）

- 读取《成绩语音录入系统.md》，梳理 31 节需求。
- 解析《成绩表.xlsx》实际结构（通过 openpyxl 原始 XML 解析，未改原文件）：
  - 工作表：`班级成绩登记表`
  - 标题：莞城阮涌小学 2026—2027 学年第一学期 三年级（1）班英语学科单元成绩登记表（A1:C1 合并）
  - 表头第 2 行：`A=序号`、`B=姓名`、`C=第一单元`
  - 学生数据第 3~50 行；**序号不连续**（缺 4、9）
  - 非数字成绩：42 号吴奕辰、47 号郑立夏 = `请假`
  - 统计区第 51~53 行：平均分/合格率/优秀率（含公式）
  - 当前仅 C 列一个成绩列，D/E 列为空（留待扩展）
- 环境探测：Python 3.12、已装 Office 16（Excel，xlwings 可用）

## 选型确认（已完成）

- 生成范围：**全量实现**
- ASR：**先文本模拟、语音后接**（预留 FunASR 可插拔接口）
- 依赖：安装核心依赖并本机验证

## 项目结构（已创建）

```
E:\AI\成绩\
├── main.py / config.json / requirements.txt / README.md / PROGRESS.md
├── ui/       main_window.py, widgets.py
├── audio/    recorder.py, vad.py
├── asr/      engine.py, funasr_engine.py
├── parser/   command_parser.py, chinese_number.py, score_calculator.py
├── excel/    excel_adapter.py
├── history/  history_manager.py
├── core/     controller.py
├── models/   command.py
├── utils/    config.py, logger.py
├── tests/    3 个单元测试模块
└── scripts/  verify_excel.py
```

## Phase 进度

| Phase | 内容 | 状态 |
| ---- | ---- | ---- |
| 1 | Excel 打开/读表头/找学生/读写/保存/定位 | ✅ 已实现（`excel/excel_adapter.py`） |
| 2 | 文本命令解析计算（解析→计算→Excel） | ✅ 已实现（`parser/`，21 测试全通过） |
| 3 | GUI（文件/项目/识别/结果/历史） | ✅ 已实现（`ui/`） |
| 4 | ASR 引擎（文本模拟 + FunASR 接口） | ✅ 已实现（`asr/`） |
| 5 | VAD + 持续监听 | ✅ 骨架已实现（`audio/`，MVP 用文本模拟） |
| 6 | Undo / 日志 / 异常处理 | ✅ 已实现（`history/`、`utils/logger.py`） |
| 7 | PyInstaller 打包 | ✅ 已实现（`build/成绩语音录入系统.spec` + `build.bat`） |

## 单元测试（2026-10-02 22:11）

`python -m unittest discover -s tests` → **21 个测试全部通过**
- 中文数字：一/二/十/二十/二十一/一百/一百零五/九十五/两/全角数字
- 成绩计算：100-2-8-10=80、95-5=90、88-3-2=83、再扣 92-5=87、越界/非数字校验
- 命令解析：减/扣/-/分/再扣/序号/学号/第N号/中文序号/显式成绩项目/异常场景

## 修复记录

1. 包间相对导入越界 → 改为绝对导入（项目根在 `sys.path`）。
2. 正则 `\s` 非法转义告警 → 改用 raw 字符串与字符类。
3. 「扣2分、8分、10分」因删除「分」导致 810 粘连 → 不再删除「分」。

## 待办

- [x] 等待依赖安装完成，运行 `scripts/verify_excel.py` 验证 Excel 读写链路
- [x] `python -c "import main"` 等 GUI 导入自检
- [x] 编写 PyInstaller spec（Phase 7）
- [ ] （可选）接入 FunASR 真实语音识别

## 运行验证（2026-10-02 22:24）

### 依赖安装
PySide6 6.11.2 / xlwings 0.37.5 / numpy 2.5.3 / sounddevice 0.5.6 / pywin32 312 ✅

### 导入自检
`import main, ui.main_window, core.controller, asr.engine, audio.recorder, audio.vad` ✅

### Excel 读写验证（`scripts/verify_excel.py`，临时副本，不动原表）
- 连接：工作表 `['班级成绩登记表']`，成绩列 `['第一单元']`，学生 48 名
- 序号 1 → 行 3，姓名 曾芊羽（序号不连续也正确按 A 列查找）
- 序号 42 成绩 = `请假`（非数字正确返回字符串）
- 写入 C3=80 → 读回 80 → 回滚 82，保存正常 ✅

### 全链路集成测试（`scripts/verify_e2e.py`，Qt 信号/Worker 真实跑通）6/6
1. `1号，100减2减8减10` → C3 = 80 ✅
2. `1号，再扣5分` → 80 → 75 ✅
3. `42号，再扣5分`（请假）→ 拒绝「当前成绩不是数字：请假」 ✅
4. `99号，100减5`（不存在）→ 拒绝「未找到学生：序号 99」 ✅
5. `1号，100减200` → 拒绝「计算结果超出 0~100 范围：-100」 ✅
6. 撤销 → 75 恢复为 80 ✅

## 结论

MVP 核心链路（文本命令 → 解析 → 计算 → Excel 实时修改 → 撤销/历史/错误处理）
已全部实现并本机验证通过。真实语音识别（FunASR/VAD）已预留可插拔接口，可后续接入。

---

## 接入 Windows 自带语音识别（2026-10-02/03）

### 方案

- 新增 `asr/winrt_engine.py`：`WinRTSpeechEngine`，调用 Windows 10/11 内置
  `Windows.Media.SpeechRecognition`（zh-CN 普通话），免费、无需下载模型。
- 依赖（轻量）：`pip install winrt-Windows.Media.SpeechRecognition winrt-Windows.Globalization`
  （已加入 `requirements.txt`，本机安装 winrt 3.2.1 ✅）
- `config.json` 默认 `asr_engine = "winrt"`；依赖缺失自动回退文本模拟并界面提示。

### 架构要点

- WinRT 为**推模式**（自行管理麦克风与静音切分）：基类新增
  `set_text_handler()/start()/stop()`，识别整句后回调
  `controller.submit_text()` 进入统一命令链路（不使用 `audio/` 采集与 VAD）。
- 引擎在独立后台线程跑 asyncio 事件循环；WinRT 事件回调线程 → Qt 信号
  跨线程投递（GUI 冒烟验证通过）。
- 持续会话因静音超时等意外结束（completed 事件）时**自动重启**，保证持续监听；
  初始静音超时放宽至 60 秒减少无谓重启。
- UI：状态区显示「引擎：Windows 自带识别」，输入框分组改为
  「命令输入（手动补录 · 引擎：…）」。

### 关键修复：winrt 与 PySide6 的 DLL 冲突

- 现象：进程内 **先 `import winrt`、后 `import PySide6.QtCore` → 0xC0000005 崩溃**
  （分段实验 D1~D4 定位；winrt 自带 `winrt\msvcp140.dll` 与 Qt 运行库冲突）。
- 修复：`asr/winrt_engine.py` 的 `_load_winrt()`（项目内唯一加载 winrt 的入口）
  强制先 `import PySide6.QtCore` 再加载 winrt；`main.py` 本身也满足该顺序。
- 约束已写入 README「已知约束」；勿在项目外先行 `import winrt`。

### 验证

- 单元测试：`python -m unittest discover -s tests` → **30 个全部通过**
  （新增 `tests/test_winrt_engine.py`：注入假 WinRT，覆盖生命周期、文本回调、
  意外完成自动重启、停止后不重启、启动失败抛错、重启可重复，不访问真实麦克风）。
- 真实引擎冒烟：构造 / 约束编译 / 事件订阅 / start-stop ✅（status 枚举为
  `SpeechRecognitionResultStatus`，5=USER_CANCELED、7=TIMEOUT_EXCEEDED）。
- GUI 冒烟（真实 MainWindow + 事件循环）：引擎标签、监听状态、
  跨线程 recognized 信号到达 GUI、暂停/退出全部正常 ✅。
- PyInstaller spec 已补充 `collect_all("winrt")` 收集原生 pyd 与 msvcp140.dll；
  同时修复 spec 内相对路径被解析到 `build/` 目录的问题（改用 `SPECPATH` 推导根目录）。
- 重新打包成功（`BUILD_EXIT=0`，`dist/成绩语音录入系统/`），确认
  `_internal/winrt/` 下 4 个原生 pyd + `msvcp140.dll` + Python 模块均已收集，
  打包 exe 启动 6 秒存活无崩溃。
- 新增 `scripts/check_voice.py` 麦克风自检脚本（人声实测入口）。

### 待办

- [x] 接入 Windows 自带（WinRT）中文语音识别
- [x] PyInstaller 重新打包并验证 exe 可启动
- [ ] 真人对麦克风说出命令的实测（`python scripts/check_voice.py`；本机自动化无法代替人声）
- [ ] （可选）接入 FunASR 真实语音识别