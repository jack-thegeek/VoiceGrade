@echo off
chcp 65001 >nul
REM Excel 成绩语音录入系统 - 一键打包脚本
REM 需要先安装：pip install pyinstaller
echo ============================================
echo   正在打包 Excel 成绩语音录入系统 ...
echo ============================================
pyinstaller --clean --noconfirm build\成绩语音录入系统.spec
echo.
if exist "dist\成绩语音录入系统\成绩语音录入系统.exe" (
    echo [完成] 输出：dist\成绩语音录入系统\成绩语音录入系统.exe
) else (
    echo [失败] 打包未成功，请检查上方错误信息。
)
pause