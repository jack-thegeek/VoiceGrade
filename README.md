# Excel 成绩语音连续录入系统

通过中文普通话连续语音修改 Excel 成绩表。MVP 默认使用「文本模拟」充当语音来源，
完整跑通 **文字命令 → 解析 → 计算 → Excel 实时修改** 链路；语音识别引擎已预留可插拔接口。

## 功能

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

## 安装

```powershell
pip install -r requirements.txt
```

（可选）本地语音识别：

```powershell
# FunASR（推荐，中文普通话，依赖较重）
pip install funasr modelscope torch torchaudio
```

## 运行

```powershell
python main.py
```

1. 点击「打开成绩表」选择 `成绩表.xlsx`
2. 选择班级（工作表）与「成绩项目」
3. 在「命令输入」框输入命令（如 `1号，100减2减8减10`）回车，即可看到 Excel 实时修改
4. 点击「开始监听」后可持续输入命令，连续修改

## 目录结构

```
├── main.py                 入口
├── config.json             配置
├── requirements.txt        依赖
├── ui/                     GUI
├── audio/                  麦克风采集 + VAD
├── asr/                    ASR 引擎（文本模拟 / FunASR）
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
```