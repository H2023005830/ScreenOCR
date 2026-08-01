#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ScreenOCR v3 — 识屏文字提取 & 翻译工具
========================================
OCR引擎: OCR.space API (免费, 支持中英文混排)
翻译引擎: MyMemory API (免费, 国内可直接访问)

快捷键:
  Ctrl+Shift+O → 开始识屏
  Ctrl+Shift+T → 翻译
  Ctrl+V       → 从剪贴板粘贴图片识别
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import os
import io
import base64
import ctypes
from datetime import datetime
from PIL import Image, ImageGrab, ImageTk
import pyperclip
import requests

# ================= DPI 缩放修复 =================
def _get_dpi():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    try:
        return ctypes.windll.shcore.GetScaleFactorForMonitor(0, None) / 100.0
    except Exception:
        return 1.0

DPI = _get_dpi()

# OCR.space API KEY (免费key, 每天500次)
OCR_API_KEY = "helloworld"

# ================= 语言映射 =================
LANG_MAP = {
    "中文 (简体)": "zh-CN",
    "中文 (繁体)": "zh-TW",
    "English": "en",
    "日本語": "ja",
    "한국어": "ko",
    "Français": "fr",
    "Deutsch": "de",
    "Español": "es",
    "Русский": "ru",
    "Italiano": "it",
    "Português": "pt",
    "Tiếng Việt": "vi",
}

# OCR 语言映射
OCR_LANG = {
    "chs": "chs",      # 简体中文
    "cht": "cht",      # 繁体中文
    "en": "eng",       # 英文
    "ja": "jpn",       # 日文
    "ko": "kor",       # 韩文
    "fr": "fre",       # 法文
    "de": "ger",       # 德文
    "es": "spa",       # 西班牙文
    "ru": "rus",       # 俄文
    "it": "ita",       # 意大利文
    "pt": "por",       # 葡萄牙文
}

# 翻译语言对映射
TRANSLATE_PAIR = {
    "zh-CN": "zh",
    "zh-TW": "zh-TW",
    "en": "en",
    "ja": "ja",
    "ko": "ko",
    "fr": "fr",
    "de": "de",
    "es": "es",
    "ru": "ru",
    "it": "it",
    "pt": "pt",
    "vi": "vi",
}


# ================= 区域选择器 =================
class RegionSelector:
    def __init__(self, callback):
        self.cb = callback
        self.top = tk.Toplevel()
        self.top.attributes("-fullscreen", True)
        self.top.attributes("-topmost", True)
        self.top.attributes("-alpha", 0.38)
        self.top.configure(bg="#000")

        self.cv = tk.Canvas(self.top, bg="#000", highlightthickness=0, cursor="cross")
        self.cv.pack(fill=tk.BOTH, expand=True)
        self._sx = self._sy = None
        self._rect = self._info = None

        sw, sh = self.top.winfo_screenwidth(), self.top.winfo_screenheight()
        self.cv.create_text(sw//2, sh//2-35, text="拖拽鼠标框选要识别的区域",
                            fill="#00ff88", font=("Microsoft YaHei", 22, "bold"), tags="h")
        self.cv.create_text(sw//2, sh//2+10, text="ESC 取消 | 松开鼠标确认",
                            fill="#999", font=("Microsoft YaHei", 12), tags="h")

        self.cv.bind("<ButtonPress-1>", self._down)
        self.cv.bind("<B1-Motion>", self._move)
        self.cv.bind("<ButtonRelease-1>", self._up)
        self.top.bind("<Escape>", self._cancel)
        self.top.focus_force()

    def _down(self, e):
        self._sx, self._sy = e.x, e.y
        self.cv.delete("h")
        for i in (self._rect, self._info):
            if i: self.cv.delete(i)
        self._rect = self.cv.create_rectangle(
            self._sx, self._sy, self._sx, self._sy,
            outline="#00ff88", width=2, dash=(8, 4))

    def _move(self, e):
        if not self._rect: return
        self.cv.coords(self._rect, self._sx, self._sy, e.x, e.y)
        if self._info: self.cv.delete(self._info)
        w, h = abs(e.x - self._sx), abs(e.y - self._sy)
        cx = (self._sx + e.x) // 2
        cy = (self._sy + e.y) // 2
        self._info = self.cv.create_text(
            cx, cy-22 if cy>25 else cy+22,
            text=f"{w} x {h}", fill="#00ff88", font=("Consolas", 13, "bold"))

    def _up(self, e):
        if self._sx is None: return
        x1, x2 = sorted([self._sx, e.x])
        y1, y2 = sorted([self._sy, e.y])
        if x2-x1 < 10 or y2-y1 < 10: return
        self.top.destroy()
        self.cb((x1, y1, x2, y2))

    def _cancel(self, e):
        self.top.destroy()
        self.cb(None)


