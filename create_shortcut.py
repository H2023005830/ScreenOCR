"""在桌面创建 ScreenOCR 快捷方式"""
import os
import sys
import pylnk3

desktop = os.path.expandvars(r"%USERPROFILE%\Desktop")
shortcut_path = os.path.join(desktop, "ScreenOCR.lnk")

lnk = pylnk3.create(shortcut_path)

# 目标程序
lnk.specify_local_location(r"C:\Windows\System32\cmd.exe")

# 启动参数
lnk._set_arguments(r'/c ""D:\workbuddy\ScreenOCR\启动.bat""')

# 工作目录
lnk._set_work_dir(r"D:\workbuddy\ScreenOCR")

# 描述
lnk._set_description(
    "ScreenOCR - 识屏提取文字 & 翻译工具\n"
    "Ctrl+Shift+O: 识屏 | Ctrl+V: 粘贴图片 | Ctrl+Shift+T: 翻译"
)

# 图标 (imageres.dll 第86号是屏幕图标)
icon_path = r"C:\Windows\System32\imageres.dll"
if os.path.exists(icon_path):
    lnk._set_icon(icon_path)
    lnk.icon_index = 86

lnk.save()
print(f"[OK] 桌面快捷方式: ScreenOCR.lnk")
