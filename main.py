import ctypes
import sys
import os

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

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
DEFAULT_CONFIG = {
    "min_speed": 50,
    "max_speed": 150,
    "hotkey": "alt+v",
    "stop_hotkey": "alt+b",
    "use_random_speed": True,
    "fixed_speed": 100,
    "hide_to_tray": True,
    "asked_hide_to_tray": False
}

CONFLICT_HOTKEYS = {
    'ctrl+a': '全选',
    'ctrl+c': '复制',
    'ctrl+v': '粘贴',
    'ctrl+x': '剪切',
    'ctrl+z': '撤销',
    'ctrl+s': '保存',
    'ctrl+f': '查找',
    'ctrl+p': '打印',
    'alt+f4': '关闭窗口',
    'alt+tab': '切换窗口',
}

class SimulatedInputApp:
    def __init__(self, root):
        self.root = root
        self.root.title("模拟输入工具")
        self.root.geometry("480x620")
        self.root.resizable(False, False)
        self.root.configure(bg='#ffffff')
        
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
    
    def setup_ui(self):
        header = tk.Frame(self.root, bg='#2563eb', height=120)
        header.pack(fill=tk.X)
        
        title_label = tk.Label(header, text="⌨ 模拟输入工具", 
                               font=('Microsoft YaHei', 24, 'bold'),
                               bg='#2563eb', fg='white')
        title_label.pack(pady=(25, 5))
        
        subtitle = tk.Label(header, text="从剪贴板读取文本并模拟键盘输入", 
                            font=('Microsoft YaHei', 10),
                            bg='#2563eb', fg='#dbeafe')
        subtitle.pack()
        
        main_container = tk.Frame(self.root, bg='#f8fafc')
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.create_speed_section(main_container)
        self.create_hotkey_section(main_container)
        self.create_tray_section(main_container)
        self.create_status_section(main_container)
        self.create_button_section(main_container)
    
    def create_speed_section(self, parent):
        frame = tk.Frame(parent, bg='white', highlightbackground='#e2e8f0', 
                         highlightthickness=1, padx=20, pady=15)
        frame.pack(fill=tk.X, pady=(0, 12))
        
        header_frame = tk.Frame(frame, bg='white')
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(header_frame, text="⚡ 输入速度", font=('Microsoft YaHei', 11, 'bold'),
                bg='white', fg='#1e293b').pack(side=tk.LEFT)
        
        self.use_random_var = tk.BooleanVar(value=self.config.get("use_random_speed", True))
        random_check = tk.Checkbutton(header_frame, text="随机速度", 
                                      variable=self.use_random_var,
                                      command=self.on_random_toggle,
                                      font=('Microsoft YaHei', 9),
                                      bg='white', fg='#475569',
                                      activebackground='white', activeforeground='#2563eb',
                                      selectcolor='#dbeafe')
        random_check.pack(side=tk.RIGHT)
        
        speed_grid = tk.Frame(frame, bg='white')
        speed_grid.pack(fill=tk.X)
        
        tk.Label(speed_grid, text="最小延迟 (ms):", font=('Microsoft YaHei', 9),
                bg='white', fg='#475569').grid(row=0, column=0, sticky=tk.W, pady=4)
        self.min_speed_var = tk.StringVar(value=str(self.config["min_speed"]))
        self.min_speed_entry = tk.Entry(speed_grid, textvariable=self.min_speed_var, 
                                       width=10, font=('Microsoft YaHei', 10),
                                       bg='#f1f5f9', relief='flat', bd=0)
        self.min_speed_entry.grid(row=0, column=1, padx=(8, 20), pady=4)
        
        tk.Label(speed_grid, text="最大延迟 (ms):", font=('Microsoft YaHei', 9),
                bg='white', fg='#475569').grid(row=0, column=2, sticky=tk.W, pady=4)
        self.max_speed_var = tk.StringVar(value=str(self.config["max_speed"]))
        self.max_speed_entry = tk.Entry(speed_grid, textvariable=self.max_speed_var, 
                                       width=10, font=('Microsoft YaHei', 10),
                                       bg='#f1f5f9', relief='flat', bd=0)
        self.max_speed_entry.grid(row=0, column=3, padx=(8, 0), pady=4)
        
        tk.Label(speed_grid, text="固定延迟 (ms):", font=('Microsoft YaHei', 9),
                bg='white', fg='#475569').grid(row=1, column=0, sticky=tk.W, pady=4)
        self.fixed_speed_var = tk.StringVar(value=str(self.config.get("fixed_speed", 100)))
        self.fixed_speed_entry = tk.Entry(speed_grid, textvariable=self.fixed_speed_var, 
                                         width=10, font=('Microsoft YaHei', 10),
                                         bg='#f1f5f9', relief='flat', bd=0)
        self.fixed_speed_entry.grid(row=1, column=1, padx=(8, 20), pady=4)
        
        self.on_random_toggle()
    
    def create_hotkey_section(self, parent):
        frame = tk.Frame(parent, bg='white', highlightbackground='#e2e8f0', 
                         highlightthickness=1, padx=20, pady=15)
        frame.pack(fill=tk.X, pady=(0, 12))
        
        tk.Label(frame, text="⌨ 快捷键设置", font=('Microsoft YaHei', 11, 'bold'),
                bg='white', fg='#1e293b').pack(anchor=tk.W, pady=(0, 12))
        
        self.create_hotkey_row(frame, "开始输入", lambda: self.config["hotkey"], self.start_set_start_hotkey)
        self.create_hotkey_row(frame, "停止输入", lambda: self.config["stop_hotkey"], self.start_set_stop_hotkey)
    
    def create_hotkey_row(self, parent, label, get_config, set_cmd):
        row_frame = tk.Frame(parent, bg='white')
        row_frame.pack(fill=tk.X, pady=6)
        
        tk.Label(row_frame, text=label + ":", font=('Microsoft YaHei', 9), width=10, anchor=tk.W,
                bg='white', fg='#475569').pack(side=tk.LEFT)
        
        var = tk.StringVar(value=get_config())
        if label == "开始输入":
            self.hotkey_var = var
        else:
            self.stop_hotkey_var = var
        
        entry_frame = tk.Frame(row_frame, bg='#f1f5f9', padx=10, pady=6)
        entry_frame.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        tk.Label(entry_frame, textvariable=var, font=('Microsoft YaHei', 9),
                bg='#f1f5f9', fg='#1e293b').pack(anchor=tk.W)
        
        btn = tk.Button(row_frame, text="设置", command=set_cmd,
                       font=('Microsoft YaHei', 9), bg='#2563eb', fg='white',
                       relief='flat', padx=12, pady=5, cursor='hand2',
                       activebackground='#1d4ed8', activeforeground='white')
        btn.pack(side=tk.LEFT)
    
    def create_tray_section(self, parent):
        frame = tk.Frame(parent, bg='white', highlightbackground='#e2e8f0', 
                         highlightthickness=1, padx=20, pady=15)
        frame.pack(fill=tk.X, pady=(0, 12))
        
        tk.Label(frame, text="📥 托盘设置", font=('Microsoft YaHei', 11, 'bold'),
                bg='white', fg='#1e293b').pack(anchor=tk.W, pady=(0, 10))
        
        if HAS_PYSTRAY:
            self.hide_to_tray_var = tk.BooleanVar(value=self.config.get("hide_to_tray", True))
            tray_check = tk.Checkbutton(frame, text="关闭窗口时隐藏到系统托盘", 
                                        variable=self.hide_to_tray_var,
                                        command=self.on_tray_setting_change,
                                        font=('Microsoft YaHei', 9),
                                        bg='white', fg='#475569',
                                        activebackground='white', activeforeground='#2563eb',
                                        selectcolor='#dbeafe')
            tray_check.pack(anchor=tk.W)
            
            tk.Label(frame, text="隐藏后可通过托盘图标恢复窗口或退出程序", 
                    font=('Microsoft YaHei', 8), bg='white', fg='#94a3b8').pack(anchor=tk.W, pady=(5, 0))
        else:
            tk.Label(frame, text="⚠ 未安装 pystray 库，托盘功能不可用\n请运行: pip install pystray", 
                    font=('Microsoft YaHei', 9), bg='white', fg='#dc2626').pack(anchor=tk.W)
    
    def create_status_section(self, parent):
        frame = tk.Frame(parent, bg='#eff6ff', highlightbackground='#bfdbfe', 
                         highlightthickness=1, padx=20, pady=15)
        frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(frame, text="📊 状态", font=('Microsoft YaHei', 11, 'bold'),
                bg='#eff6ff', fg='#1e40af').pack(anchor=tk.W, pady=(0, 8))
        
        self.status_var = tk.StringVar(value="✓ 就绪 - 复制文本后按快捷键开始输入")
        self.status_label = tk.Label(frame, textvariable=self.status_var, 
                                     font=('Microsoft YaHei', 9), bg='#eff6ff', fg='#1e3a8a',
                                     wraplength=400, justify=tk.LEFT)
        self.status_label.pack(anchor=tk.W)
    
    def create_button_section(self, parent):
        frame = tk.Frame(parent, bg='#f8fafc')
        frame.pack(fill=tk.X)
        
        self.save_btn = tk.Button(frame, text="💾 保存设置", command=self.save_settings,
                                  font=('Microsoft YaHei', 9, 'bold'), bg='#16a34a', fg='white',
                                  relief='flat', padx=18, pady=8, cursor='hand2',
                                  activebackground='#15803d', activeforeground='white')
        self.save_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        self.test_btn = tk.Button(frame, text="🧪 测试输入", command=self.test_input,
                                 font=('Microsoft YaHei', 9), bg='#2563eb', fg='white',
                                 relief='flat', padx=18, pady=8, cursor='hand2',
                                 activebackground='#1d4ed8', activeforeground='white')
        self.test_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        self.stop_btn = tk.Button(frame, text="⏹ 停止输入", command=self.stop_typing,
                                  font=('Microsoft YaHei', 9), bg='#dc2626', fg='white',
                                  relief='flat', padx=18, pady=8, cursor='hand2',
                                  activebackground='#b91c1c', activeforeground='white',
                                  state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT)
        
        if HAS_PYSTRAY:
            hide_btn = tk.Button(frame, text="📥 隐藏到托盘", command=self.hide_to_tray,
                                 font=('Microsoft YaHei', 9), bg='#64748b', fg='white',
                                 relief='flat', padx=18, pady=8, cursor='hand2',
                                 activebackground='#475569', activeforeground='white')
            hide_btn.pack(side=tk.RIGHT)
    
    def on_random_toggle(self):
        use_random = self.use_random_var.get()
        if use_random:
            self.min_speed_entry.config(state=tk.NORMAL, bg='#f1f5f9')
            self.max_speed_entry.config(state=tk.NORMAL, bg='#f1f5f9')
            self.fixed_speed_entry.config(state=tk.DISABLED, bg='#e2e8f0')
        else:
            self.min_speed_entry.config(state=tk.DISABLED, bg='#e2e8f0')
            self.max_speed_entry.config(state=tk.DISABLED, bg='#e2e8f0')
            self.fixed_speed_entry.config(state=tk.NORMAL, bg='#f1f5f9')
    
    def on_tray_setting_change(self):
        self.config["hide_to_tray"] = self.hide_to_tray_var.get()
        self.save_config()
        status = "启用" if self.config["hide_to_tray"] else "禁用"
        self.status_var.set(f"✓ 托盘设置已{status}并保存")
    
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
                    if new_hotkey_lower in CONFLICT_HOTKEYS:
                        conflict_name = CONFLICT_HOTKEYS[new_hotkey_lower]
                        self.root.after(0, lambda: messagebox.showwarning(
                            "快捷键冲突",
                            f"快捷键 {new_hotkey.upper()} 与系统快捷键【{conflict_name}】冲突！\n\n"
                            f"建议使用其他快捷键，如：\n"
                            f"• Ctrl+Shift+V\n"
                            f"• Alt+Shift+V\n"
                            f"• F9 / F10\n\n"
                            f"是否仍要使用此快捷键？",
                            icon='warning'
                        ))
                    
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
            stop_hotkey = self.config.get("stop_hotkey", "alt+b")
            
            start_hotkey_lower = start_hotkey.lower()
            stop_hotkey_lower = stop_hotkey.lower()
            
            warnings = []
            if start_hotkey_lower in CONFLICT_HOTKEYS:
                warnings.append(f"开始快捷键 {start_hotkey.upper()} 与【{CONFLICT_HOTKEYS[start_hotkey_lower]}】冲突")
            if stop_hotkey_lower in CONFLICT_HOTKEYS:
                warnings.append(f"停止快捷键 {stop_hotkey.upper()} 与【{CONFLICT_HOTKEYS[stop_hotkey_lower]}】冲突")
            
            self.start_hotkey_hook = keyboard.add_hotkey(
                start_hotkey, 
                self.start_typing
            )
            self.stop_hotkey_hook = keyboard.add_hotkey(
                stop_hotkey, 
                self.stop_typing
            )
            
            if warnings:
                self.status_var.set(f"⚠ {'; '.join(warnings)}")
                print(f"快捷键警告: {'; '.join(warnings)}")
            else:
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
            
            for char in text:
                if not self.is_typing:
                    break
                    
                keyboard.write(char)
                
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
            color1 = (37, 99, 235)
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
