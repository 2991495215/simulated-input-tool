# 模拟输入工具

一个简单易用的模拟键盘输入工具，可以从剪贴板读取文本并模拟键盘输入，支持自定义速度和全局快捷键。

## ✨ 功能特性

- 📝 从剪贴板读取文本并模拟键盘输入
- ⚡ 支持随机速度和固定速度两种模式
- ⌨️ 全局快捷键控制（开始/停止输入）
- 📥 系统托盘支持，最小化到托盘继续运行
- 🎨 简洁美观的现代化界面
- 🔧 支持自定义配置

## 🚀 快速开始

### 使用 exe 文件（推荐）

1. 下载最新的 `模拟输入工具.exe`
2. **右键点击** → **「以管理员身份运行」**（需要管理员权限监听全局键盘事件）
3. 在 UAC 提示框中点击「是」

### 从源码运行

```bash
# 克隆仓库
git clone <repo-url>
cd "模拟输入工具"

# 安装依赖
pip install -r requirements.txt

# 运行程序
python main.py
```

## ⌨️ 快捷键说明

| 功能 | 快捷键 |
|------|--------|
| 开始输入 | Alt+V |
| 停止输入 | Alt+B |

### 自定义快捷键

1. 点击「设置」按钮
2. 按下想要的新快捷键组合
3. 快捷键会自动保存

## ⚙️ 配置说明

配置文件 `config.json` 包含以下设置：

```json
{
  "min_speed": 50,
  "max_speed": 150,
  "hotkey": "alt+v",
  "stop_hotkey": "alt+b",
  "use_random_speed": true,
  "fixed_speed": 100,
  "hide_to_tray": true
}
```

| 参数 | 说明 |
|------|------|
| `min_speed` | 最小延迟（毫秒，随机模式） |
| `max_speed` | 最大延迟（毫秒，随机模式） |
| `hotkey` | 开始输入快捷键 |
| `stop_hotkey` | 停止输入快捷键 |
| `use_random_speed` | 是否使用随机速度 |
| `fixed_speed` | 固定延迟（毫秒，固定模式） |
| `hide_to_tray` | 是否隐藏到系统托盘 |

## 📦 打包成 exe

```bash
# 安装 PyInstaller
pip install pyinstaller

# 打包
pyinstaller --onefile --noconsole --name "模拟输入工具" main.py
```

打包后的 exe 文件位于 `dist/` 目录。

## 🔧 技术栈

- **GUI**: Tkinter
- **全局快捷键**: keyboard
- **剪贴板**: pyperclip
- **系统托盘**: pystray
- **打包**: PyInstaller

## 📝 使用说明

1. 复制你想要输入的文本（Ctrl+C）
2. 将光标放在目标输入框中
3. 按下 **Alt+V** 开始输入
4. 按下 **Alt+B** 停止输入

## ⚠️ 注意事项

- 程序需要**管理员权限**才能监听全局键盘事件
- 首次运行时，Windows 可能会弹出 UAC 提示，请点击「是」
- 快捷键可能会与其他程序冲突，建议使用自定义快捷键

## 📄 许可证

MIT License
