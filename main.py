import ctypes
import sys
import os
import importlib.util
import subprocess

def enable_dpi_awareness():
    if sys.platform != 'win32':
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    if sys.platform == 'win32':
        script = os.path.abspath(sys.argv[0])
        params = subprocess.list2cmdline(sys.argv[1:] if getattr(sys, 'frozen', False) else [script] + sys.argv[1:])
        try:
            return ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1) > 32
        except:
            return False
    return False

import tkinter as tk
from tkinter import messagebox, ttk, font as tkfont
import threading
import random
import json
import time

keyboard = None
pyperclip = None
pystray = None
HAS_PYSTRAY = importlib.util.find_spec("pystray") is not None

def load_keyboard():
    global keyboard
    if keyboard is None:
        import keyboard as keyboard_module
        keyboard = keyboard_module
    return keyboard

def load_pyperclip():
    global pyperclip
    if pyperclip is None:
        import pyperclip as pyperclip_module
        pyperclip = pyperclip_module
    return pyperclip

def load_tray():
    global pystray
    if pystray is None:
        import pystray as pystray_module
        pystray = pystray_module
    from PIL import Image, ImageDraw
    return pystray, Image, ImageDraw

def get_config_path():
    if getattr(sys, 'frozen', False):
        # 程序被打包成 exe
        base_dir = os.path.dirname(sys.executable)
    else:
        # 普通 Python 脚本
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "config.json")

CONFIG_FILE = get_config_path()
DEFAULT_CONFIG = {
    "min_speed": 50,
    "max_speed": 150,
    "hotkey": "ctrl+alt+v",
    "stop_hotkey": "ctrl+a",
    "use_random_speed": True,
    "fixed_speed": 100,
    "hide_to_tray": True,
    "asked_hide_to_tray": False
}

INSTANCE_MUTEX_NAME = r'Local\SimulatedInputTool.SingleInstance'

def acquire_instance():
    if sys.platform != 'win32':
        return None
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexExW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD)
    kernel.CreateMutexExW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.CreateMutexExW(None, INSTANCE_MUTEX_NAME, 0, 0x00100000)
    error = ctypes.get_last_error()
    if not handle:
        raise ctypes.WinError(error)
    if error == 183:
        kernel.CloseHandle(handle)
        user = ctypes.windll.user32
        user.FindWindowW.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR)
        user.FindWindowW.restype = wintypes.HWND
        user.ShowWindow.argtypes = (wintypes.HWND, ctypes.c_int)
        user.SetForegroundWindow.argtypes = (wintypes.HWND,)
        window = user.FindWindowW('TkTopLevel', '模拟输入工具')
        if window:
            user.ShowWindow(window, 9)
            user.SetForegroundWindow(window)
        return None
    return handle

