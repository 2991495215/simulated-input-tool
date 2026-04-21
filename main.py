import ctypes
import sys
import os
from ctypes import wintypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    if sys.platform == 'win32':
        script = os.path.abspath(sys.argv[0])
        params = ' '.join([script] + sys.argv[1:])
        try:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
            return True
        except:
            return False
    return False

if not is_admin():
    print("需要管理员权限来监听全局键盘事件...")
    if run_as_admin():
        sys.exit(0)
    else:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(
            "权限不足",
            "此程序需要管理员权限才能监听全局键盘事件！\n\n"
            "请右键点击程序，选择「以管理员身份运行」"
        )
        root.destroy()
        sys.exit(1)

import tkinter as tk
from tkinter import ttk, messagebox
import keyboard
import pyperclip
import threading
import random
import json
import time
from PIL import Image, ImageDraw

try:
    import pystray
    HAS_PYSTRAY = True
except ImportError:
    HAS_PYSTRAY = False

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
    "hotkey": "alt+v",
    "stop_hotkey": "ctrl+a",
    "use_random_speed": True,
    "fixed_speed": 100,
    "hide_to_tray": True,
    "asked_hide_to_tray": False
}

class SimulatedInputApp:
    def __init__(self, root):
        self.root = root
        self.root.title("模拟输入工具")
        self.root.geometry("620x680")
        self.root.resizable(True, True)
        self.root.configure(bg='#eef2f7')
        
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
        
        self.root.after(100, self.init_keyboard)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        if HAS_PYSTRAY:
            self.setup_tray()
    
    def init_keyboard(self):
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
            "primary": ("#0f766e", "#ffffff", "#115e59"),
            "success": ("#15803d", "#ffffff", "#166534"),
            "danger": ("#dc2626", "#ffffff", "#b91c1c"),
            "muted": ("#475569", "#ffffff", "#334155"),
            "light": ("#e5e7eb", "#111827", "#d1d5db"),
        }
        bg, fg, active_bg = styles.get(kind, styles["primary"])
        return {
            "font": ('Microsoft YaHei', 10, 'bold'),
            "bg": bg,
            "fg": fg,
            "activebackground": active_bg,
            "activeforeground": fg,
            "relief": "flat",
            "bd": 0,
            "padx": 14,
            "pady": 7,
            "cursor": "hand2",
        }

    def create_card(self, parent, pady=(0, 14)):
        frame = tk.Frame(
            parent,
            bg='#ffffff',
            highlightbackground='#d7dde8',
            highlightthickness=1,
            padx=16,
            pady=12
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
        header = tk.Frame(self.root, bg='#111827', height=92)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        title_label = tk.Label(
            header,
            text="模拟输入工具",
            font=('Microsoft YaHei', 22, 'bold'),
            bg='#111827',
            fg='#f9fafb'
        )
        title_label.pack(anchor=tk.W, padx=24, pady=(12, 4))
        
        subtitle = tk.Label(
            header,
            text="复制文本，按快捷键，逐字符写入当前输入框。",
            font=('Microsoft YaHei', 10),
            bg='#111827',
            fg='#cbd5e1'
        )
        subtitle.pack(anchor=tk.W, padx=26)
        
        body = tk.Frame(self.root, bg='#eef2f7')
        body.pack(fill=tk.BOTH, expand=True, padx=20, pady=(12, 10))

        self.content_canvas = tk.Canvas(
            body,
            bg='#eef2f7',
            highlightthickness=0,
            bd=0
        )
        scrollbar = tk.Scrollbar(body, orient=tk.VERTICAL, command=self.content_canvas.yview)
        self.content_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.content_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        main_container = tk.Frame(self.content_canvas, bg='#eef2f7')
        self.scroll_window = self.content_canvas.create_window((0, 0), window=main_container, anchor=tk.NW)
        main_container.bind("<Configure>", self.update_scroll_region)
        self.content_canvas.bind("<Configure>", self.sync_scroll_width)
        self.content_canvas.bind_all("<MouseWheel>", self.on_mousewheel)

        guide = tk.Frame(main_container, bg='#dff7ef', highlightbackground='#a7f3d0', highlightthickness=1, padx=14, pady=8)
        guide.pack(fill=tk.X, pady=(0, 10))
        tk.Label(
            guide,
            text=f"开始: {self.config.get('hotkey', 'alt+v')}    停止: {self.config.get('stop_hotkey', 'ctrl+a')}",
            font=('Microsoft YaHei', 10, 'bold'),
            bg='#dff7ef',
            fg='#064e3b'
        ).pack(anchor=tk.W)
        tk.Label(
            guide,
            text="先复制要输入的内容，再把光标放到目标位置。",
            font=('Microsoft YaHei', 9),
            bg='#dff7ef',
            fg='#047857'
        ).pack(anchor=tk.W, pady=(2, 0))
        
        self.create_speed_section(main_container)
        self.create_hotkey_section(main_container)
        self.create_tray_section(main_container)
        self.create_status_section(main_container)
        self.create_button_section(main_container)
    
    def create_speed_section(self, parent):
        frame = self.create_card(parent)
        self.create_section_title(frame, "输入速度", "随机速度更像人工输入；固定速度适合稳定复现。")

        header_frame = tk.Frame(frame, bg='#ffffff')
        header_frame.pack(fill=tk.X, pady=(0, 8))
        
        self.use_random_var = tk.BooleanVar(value=self.config.get("use_random_speed", True))
        random_check = tk.Checkbutton(header_frame, text="随机速度", 
                                      variable=self.use_random_var,
                                      command=self.on_random_toggle,
                                      font=('Microsoft YaHei', 10, 'bold'),
                                      bg='#ffffff', fg='#0f766e',
                                      activebackground='#ffffff', activeforeground='#0f766e',
                                      selectcolor='#ccfbf1')
        random_check.pack(anchor=tk.W)
        
        speed_grid = tk.Frame(frame, bg='#ffffff')
        speed_grid.pack(fill=tk.X)
        speed_grid.columnconfigure(1, weight=1)
        speed_grid.columnconfigure(3, weight=1)
        
        tk.Label(speed_grid, text="最小延迟", font=('Microsoft YaHei', 9),
                bg='#ffffff', fg='#475569').grid(row=0, column=0, sticky=tk.W, pady=4)
        self.min_speed_var = tk.StringVar(value=str(self.config["min_speed"]))
        self.min_speed_entry = self.create_entry(speed_grid, self.min_speed_var)
        self.min_speed_entry.grid(row=0, column=1, sticky=tk.EW, padx=(8, 18), pady=4, ipady=5)
        
        tk.Label(speed_grid, text="最大延迟", font=('Microsoft YaHei', 9),
                bg='#ffffff', fg='#475569').grid(row=0, column=2, sticky=tk.W, pady=4)
        self.max_speed_var = tk.StringVar(value=str(self.config["max_speed"]))
        self.max_speed_entry = self.create_entry(speed_grid, self.max_speed_var)
        self.max_speed_entry.grid(row=0, column=3, sticky=tk.EW, padx=(8, 0), pady=4, ipady=5)
        
        tk.Label(speed_grid, text="固定延迟", font=('Microsoft YaHei', 9),
                bg='#ffffff', fg='#475569').grid(row=1, column=0, sticky=tk.W, pady=4)
        self.fixed_speed_var = tk.StringVar(value=str(self.config.get("fixed_speed", 100)))
        self.fixed_speed_entry = self.create_entry(speed_grid, self.fixed_speed_var)
        self.fixed_speed_entry.grid(row=1, column=1, sticky=tk.EW, padx=(8, 18), pady=4, ipady=5)

        tk.Label(speed_grid, text="单位: ms", font=('Microsoft YaHei', 9),
                bg='#ffffff', fg='#94a3b8').grid(row=1, column=2, columnspan=2, sticky=tk.W, pady=4)
        
        self.on_random_toggle()
    
    def create_hotkey_section(self, parent):
        frame = self.create_card(parent)
        self.create_section_title(frame, "快捷键", "设置后会自动保存。建议避开系统常用快捷键。")
        
        self.create_hotkey_row(frame, "开始输入", lambda: self.config["hotkey"], self.start_set_start_hotkey)
        self.create_hotkey_row(frame, "停止输入", lambda: self.config["stop_hotkey"], self.start_set_stop_hotkey)
    
    def create_hotkey_row(self, parent, label, get_config, set_cmd):
        row_frame = tk.Frame(parent, bg='#ffffff')
        row_frame.pack(fill=tk.X, pady=4)
        
        tk.Label(row_frame, text=label + ":", font=('Microsoft YaHei', 9), width=10, anchor=tk.W,
                bg='#ffffff', fg='#475569').pack(side=tk.LEFT)
        
        var = tk.StringVar(value=get_config())
        if label == "开始输入":
            self.hotkey_var = var
        else:
            self.stop_hotkey_var = var
        
        entry_frame = tk.Frame(row_frame, bg='#f8fafc', highlightbackground='#cbd5e1', highlightthickness=1, padx=12, pady=6)
        entry_frame.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        tk.Label(entry_frame, textvariable=var, font=('Microsoft YaHei', 10, 'bold'),
                bg='#f8fafc', fg='#111827').pack(anchor=tk.W)
        
        btn = tk.Button(row_frame, text="设置", command=set_cmd, **self.button_style("light"))
        btn.pack(side=tk.LEFT)
    
    def create_tray_section(self, parent):
        frame = self.create_card(parent)
        self.create_section_title(frame, "托盘", "关闭窗口时可以继续在后台监听快捷键。")
        
        if HAS_PYSTRAY:
            self.hide_to_tray_var = tk.BooleanVar(value=self.config.get("hide_to_tray", True))
            tray_check = tk.Checkbutton(frame, text="关闭窗口时隐藏到系统托盘", 
                                        variable=self.hide_to_tray_var,
                                        command=self.on_tray_setting_change,
                                        font=('Microsoft YaHei', 10),
                                        bg='#ffffff', fg='#475569',
                                        activebackground='#ffffff', activeforeground='#0f766e',
                                        selectcolor='#ccfbf1')
            tray_check.pack(anchor=tk.W)
            
            tk.Label(frame, text="隐藏后可通过托盘图标恢复窗口或退出程序", 
                    font=('Microsoft YaHei', 9), bg='#ffffff', fg='#94a3b8').pack(anchor=tk.W, pady=(4, 0))
        else:
            tk.Label(frame, text="⚠ 未安装 pystray 库，托盘功能不可用\n请运行: pip install pystray", 
                    font=('Microsoft YaHei', 9), bg='#ffffff', fg='#dc2626').pack(anchor=tk.W)
    
    def create_status_section(self, parent):
        frame = tk.Frame(parent, bg='#172033', highlightbackground='#0f172a', 
                         highlightthickness=1, padx=16, pady=12)
        frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(frame, text="当前状态", font=('Microsoft YaHei', 11, 'bold'),
                bg='#172033', fg='#e5e7eb').pack(anchor=tk.W, pady=(0, 8))
        
        self.status_var = tk.StringVar(value="✓ 就绪 - 复制文本后按快捷键开始输入")
        self.status_label = tk.Label(frame, textvariable=self.status_var, 
                                     font=('Microsoft YaHei', 10), bg='#172033', fg='#a7f3d0',
                                     wraplength=460, justify=tk.LEFT)
        self.status_label.pack(anchor=tk.W)
    
    def create_button_section(self, parent):
        frame = tk.Frame(parent, bg='#eef2f7')
        frame.pack(fill=tk.X)
        
        self.save_btn = tk.Button(frame, text="保存设置", command=self.save_settings, **self.button_style("success"))
        self.save_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        self.test_btn = tk.Button(frame, text="测试输入", command=self.test_input, **self.button_style("primary"))
        self.test_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        self.stop_btn = tk.Button(frame, text="停止输入", command=self.stop_typing,
                                  state=tk.DISABLED, **self.button_style("danger"))
        self.stop_btn.pack(side=tk.LEFT)
        
        if HAS_PYSTRAY:
            hide_btn = tk.Button(frame, text="隐藏到托盘", command=self.hide_to_tray, **self.button_style("muted"))
            hide_btn.pack(side=tk.RIGHT)
    
    def on_random_toggle(self):
        use_random = self.use_random_var.get()
        if use_random:
            self.min_speed_entry.config(state=tk.NORMAL, bg='#f8fafc', fg='#111827')
            self.max_speed_entry.config(state=tk.NORMAL, bg='#f8fafc', fg='#111827')
            self.fixed_speed_entry.config(state=tk.DISABLED, bg='#e5e7eb', fg='#94a3b8')
        else:
            self.min_speed_entry.config(state=tk.DISABLED, bg='#e5e7eb', fg='#94a3b8')
            self.max_speed_entry.config(state=tk.DISABLED, bg='#e5e7eb', fg='#94a3b8')
            self.fixed_speed_entry.config(state=tk.NORMAL, bg='#f8fafc', fg='#111827')
    
    def on_tray_setting_change(self):
        self.config["hide_to_tray"] = self.hide_to_tray_var.get()
        self.save_config()
        status = "启用" if self.config["hide_to_tray"] else "禁用"
        self.status_var.set(f"✓ 托盘设置已{status}并保存")

    def send_unicode_char(self, char):
        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
            ]

        class INPUTUNION(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT)]

        class INPUT(ctypes.Structure):
            _fields_ = [
                ("type", wintypes.DWORD),
                ("union", INPUTUNION),
            ]

        INPUT_KEYBOARD = 1
        KEYEVENTF_KEYUP = 0x0002
        KEYEVENTF_UNICODE = 0x0004

        def send_unit(unit):
            extra = ctypes.pointer(wintypes.ULONG(0))
            inputs = (INPUT * 2)(
                INPUT(INPUT_KEYBOARD, INPUTUNION(KEYBDINPUT(0, unit, KEYEVENTF_UNICODE, 0, extra))),
                INPUT(INPUT_KEYBOARD, INPUTUNION(KEYBDINPUT(0, unit, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, extra))),
            )
            sent = ctypes.windll.user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))
            if sent != 2:
                raise ctypes.WinError()

        codepoint = ord(char)
        if codepoint <= 0xFFFF:
            send_unit(codepoint)
            return

        codepoint -= 0x10000
        send_unit(0xD800 + (codepoint >> 10))
        send_unit(0xDC00 + (codepoint & 0x3FF))
    
    def start_set_start_hotkey(self):
        self.is_setting_hotkey = True
        self.setting_stop_hotkey = False
        self.pressed_keys.clear()
        self.hotkey_var.set("请按下...")
        self.status_var.set("⌨ 请按下新的开始快捷键...")
        
        self.hook_handle = keyboard.hook(self.on_key_event)
    
    def start_set_stop_hotkey(self):
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
        try:
            if self.start_hotkey_hook:
                self.start_hotkey_hook()
                self.start_hotkey_hook = None
            if self.stop_hotkey_hook:
                self.stop_hotkey_hook()
                self.stop_hotkey_hook = None
            
            start_hotkey = self.config.get("hotkey", "alt+v")
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
                    
                self.send_unicode_char(char)
                
                if use_random:
                    delay = random.randint(min_speed, max_speed) / 1000.0
                else:
                    delay = fixed_speed / 1000.0
                    
                time.sleep(delay)
                
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"⚠ 输入错误: {str(e)}"))
        finally:
            self.is_typing = False
            self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
            if self.is_typing == False:
                self.root.after(0, lambda: self.status_var.set("✓ 输入完成"))
    
    def stop_typing(self):
        self.is_typing = False
        self.root.after(0, lambda: self.status_var.set("⏹ 输入已停止"))
        self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
    
    def test_input(self):
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
        
        return pystray.Icon(
            "simulated_input",
            create_image(),
            "模拟输入工具",
            menu=pystray.Menu(
                pystray.MenuItem("显示窗口", self.show_window, default=True),
                pystray.MenuItem("开始输入", self.start_typing),
                pystray.MenuItem("停止输入", self.stop_typing),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", self.quit_app)
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
    root = tk.Tk()
    app = SimulatedInputApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
