@echo off
chcp 65001 >nul 2>&1
title ScreenOCR - 识屏提取 & 翻译工具
cd /d "%~dp0"

echo.
echo  ============================================
echo     ScreenOCR - 识屏提取文字 ^& 翻译工具
echo  ============================================
echo.
echo   首次启动会下载OCR模型（约100MB），请稍等...
echo   后续启动秒开！
echo.
echo  ============================================
echo.

call venv\Scripts\python.exe screen_ocr.py

if %errorlevel% neq 0 (
    echo.
    echo   [错误] 启动失败！
    echo   请检查 Python 虚拟环境是否正确安装。
    echo   运行以下命令重新安装依赖:
    echo     venv\Scripts\pip install easyocr pillow mss deep-translator pyperclip
    echo.
    pause
)
