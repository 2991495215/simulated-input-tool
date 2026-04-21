# 模拟输入工具

一个 Windows 桌面小工具：从剪贴板读取文本，并按设定速度逐字符模拟键盘输入。

适合把一段已经复制好的文本输入到网页、聊天框、表单、远程窗口或不方便直接粘贴的输入环境中。

## 功能

- 从剪贴板读取文本
- 逐字符模拟键盘输入
- 支持随机延迟和固定延迟
- 支持开始/停止全局快捷键
- 支持关闭窗口后隐藏到系统托盘
- 配置自动保存到 `config.json`
- 可使用 PyInstaller 打包为单文件 exe

## 默认快捷键

| 操作 | 快捷键 |
| --- | --- |
| 开始输入 | `Alt + V` |
| 停止输入 | `Ctrl + A` |

如果快捷键和其他软件冲突，可以在界面里点击“设置”，按下新的组合键后自动保存。

## 使用方法

1. 复制要输入的文本。
2. 打开模拟输入工具。
3. 把光标放到目标输入框。
4. 按 `Alt + V` 开始输入。
5. 需要中断时按 `Ctrl + A`，或点击“停止输入”。

## 速度设置

工具提供两种输入速度：

| 模式 | 说明 |
| --- | --- |
| 随机速度 | 每个字符之间使用 `min_speed` 到 `max_speed` 之间的随机延迟 |
| 固定速度 | 每个字符之间使用相同的 `fixed_speed` 延迟 |

延迟单位都是毫秒。数值越小，输入越快。

## 配置文件

程序会在运行目录读取或生成 `config.json`。

```json
{
  "min_speed": 50,
  "max_speed": 150,
  "hotkey": "alt+v",
  "stop_hotkey": "ctrl+a",
  "use_random_speed": true,
  "fixed_speed": 100,
  "hide_to_tray": true,
  "asked_hide_to_tray": true
}
```

| 字段 | 说明 |
| --- | --- |
| `min_speed` | 随机模式的最小延迟 |
| `max_speed` | 随机模式的最大延迟 |
| `hotkey` | 开始输入快捷键 |
| `stop_hotkey` | 停止输入快捷键 |
| `use_random_speed` | 是否启用随机速度 |
| `fixed_speed` | 固定模式的延迟 |
| `hide_to_tray` | 关闭窗口时是否隐藏到托盘 |
| `asked_hide_to_tray` | 兼容旧配置的标记字段 |

## 从源码运行

```bash
pip install -r requirements.txt
python main.py
```

依赖：

- `keyboard`
- `pyperclip`
- `pystray`
- `Pillow`

## 打包

项目内已有多个 PyInstaller `.spec` 文件，也可以直接执行：

```bash
pyinstaller --onefile --noconsole --name "simulated-input-tool" main.py
```

生成的 exe 位于 `dist/` 目录。

## 权限说明

`keyboard` 库监听全局快捷键时通常需要管理员权限。建议运行 exe 或源码时使用“以管理员身份运行”。

如果没有管理员权限，程序会尝试自动提权；提权失败时会显示提示并退出。

## 注意事项

- 输入逻辑是逐字符发送，不是一次性粘贴。
- 快捷键尽量避开系统或常用软件快捷键。
- `Ctrl + A` 默认用于停止输入，可能会和“全选”冲突，可以在界面中改成其他组合键。
- 打包产物较大是正常现象，因为 PyInstaller 会把 Python 运行环境和依赖一并打进 exe。