# ================= 主应用 =================
class App:
    T = {
        "bg": "#1a1a2e", "bg2": "#22223a", "fg": "#e2e2f0",
        "acc": "#7aa2f7", "g": "#9ece6a", "btn": "#3a3a55",
        "btn2": "#4c4c6a", "pan": "#2a2a42", "dim": "#6c6c8a",
        "warn": "#e0af68", "err": "#f7768e",
    }

    def __init__(self):
        self.root = tk.Tk()
        self.root.tk.call("tk", "scaling", DPI)
        w, h = int(820*DPI), int(680*DPI)
        self.root.geometry(f"{w}x{h}")
        self.root.minsize(int(650*DPI), int(500*DPI))
        self.root.title("ScreenOCR — 识屏提取 & 翻译")
        self.root.configure(bg=self.T["bg"])

        self._last_img = None
        self._thumb = None
        self._ocr_lang = "chs"  # 默认简体中文OCR
        self._mk_ui()
        self._bar.config(text="就绪 | Ctrl+Shift+O 识屏 | Ctrl+V 粘贴 | Ctrl+Shift+T 翻译")
        self._stat.config(text="✅ 就绪", fg=self.T["g"])
        self._cap.config(state=tk.NORMAL)

    # ---------- UI ----------
    def _mk_ui(self):
        T = self.T
        top = tk.Frame(self.root, bg=T["bg2"], height=54)
        top.pack(fill=tk.X, side=tk.TOP)
        top.pack_propagate(False)

        tk.Label(top, text="ScreenOCR", font=("Segoe UI", 15, "bold"),
                 bg=T["bg2"], fg=T["g"]).pack(side=tk.LEFT, padx=14)

        self._stat = tk.Label(top, text="✅ 就绪",
                              font=("Microsoft YaHei", 9), bg=T["bg2"], fg=T["g"])
        self._stat.pack(side=tk.LEFT, padx=6)

        # OCR识别语言
        tk.Label(top, text="OCR:", font=("Microsoft YaHei", 9),
                 bg=T["bg2"], fg=T["dim"]).pack(side=tk.LEFT, padx=(15, 2))
        self._ocr_lang_var = tk.StringVar(value="中英混合")
        ocr_cb = ttk.Combobox(top, textvariable=self._ocr_lang_var,
            values=["中英混合", "仅中文", "仅英文", "日文", "韩文"],
            state="readonly", width=8, font=("Microsoft YaHei", 9))
        ocr_cb.pack(side=tk.LEFT, padx=2)
        ocr_cb.bind("<<ComboboxSelected>>", self._on_ocr_lang_change)

        # 翻译语言
        tk.Label(top, text="→", font=("Microsoft YaHei", 10),
                 bg=T["bg2"], fg=T["fg"]).pack(side=tk.RIGHT, padx=2)
        self._lang = tk.StringVar(value="中文 (简体)")
        ttk.Combobox(top, textvariable=self._lang, values=list(LANG_MAP.keys()),
                     state="readonly", width=13, font=("Microsoft YaHei", 9)
                     ).pack(side=tk.RIGHT, padx=4)
        self._btn(top, "翻译", self._translate, side=tk.RIGHT, padx=4)
        self._btn(top, "粘贴", self._paste, side=tk.RIGHT, padx=4)
        self._cap = self._btn(top, "识屏", self._capture,
                              bg=T["acc"], fg="#1a1a2e", activebackground="#b0c8ff",
                              side=tk.RIGHT, padx=8)

        # 预览区
        pv = tk.Frame(self.root, bg=T["pan"], height=110)
        pv.pack(fill=tk.X, padx=8, pady=(4, 0))
        pv.pack_propagate(False)
        self._pv = tk.Label(pv, text="截图预览", bg=T["pan"], fg=T["dim"],
                            font=("Microsoft YaHei", 10))
        self._pv.pack(expand=True)

        # 标签页
        nb = ttk.Notebook(self.root)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # --- OCR标签页 ---
        f1 = tk.Frame(nb, bg=T["bg"])
        nb.add(f1, text="  识别文字  ")
        tb = tk.Frame(f1, bg=T["bg"])
        tb.pack(fill=tk.X, pady=(4, 2))
        tk.Label(tb, text="OCR 提取结果", font=("Microsoft YaHei", 10, "bold"),
                 bg=T["bg"], fg=T["acc"]).pack(side=tk.LEFT, padx=4)
        self._btn(tb, "保存图", self._save_img, side=tk.RIGHT, padx=2)
        self._btn(tb, "复制", self._copy_ocr, side=tk.RIGHT, padx=2)
        self._btn(tb, "清空", lambda: self._ot.delete("1.0", tk.END), side=tk.RIGHT, padx=2)
        self._ot = scrolledtext.ScrolledText(f1, wrap=tk.WORD,
            font=("Microsoft YaHei", 11), bg="#2e2e48", fg=T["fg"],
            insertbackground=T["fg"], relief=tk.FLAT, borderwidth=1, padx=10, pady=10)
        self._ot.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # --- 翻译标签页 ---
        f2 = tk.Frame(nb, bg=T["bg"])
        nb.add(f2, text="  翻译结果  ")
        tb2 = tk.Frame(f2, bg=T["bg"])
        tb2.pack(fill=tk.X, pady=(4, 2))
        tk.Label(tb2, text="MyMemory 翻译", font=("Microsoft YaHei", 10, "bold"),
                 bg=T["bg"], fg=T["acc"]).pack(side=tk.LEFT, padx=4)
        self._btn(tb2, "复制", self._copy_trans, side=tk.RIGHT, padx=2)
        self._tt = scrolledtext.ScrolledText(f2, wrap=tk.WORD,
            font=("Microsoft YaHei", 11), bg="#2e2e48", fg=T["fg"],
            insertbackground=T["fg"], relief=tk.FLAT, borderwidth=1, padx=10, pady=10)
        self._tt.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # 状态栏
        self._bar = tk.Label(self.root,
            text="Ctrl+Shift+O 识屏 | Ctrl+V 粘贴 | Ctrl+Shift+T 翻译",
            font=("Microsoft YaHei", 9), bg=T["bg2"], fg=T["dim"], anchor=tk.W)
        self._bar.pack(fill=tk.X, side=tk.BOTTOM)

        # 快捷键
        self.root.bind("<Control-Shift-O>", lambda e: self._capture())
        self.root.bind("<Control-Shift-T>", lambda e: self._translate())
        self.root.bind("<Control-v>", lambda e: self._paste())
        self.root.bind("<Control-V>", lambda e: self._paste())
        self.root.protocol("WM_DELETE_WINDOW", lambda: self.root.destroy())

        # 右键菜单
        self._menu = tk.Menu(self.root, tearoff=0, bg=T["bg2"], fg=T["fg"])
        self._menu.add_command(label="复制", command=self._copy_ocr)
        self._menu.add_command(label="清空", command=lambda: self._ot.delete("1.0", tk.END))
        self._ot.bind("<Button-3>", lambda e: self._menu.tk_popup(e.x_root, e.y_root))

    def _btn(self, p, t, c, **kw):
        T = self.T
        d = dict(font=("Microsoft YaHei", 9), bg=T["btn"], fg=T["fg"],
                 activebackground=T["btn2"], activeforeground=T["fg"],
                 relief=tk.FLAT, cursor="hand2", padx=10, pady=4)
        d.update(kw)
        sd, px = d.pop("side", tk.LEFT), d.pop("padx", 2)
        b = tk.Button(p, text=t, command=c, **d)
        b.pack(side=sd, padx=px)
        return b

    def _on_ocr_lang_change(self, e):
        m = {
            "中英混合": "chs",
            "仅中文": "chs",
            "仅英文": "eng",
            "日文": "jpn",
            "韩文": "kor",
        }
        self._ocr_lang = m.get(self._ocr_lang_var.get(), "chs")

    @staticmethod
    def _fix_case(text):
        """修正全是全大写/全小写的文本，转为正常大小写"""
        letters = [c for c in text if c.isalpha()]
        if not letters:
            return text
        upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
        if upper_ratio > 0.5:
            # 过半大写 → 转正常语句大小写
            result = []
            for part in text.replace("!", ".").replace("?", ".").split("."):
                part = part.strip().capitalize()
                if part:
                    result.append(part)
            return ". ".join(result)
        return text

    @staticmethod
    def _detect_lang(text):
        """检测文本主要语言，返回2字母ISO代码"""
        cjk = sum(1 for c in text if '\u4e00' <= c <= '\u9fff' or '\u3400' <= c <= '\u4dbf')
        jp = sum(1 for c in text if '\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff')
        kr = sum(1 for c in text if '\uac00' <= c <= '\ud7af')
        total = len(text.strip())
        if total == 0:
            return "en"
        if cjk / total > 0.15:
            return "zh-CN"
        if jp / total > 0.1:
            return "ja"
        if kr / total > 0.1:
            return "ko"
        return "en"

    # ---------- 识屏 ----------
    def _capture(self):
        self.root.iconify()
        self.root.after(350, self._show_sel)

    def _show_sel(self):
        s = RegionSelector(self._on_region)
        self.root.wait_window(s.top)

    def _on_region(self, r):
        self.root.deiconify()
        if r is None:
            self._bar.config(text="已取消")
            return
        x1, y1, x2, y2 = r
        self._bar.config(text=f"选中区域，OCR识别中...")
        self._stat.config(text="⏳ 识别中...", fg=self.T["warn"])
        img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        self._recognize(img)

    def _paste(self):
        try:
            img = ImageGrab.grabclipboard()
            if img is None:
                messagebox.showinfo("提示", "剪贴板中没有图片。\n请先用 Win+Shift+S 截图。")
                return
            self._bar.config(text="从剪贴板读取，OCR识别中...")
            self._stat.config(text="⏳ 识别中...", fg=self.T["warn"])
            self._recognize(img)
        except Exception as e:
            messagebox.showerror("错误", f"读取剪贴板失败:\n{e}")

    def _recognize(self, img):
        self._show_preview(img)
        self._last_img = img

        def _do():
            try:
                # 压缩大图避免请求过大
                w, h = img.size
                if max(w, h) > 2000:
                    ratio = 2000 / max(w, h)
                    img2 = img.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)
                else:
                    img2 = img

                buf = io.BytesIO()
                img2.save(buf, format="PNG", optimize=True)
                b64 = base64.b64encode(buf.getvalue()).decode()

                # 调用 OCR.space API
                resp = requests.post("https://api.ocr.space/parse/image",
                    data={
                        "apikey": OCR_API_KEY,
                        "language": self._ocr_lang,
                        "isOverlayRequired": "false",
                        "base64Image": f"data:image/png;base64,{b64}",
                    },
                    timeout=30)

                if resp.status_code != 200:
                    raise Exception(f"HTTP {resp.status_code}")

                data = resp.json()
                if data.get("IsErroredOnProcessing"):
                    raise Exception(data.get("ErrorMessage", "OCR处理错误"))

                results = data.get("ParsedResults", [])
                texts = []
                for r in results:
                    t = r.get("ParsedText", "").strip()
                    if t:
                        texts.append(t)

                text = "\n".join(texts) if texts else "（未识别到文字）"
                self.root.after(0, lambda: self._show_ocr(text))

            except Exception as e:
                self.root.after(0, lambda: self._show_err(str(e)))

        threading.Thread(target=_do, daemon=True).start()

    def _show_ocr(self, text):
        self._ot.delete("1.0", tk.END)
        self._ot.insert("1.0", self._fix_case(text))
        self._bar.config(text="识别完成 ✓")
        self._stat.config(text="✅ 就绪", fg=self.T["g"])

    def _show_err(self, e):
        self._ot.delete("1.0", tk.END)
        self._ot.insert("1.0", f"识别失败:\n{e}")
        self._bar.config(text=f"失败: {e[:60]}")
        self._stat.config(text="❌ 失败", fg=self.T["err"])

    # ---------- 翻译 (MyMemory) ----------
    def _translate(self):
        text = self._ot.get("1.0", tk.END).strip()
        if not text or text == "（未识别到文字）":
            messagebox.showinfo("无内容", "请先识屏获取文字。")
            return
        tl = LANG_MAP.get(self._lang.get(), "zh-CN")
        tl_short = TRANSLATE_PAIR.get(tl, "zh")

        self._tt.delete("1.0", tk.END)
        self._tt.insert("1.0", "⏳ 翻译中...")
        self._bar.config(text=f"翻译中 → {self._lang.get()}...")
        self._stat.config(text="⏳ 翻译中...", fg=self.T["warn"])

        def _do():
            try:
                # MyMemory 免费API最长500字符，需要分批
                chunks = [text[i:i+450] for i in range(0, len(text), 450)]
                results = []
                source_lang = self._detect_lang(text)

                for idx, chunk in enumerate(chunks):
                    try:
                        resp = requests.get("https://api.mymemory.translated.net/get",
                            params={"q": chunk, "langpair": f"{source_lang}|{tl_short}"},
                            timeout=15)
                        if resp.status_code == 200:
                            data = resp.json()
                            result = data.get("responseData", {}).get("translatedText", "")
                            results.append(result)
                            # 实时更新进度
                            pct = (idx + 1) * 100 // len(chunks)
                            partial = "\n".join(results)
                            self.root.after(0, lambda t=partial, p=pct: (
                                self._tt.delete("1.0", tk.END),
                                self._tt.insert("1.0", t if len(chunks) == 1
                                    else f"{t}\n\n[翻译中 {p}%...]"),
                                self._bar.config(text=f"翻译中 {p}%...")
                            ))
                        else:
                            results.append(f"[第{idx+1}段失败: HTTP {resp.status_code}]")
                    except Exception as ex:
                        results.append(f"[第{idx+1}段失败: {ex}]")

                final = "\n".join(results)
                self.root.after(0, lambda: self._show_trans(final))

            except Exception as e:
                self.root.after(0, lambda: self._show_trans_err(str(e)))

        threading.Thread(target=_do, daemon=True).start()

    def _show_trans(self, text):
        self._tt.delete("1.0", tk.END)
        self._tt.insert("1.0", self._fix_case(text))
        self._bar.config(text="翻译完成 ✓")
        self._stat.config(text="✅ 就绪", fg=self.T["g"])

    def _show_trans_err(self, e):
        self._tt.delete("1.0", tk.END)
        self._tt.insert("1.0", f"翻译失败:\n{e}")
        self._bar.config(text=f"翻译失败: {e[:60]}")
        self._stat.config(text="❌ 翻译失败", fg=self.T["err"])
        self._tt.insert(tk.END, "\n\n💡 MyMemory 翻译服务可能暂时不可用，请稍后重试。")

    # ---------- 辅助 ----------
    def _show_preview(self, img):
        try:
            w = max(self.root.winfo_width() - 20, 200)
            ratio = min(w / img.width, 100 / img.height, 1.0)
            nw, nh = int(img.width * ratio), int(img.height * ratio)
            self._thumb = ImageTk.PhotoImage(img.resize((nw, nh), Image.LANCZOS))
            self._pv.config(image=self._thumb, text="")
        except Exception:
            pass

    def _save_img(self):
        if not self._last_img:
            messagebox.showinfo("提示", "请先识屏。")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")],
            initialfile=f"screenshot_{ts}.png", title="保存截图")
        if path:
            self._last_img.save(path)
            self._bar.config(text=f"已保存: {os.path.basename(path)}")

    def _copy_ocr(self):
        t = self._ot.get("1.0", tk.END).strip()
        if t and t != "（未识别到文字）":
            pyperclip.copy(t); self._bar.config(text="已复制 ✓")

    def _copy_trans(self):
        t = self._tt.get("1.0", tk.END).strip()
        if t and "翻译中" not in t:
            pyperclip.copy(t); self._bar.config(text="已复制 ✓")

    def run(self):
        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