class SimulatedInputApp:
    def __init__(self, root):
        self.root = root
        self.root.title("模拟输入工具")
        self.root.resizable(True, True)
        self.root.configure(bg='#f7f8fa')
        
        self.config = self.load_config()
        self.is_typing = False
        self.typing_thread = None
        self.is_setting_hotkey = False
        self.setting_stop_hotkey = False
        self.pressed_keys = set()
        self.tray_icon = None
        self.is_hidden = False
        self.hook_handle = None
        self.start_hotkey_hook = None
        self.stop_hotkey_hook = None
        
        self.setup_ui()
        self.root.update_idletasks()
        width = self.root.winfo_reqwidth()
        height = self.root.winfo_reqheight()
        self.root.geometry(f'{width}x{height}')
        self.root.minsize(width, height)
        
        self.root.after_idle(self.initialize_background_features)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def initialize_background_features(self):
        self.init_keyboard()
        if HAS_PYSTRAY:
            self.setup_tray()
    
    def init_keyboard(self):
        load_keyboard()
        self.register_hotkeys()
    
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    for key in DEFAULT_CONFIG:
                        if key not in loaded:
                            loaded[key] = DEFAULT_CONFIG[key]
                    return loaded
            except:
                return DEFAULT_CONFIG.copy()
        else:
            default = DEFAULT_CONFIG.copy()
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(default, f, ensure_ascii=False, indent=2)
            return default
    
    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def button_style(self, kind="primary"):
        styles = {
            "primary": ("#2563eb", "#ffffff", "#1d4ed8"),
            "success": ("#0f766e", "#ffffff", "#115e59"),
            "danger": ("#dc2626", "#ffffff", "#b91c1c"),
            "muted": ("#334155", "#ffffff", "#1e293b"),
            "light": ("#e8eef7", "#1e293b", "#dbe5f2"),
        }
        bg, fg, active_bg = styles.get(kind, styles["primary"])
        return {
            "font": ('Microsoft YaHei UI', 10, 'bold'),
            "bg": bg,
            "fg": fg,
            "activebackground": active_bg,
            "activeforeground": fg,
            "relief": "flat",
            "bd": 0,
            "padx": 15,
            "pady": 8,
            "cursor": "hand2",
        }

    def create_card(self, parent, pady=(0, 14)):
        frame = tk.Frame(
            parent,
            bg='#ffffff',
            highlightbackground='#dbe4f0',
            highlightthickness=1,
            padx=18,
            pady=14
        )
        frame.pack(fill=tk.X, pady=pady)
        return frame

    def create_section_title(self, parent, title, hint=None):
        tk.Label(
            parent,
            text=title,
            font=('Microsoft YaHei', 12, 'bold'),
            bg='#ffffff',
            fg='#111827'
        ).pack(anchor=tk.W)
        if hint:
            tk.Label(
                parent,
                text=hint,
                font=('Microsoft YaHei', 9),
                bg='#ffffff',
                fg='#64748b',
                wraplength=450,
                justify=tk.LEFT
            ).pack(anchor=tk.W, pady=(4, 8))
        else:
            tk.Frame(parent, height=6, bg='#ffffff').pack(fill=tk.X)

    def create_entry(self, parent, variable, width=10):
        return tk.Entry(
            parent,
            textvariable=variable,
            width=width,
            font=('Microsoft YaHei', 11),
            bg='#f8fafc',
            fg='#111827',
            relief='flat',
            bd=0,
            highlightthickness=1,
            highlightbackground='#cbd5e1',
            highlightcolor='#0f766e',
            insertbackground='#0f766e'
        )

    def update_scroll_region(self, event=None):
        self.content_canvas.configure(scrollregion=self.content_canvas.bbox("all"))

    def sync_scroll_width(self, event):
        self.content_canvas.itemconfigure(self.scroll_window, width=event.width)

    def on_mousewheel(self, event):
        self.content_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def setup_ui(self):
        self.font = ('Microsoft YaHei UI', 10)
        self.font_small = ('Microsoft YaHei UI', 9)
        self.font_title = ('Microsoft YaHei UI', 18, 'bold')
        self.mono_font = ('Cascadia Mono', 10)
        tkfont.nametofont('TkDefaultFont').configure(family=self.font[0], size=10)
        tkfont.nametofont('TkTextFont').configure(family=self.font[0], size=10)

        style = ttk.Style(self.root)
        style.theme_use('clam')
        if sys.platform == 'win32':
            style.element_create('App.Checkbutton.indicator', 'from', 'vista', 'Checkbutton.indicator')
            style.layout('App.TCheckbutton', [('Checkbutton.padding', {'sticky': 'nswe', 'children': [
                ('App.Checkbutton.indicator', {'side': 'left', 'sticky': ''}),
                ('Checkbutton.focus', {'side': 'left', 'sticky': 'w', 'children': [
                    ('Checkbutton.label', {'sticky': 'nswe'})
                ]})
            ]})])
        style.configure('App.TFrame', background='#f7f8fa')
        style.configure('Title.TLabel', background='#f7f8fa', foreground='#17202a', font=self.font_title)
        style.configure('Muted.TLabel', background='#f7f8fa', foreground='#64748b', font=self.font_small)
        style.configure('App.TCheckbutton', background='#ffffff', foreground='#334155', font=self.font)
        style.map('App.TCheckbutton', background=[('active', '#ffffff')])
        style.configure('App.TEntry', fieldbackground='#ffffff', foreground='#17202a', padding=(9, 6))
        style.configure('Secondary.TButton', background='#eef2f6', foreground='#334155', padding=(12, 7), borderwidth=0, font=self.font)
        style.map('Secondary.TButton', background=[('active', '#e2e8f0')])
        style.configure('Primary.TButton', background='#0f6cbd', foreground='#ffffff', padding=(16, 9), borderwidth=0, font=('Microsoft YaHei UI', 10, 'bold'))
        style.map('Primary.TButton', background=[('active', '#0b5da5')])
        style.configure('Danger.TButton', background='#fff1f2', foreground='#be123c', padding=(12, 7), borderwidth=0, font=self.font)
        style.map('Danger.TButton', background=[('active', '#ffe4e6')])

        root_frame = ttk.Frame(self.root, style='App.TFrame', padding=(24, 20, 24, 18))
        root_frame.pack(fill=tk.BOTH, expand=True)
        root_frame.columnconfigure(0, weight=1)

        ttk.Label(root_frame, text='模拟输入工具', style='Title.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Label(root_frame, text='复制文本后，用快捷键逐字符输入到当前光标位置', style='Muted.TLabel').grid(row=1, column=0, sticky='w', pady=(3, 16))

        guide = tk.Frame(root_frame, bg='#eaf3ff', highlightbackground='#cfe3fb', highlightthickness=1)
        guide.grid(row=2, column=0, sticky='ew', pady=(0, 12))
        guide.columnconfigure(1, weight=1)
        tk.Label(guide, text='快捷操作', bg='#eaf3ff', fg='#0f6cbd', font=('Microsoft YaHei UI', 9, 'bold')).grid(row=0, column=0, padx=(12, 8), pady=10, sticky='w')
        tk.Label(guide, text='复制文本后，将光标放到目标输入框', bg='#eaf3ff', fg='#1e3a5f', font=self.font_small).grid(row=0, column=1, padx=(0, 12), pady=10, sticky='w')

        self.create_speed_section(root_frame, 3)
        self.create_hotkey_section(root_frame, 4)
        self.create_tray_section(root_frame, 5)
        self.create_status_section(root_frame, 6)
        self.create_button_section(root_frame, 7)
    
    def create_speed_section(self, parent, row):
        frame = tk.Frame(parent, bg='#ffffff', highlightbackground='#e5e7eb', highlightthickness=1, padx=14, pady=12)
        frame.grid(row=row, column=0, sticky='ew', pady=(0, 10))
        tk.Label(frame, text='输入速度', bg='#ffffff', fg='#17202a', font=('Microsoft YaHei UI', 11, 'bold')).grid(row=0, column=0, columnspan=4, sticky='w')
        tk.Label(frame, text='随机速度更像人工输入；固定速度适合稳定复现。', bg='#ffffff', fg='#64748b', font=self.font_small).grid(row=1, column=0, columnspan=4, sticky='w', pady=(3, 9))
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)

        self.use_random_var = tk.BooleanVar(value=self.config.get("use_random_speed", True))
        ttk.Checkbutton(frame, text='随机速度', variable=self.use_random_var, command=self.on_random_toggle, style='App.TCheckbutton').grid(row=2, column=0, columnspan=4, sticky='w', pady=(0, 6))

        tk.Label(frame, text='最小延迟', font=self.font_small, bg='#ffffff', fg='#475569').grid(row=3, column=0, sticky='w', pady=3)
        self.min_speed_var = tk.StringVar(value=str(self.config["min_speed"]))
        self.min_speed_entry = ttk.Entry(frame, textvariable=self.min_speed_var, style='App.TEntry', width=8)
        self.min_speed_entry.grid(row=3, column=1, sticky='ew', padx=(8, 18), pady=3)
        tk.Label(frame, text='最大延迟', font=self.font_small, bg='#ffffff', fg='#475569').grid(row=3, column=2, sticky='w', pady=3)
        self.max_speed_var = tk.StringVar(value=str(self.config["max_speed"]))
        self.max_speed_entry = ttk.Entry(frame, textvariable=self.max_speed_var, style='App.TEntry', width=8)
        self.max_speed_entry.grid(row=3, column=3, sticky='ew', padx=(8, 0), pady=3)
        tk.Label(frame, text='固定延迟', font=self.font_small, bg='#ffffff', fg='#475569').grid(row=4, column=0, sticky='w', pady=3)
        self.fixed_speed_var = tk.StringVar(value=str(self.config.get("fixed_speed", 100)))
        self.fixed_speed_entry = ttk.Entry(frame, textvariable=self.fixed_speed_var, style='App.TEntry', width=8)
        self.fixed_speed_entry.grid(row=4, column=1, sticky='ew', padx=(8, 18), pady=3)
        tk.Label(frame, text='单位：毫秒', font=self.font_small, bg='#ffffff', fg='#94a3b8').grid(row=4, column=2, columnspan=2, sticky='w', pady=3)
        
        self.on_random_toggle()
    
    def create_hotkey_section(self, parent, row):
        frame = tk.Frame(parent, bg='#ffffff', highlightbackground='#e5e7eb', highlightthickness=1, padx=14, pady=12)
        frame.grid(row=row, column=0, sticky='ew', pady=(0, 10))
        tk.Label(frame, text='快捷键', bg='#ffffff', fg='#17202a', font=('Microsoft YaHei UI', 11, 'bold')).pack(anchor='w')
        tk.Label(frame, text='设置后自动保存。建议避开系统常用快捷键。', bg='#ffffff', fg='#64748b', font=self.font_small).pack(anchor='w', pady=(3, 7))
        
        self.create_hotkey_row(frame, "开始输入", lambda: self.config["hotkey"], self.start_set_start_hotkey)
        self.create_hotkey_row(frame, "停止输入", lambda: self.config["stop_hotkey"], self.start_set_stop_hotkey)
    
    def create_hotkey_row(self, parent, label, get_config, set_cmd):
        row_frame = tk.Frame(parent, bg='#ffffff')
        row_frame.pack(fill=tk.X, pady=4)
        
        tk.Label(row_frame, text=label, font=self.font_small, width=9, anchor=tk.W,
                bg='#ffffff', fg='#475569').pack(side=tk.LEFT)
        
        var = tk.StringVar(value=get_config())
        if label == "开始输入":
            self.hotkey_var = var
        else:
            self.stop_hotkey_var = var
        
        entry_frame = tk.Frame(row_frame, bg='#f8fafc', highlightbackground='#dbe3ec', highlightthickness=1, padx=10, pady=5)
        entry_frame.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        tk.Label(entry_frame, textvariable=var, font=self.mono_font,
                bg='#f8fafc', fg='#111827').pack(anchor=tk.W)
        ttk.Button(row_frame, text='修改', command=set_cmd, style='Secondary.TButton').pack(side=tk.LEFT)
    
    def create_tray_section(self, parent, row):
        frame = tk.Frame(parent, bg='#ffffff', highlightbackground='#e5e7eb', highlightthickness=1, padx=14, pady=10)
        frame.grid(row=row, column=0, sticky='ew', pady=(0, 10))
        frame.columnconfigure(0, weight=1)
        tk.Label(frame, text='托盘', bg='#ffffff', fg='#17202a', font=('Microsoft YaHei UI', 11, 'bold')).grid(row=0, column=0, sticky='w')
        
        if HAS_PYSTRAY:
            self.hide_to_tray_var = tk.BooleanVar(value=self.config.get("hide_to_tray", True))
            ttk.Checkbutton(frame, text='关闭窗口时隐藏到系统托盘', variable=self.hide_to_tray_var, command=self.on_tray_setting_change, style='App.TCheckbutton').grid(row=1, column=0, sticky='w', pady=(6, 0))
            tk.Label(frame, text='隐藏后可通过托盘图标恢复窗口或退出程序', font=self.font_small, bg='#ffffff', fg='#94a3b8').grid(row=2, column=0, sticky='w', pady=(3, 0))
        else:
            tk.Label(frame, text="⚠ 未安装 pystray 库，托盘功能不可用\n请运行: pip install pystray", 
                    font=self.font_small, bg='#ffffff', fg='#dc2626').grid(row=1, column=0, sticky='w', pady=(6, 0))
    
    def create_status_section(self, parent, row):
        frame = tk.Frame(parent, bg='#17202a', highlightbackground='#17202a', highlightthickness=1, padx=14, pady=11)
        frame.grid(row=row, column=0, sticky='ew', pady=(0, 10))
        tk.Label(frame, text='运行状态', font=('Microsoft YaHei UI', 10, 'bold'), bg='#17202a', fg='#ffffff').pack(anchor='w', pady=(0, 6))
        self.status_var = tk.StringVar(value="✓ 就绪 - 复制文本后按快捷键开始输入")
        self.status_label = tk.Label(frame, textvariable=self.status_var, 
                                     font=self.font_small, bg='#17202a', fg='#d7e2ef',
                                     wraplength=460, justify=tk.LEFT)
        self.status_label.pack(anchor=tk.W)
    
    def create_button_section(self, parent, row):
        frame = tk.Frame(parent, bg='#f7f8fa')
        frame.grid(row=row, column=0, sticky='ew')
        frame.columnconfigure((0, 1), weight=1, uniform='actions')
        self.save_btn = ttk.Button(frame, text='保存设置', command=self.save_settings, style='Secondary.TButton')
        self.save_btn.grid(row=0, column=0, sticky='ew', padx=(0, 4))
        self.test_btn = ttk.Button(frame, text='测试输入', command=self.test_input, style='Primary.TButton')
        self.test_btn.grid(row=0, column=1, sticky='ew', padx=(4, 0))
        self.stop_btn = ttk.Button(frame, text='停止输入', command=self.stop_typing, state=tk.DISABLED, style='Danger.TButton')
        self.stop_btn.grid(row=1, column=0, sticky='ew', padx=(0, 4), pady=(8, 0))
        if HAS_PYSTRAY:
            ttk.Button(frame, text='隐藏到托盘', command=self.hide_to_tray, style='Secondary.TButton').grid(row=1, column=1, sticky='ew', padx=(4, 0), pady=(8, 0))
    
    def on_random_toggle(self):
        use_random = self.use_random_var.get()
        if use_random:
            self.min_speed_entry.configure(state='normal')
            self.max_speed_entry.configure(state='normal')
            self.fixed_speed_entry.configure(state='disabled')
        else:
            self.min_speed_entry.configure(state='disabled')
            self.max_speed_entry.configure(state='disabled')
            self.fixed_speed_entry.configure(state='normal')
    
    def on_tray_setting_change(self):
        self.config["hide_to_tray"] = self.hide_to_tray_var.get()
        self.save_config()
        status = "启用" if self.config["hide_to_tray"] else "禁用"
        self.status_var.set(f"✓ 托盘设置已{status}并保存")
    
    def start_set_start_hotkey(self):
        load_keyboard()
        self.is_setting_hotkey = True
        self.setting_stop_hotkey = False
        self.pressed_keys.clear()
        self.hotkey_var.set("请按下...")
        self.status_var.set("⌨ 请按下新的开始快捷键...")
        
        self.hook_handle = keyboard.hook(self.on_key_event)
    
    def start_set_stop_hotkey(self):
        load_keyboard()
        self.is_setting_hotkey = True
        self.setting_stop_hotkey = True
        self.pressed_keys.clear()
        self.stop_hotkey_var.set("请按下...")
        self.status_var.set("⌨ 请按下新的停止快捷键...")
        
        self.hook_handle = keyboard.hook(self.on_key_event)
    
    def on_key_event(self, event):
        if not self.is_setting_hotkey:
            return
            
        if event.event_type == keyboard.KEY_DOWN:
            self.pressed_keys.add(event.name)
        elif event.event_type == keyboard.KEY_UP:
            if len(self.pressed_keys) > 0:
                modifiers = {'ctrl', 'alt', 'shift', 'windows'}
                keys = list(self.pressed_keys)
                
                has_modifier = any(k in modifiers for k in keys)
                normal_keys = [k for k in keys if k not in modifiers]
                
                if has_modifier and len(normal_keys) > 0:
                    hotkey_parts = []
                    for mod in ['ctrl', 'alt', 'shift', 'windows']:
                        if mod in keys:
                            hotkey_parts.append(mod)
                    hotkey_parts.extend(normal_keys[:1])
                    
                    new_hotkey = '+'.join(hotkey_parts)
                    
                    if self.hook_handle:
                        keyboard.unhook(self.hook_handle)
                        self.hook_handle = None
                    self.is_setting_hotkey = False
                    
                    new_hotkey_lower = new_hotkey.lower()
                    
                    if self.setting_stop_hotkey:
                        if new_hotkey == self.config["hotkey"]:
                            self.root.after(0, lambda: self.status_var.set("⚠ 停止快捷键不能与开始快捷键相同"))
                            self.root.after(0, lambda: self.stop_hotkey_var.set(self.config["stop_hotkey"]))
                            return
                        self.config["stop_hotkey"] = new_hotkey
                        self.root.after(0, lambda: self.stop_hotkey_var.set(new_hotkey))
                        self.root.after(0, lambda: self.status_var.set(f"✓ 停止快捷键已更新为: {new_hotkey}"))
                    else:
                        if new_hotkey == self.config["stop_hotkey"]:
                            self.root.after(0, lambda: self.status_var.set("⚠ 开始快捷键不能与停止快捷键相同"))
                            self.root.after(0, lambda: self.hotkey_var.set(self.config["hotkey"]))
                            return
                        self.config["hotkey"] = new_hotkey
                        self.root.after(0, lambda: self.hotkey_var.set(new_hotkey))
                        self.root.after(0, lambda: self.status_var.set(f"✓ 开始快捷键已更新为: {new_hotkey}"))
                    
                    self.register_hotkeys()
                    self.save_config()
    
    def register_hotkeys(self):
        load_keyboard()
        try:
            if self.start_hotkey_hook:
                self.start_hotkey_hook()
                self.start_hotkey_hook = None
            if self.stop_hotkey_hook:
                self.stop_hotkey_hook()
                self.stop_hotkey_hook = None
            
            start_hotkey = self.config.get("hotkey", DEFAULT_CONFIG["hotkey"])
            stop_hotkey = self.config.get("stop_hotkey", "ctrl+a")
            
            self.start_hotkey_hook = keyboard.add_hotkey(
                start_hotkey, 
                self.start_typing
            )
            self.stop_hotkey_hook = keyboard.add_hotkey(
                stop_hotkey, 
                self.stop_typing
            )

            self.status_var.set(f"✓ 就绪 - 开始: {start_hotkey}, 停止: {stop_hotkey}")
            print(f"快捷键已注册: 开始={start_hotkey}, 停止={stop_hotkey}")
        except Exception as e:
            error_msg = str(e)
            print(f"注册快捷键失败: {error_msg}")
            self.root.after(0, lambda msg=error_msg: messagebox.showerror("错误", f"注册快捷键失败: {msg}"))
    
    def start_typing(self):
        load_pyperclip()
        if self.is_typing:
            return
            
        try:
            text = pyperclip.paste()
        except:
            text = ""
            
        if not text:
            self.root.after(0, lambda: self.status_var.set("⚠ 剪贴板为空，请先复制文本"))
            return
        
        self.is_typing = True
        self.root.after(0, lambda: self.stop_btn.config(state=tk.NORMAL))
        self.root.after(0, lambda: self.status_var.set("▶ 正在输入..."))
        
        self.typing_thread = threading.Thread(target=self.type_text, args=(text,), daemon=True)
        self.typing_thread.start()
    
    def type_text(self, text):
        completed = False
        try:
            use_random = self.config.get("use_random_speed", True)
            
            if use_random:
                try:
                    min_speed = int(self.config["min_speed"])
                    max_speed = int(self.config["max_speed"])
                    if min_speed > max_speed:
                        min_speed, max_speed = max_speed, min_speed
                except ValueError:
                    min_speed = 50
                    max_speed = 150
            else:
                try:
                    fixed_speed = int(self.config["fixed_speed"])
                except ValueError:
                    fixed_speed = 100
            
            # 释放所有修饰键，避免影响输入
            for key in ['alt', 'ctrl', 'shift', 'win']:
                if keyboard.is_pressed(key):
                    keyboard.release(key)
                    time.sleep(0.1)
            
            for char in text:
                if not self.is_typing:
                    break
                    
                # 逐字符按文本写入，避免 @、大写字母等字符被当作按键名解析
                keyboard.write(char, delay=0, exact=True)
                
                if use_random:
                    delay = random.randint(min_speed, max_speed) / 1000.0
                else:
                    delay = fixed_speed / 1000.0
                    
                time.sleep(delay)
            completed = self.is_typing
        except Exception as e:
            error_message = str(e)
            self.root.after(0, lambda msg=error_message: self.status_var.set(f"⚠ 输入错误: {msg}"))
        finally:
            self.is_typing = False
            self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
            if completed:
                self.root.after(0, lambda: self.status_var.set("✓ 输入完成"))
    
    def stop_typing(self):
        self.is_typing = False
        self.root.after(0, lambda: self.status_var.set("⏹ 输入已停止"))
        self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
    
    def test_input(self):
        load_pyperclip()
        test_text = "这是一段测试文本，用于测试模拟输入功能。"
        pyperclip.copy(test_text)
        self.status_var.set("✓ 已复制测试文本，请将光标放在输入框中，然后按快捷键")
        messagebox.showinfo("提示", f"测试文本已复制到剪贴板:\n\n{test_text}\n\n请将光标放在任意输入框中，然后按 {self.config['hotkey']} 开始输入")
    
    def save_settings(self):
        try:
            self.config["min_speed"] = int(self.min_speed_var.get())
            self.config["max_speed"] = int(self.max_speed_var.get())
            self.config["fixed_speed"] = int(self.fixed_speed_var.get())
            self.config["use_random_speed"] = self.use_random_var.get()
            if HAS_PYSTRAY:
                self.config["hide_to_tray"] = self.hide_to_tray_var.get()
            
            if self.config["min_speed"] > self.config["max_speed"]:
                self.config["min_speed"], self.config["max_speed"] = self.config["max_speed"], self.config["min_speed"]
                self.min_speed_var.set(str(self.config["min_speed"]))
                self.max_speed_var.set(str(self.config["max_speed"]))
            
            self.save_config()
            self.status_var.set("✓ 设置已保存")
            messagebox.showinfo("成功", "设置已保存")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
    
    def create_tray_icon(self):
        pystray_module, Image, ImageDraw = load_tray()

        def create_image():
            width = 64
            height = 64
            color1 = (15, 118, 110)
            color2 = (255, 255, 255)
            image = Image.new('RGB', (width, height), color2)
            dc = ImageDraw.Draw(image)
            dc.rectangle([8, 8, 56, 56], fill=color1)
            dc.rectangle([16, 20, 48, 28], fill=color2)
            dc.rectangle([16, 32, 48, 40], fill=color2)
            dc.rectangle([16, 44, 36, 52], fill=color2)
            return image
        
        return pystray_module.Icon(
            "simulated_input",
            create_image(),
            "模拟输入工具",
            menu=pystray_module.Menu(
                pystray_module.MenuItem("显示窗口", self.show_window, default=True),
                pystray_module.MenuItem("开始输入", self.start_typing),
                pystray_module.MenuItem("停止输入", self.stop_typing),
                pystray_module.Menu.SEPARATOR,
                pystray_module.MenuItem("退出", self.quit_app)
            )
        )
    
    def setup_tray(self):
        self.tray_icon = self.create_tray_icon()
        tray_thread = threading.Thread(target=self.run_tray, daemon=True)
        tray_thread.start()
    
    def run_tray(self):
        if self.tray_icon:
            self.tray_icon.run()
    
    def hide_to_tray(self):
        if HAS_PYSTRAY:
            self.is_hidden = True
            self.root.withdraw()
    
    def show_window(self, icon=None, item=None):
        self.is_hidden = False
        self.root.after(0, self.root.deiconify)
    
    def quit_app(self, icon=None, item=None):
        self.is_typing = False
        try:
            keyboard.unhook_all()
        except:
            pass
        self.save_config()
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self.root.destroy)
    
    def on_closing(self):
        if HAS_PYSTRAY and self.tray_icon:
            if self.config.get("hide_to_tray", True):
                self.hide_to_tray()
            else:
                self.quit_app()
        else:
            self.quit_app()

def main():
    handle = acquire_instance()
    if sys.platform == 'win32' and handle is None:
        return
    try:
        if sys.platform == 'win32' and not is_admin():
            # 提权后的新进程接管互斥锁。
            ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(handle))
            handle = None
            if not run_as_admin():
                enable_dpi_awareness()
                root = tk.Tk()
                root.withdraw()
                messagebox.showwarning('权限不足', '请右键点击程序，选择「以管理员身份运行」', parent=root)
                root.destroy()
            return
        run_app()
    finally:
        if handle is not None:
            ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(handle))

def run_app():
    enable_dpi_awareness()
    root = tk.Tk()
    app = SimulatedInputApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
