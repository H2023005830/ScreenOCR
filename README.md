# ScreenOCR — 识屏文字提取 & 翻译工具

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)

一个轻量级的 Windows 桌面工具，**划定屏幕区域截图 → OCR 文字识别 → 多语言翻译**，一气呵成。

## ✨ 功能

- 🖱️ **区域识屏** — 拖拽鼠标框选任意屏幕区域，自动截图并 OCR 识别文字
- 📋 **剪贴板识别** — `Win+Shift+S` 截图后，一键粘贴识别
- 🌐 **多语言翻译** — 支持 12 种语言互译（中/英/日/韩/法/德/西/俄/意/葡/越/阿）
- 📝 **大小写修正** — 自动将全大写/全小写文本转为正常语句格式
- 💾 **截图保存** — 支持 PNG/JPEG 格式导出
- 🎨 **暗色主题** — 舒适的暗色 UI 界面

## 🚀 快速开始

### 环境要求
- Windows 10/11
- Python 3.10+

### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/H2023005830/ScreenOCR.git
cd ScreenOCR

# 2. 创建虚拟环境
python -m venv venv

# 3. 安装依赖
venv\Scripts\pip install pillow mss requests pyperclip

# 4. 启动
venv\Scripts\python.exe screen_ocr.py
```

或者直接双击 `启动.bat`。

## ⌨️ 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+Shift+O` | 开始识屏 |
| `Ctrl+V` | 粘贴剪贴板图片识别 |
| `Ctrl+Shift+T` | 翻译识别文字 |
| `ESC` | 取消区域选择 |

## 🛠️ 技术架构

```
ScreenOCR/
├── screen_ocr.py      # 主程序
├── 启动.bat            # Windows 启动脚本
├── create_shortcut.py  # 桌面快捷方式生成
├── requirements.txt    # Python 依赖
└── README.md
```

### 依赖的 API 服务

| 模块 | 服务 | 说明 |
|------|------|------|
| OCR 识别 | [OCR.space](https://ocr.space/) | 免费 API，支持中英文混排 |
| 翻译 | [MyMemory](https://mymemory.translated.net/) | 免费翻译 API，国内可直连 |

## 📄 许可证

MIT License — 详见 [LICENSE](LICENSE)

## 🙏 致谢

- [OCR.space](https://ocr.space/) 提供免费 OCR API
- [MyMemory](https://mymemory.translated.net/) 提供免费翻译 API
- [Pillow](https://python-pillow.org/) Python 图像处理库
