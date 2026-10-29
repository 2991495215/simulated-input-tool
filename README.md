# 模拟输入工具

轻量 Windows 模拟输入工具：读取剪贴板文本，按随机或固定速度逐字符输入，支持自定义全局快捷键、系统托盘与单实例运行。

适合把一段已经复制好的文本输入到网页、聊天框、表单、远程窗口或不方便直接粘贴的输入环境中。

## 功能

- 从剪贴板读取文本
- 逐字符模拟键盘输入
- 支持随机延迟和固定延迟
- 支持开始/停止全局快捷键
- 支持关闭窗口后隐藏到系统托盘
- 配置自动保存到 `config.json`
- 单实例运行，再次打开时恢复已有窗口
- 窗口按字体和显示缩放自动计算尺寸
- 使用 PyInstaller 打包为 `onedir` 文件夹

## 默认快捷键

| 操作 | 快捷键 |
| --- | --- |
| 开始输入 | `Ctrl + Alt + V` |
| 停止输入 | `Ctrl + A` |

如果快捷键和其他软件冲突，可以在界面里点击“设置”，按下新的组合键后自动保存。

## 使用方法

1. 复制要输入的文本。
2. 打开模拟输入工具。
3. 把光标放到目标输入框。
4. 按 `Ctrl + Alt + V` 开始输入。
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
  "hotkey": "ctrl+alt+v",
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

以下命令均在项目根目录执行。

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

默认使用 `simulated-input-tool.spec`，避免把无关的 `numpy`、跨平台托盘后端和 Pillow 图像组件打进 EXE：

```bash
pyinstaller --clean --noconfirm --distpath release --workpath tmp/build simulated-input-tool.spec
```

生成的 `onedir` 产物位于 `release/simulated-input-tool/` 目录，发布时需要完整保留该文件夹。程序入口为其中的 `simulated-input-tool.exe`。

## 目录说明

| 位置 | 用途 |
| --- | --- |
| `main.py` | 源码入口 |
| `requirements.txt` | Python 依赖 |
| `simulated-input-tool.spec` | 当前打包配置 |
| `config.json` | 源码运行时的个人设置，保留原位置 |
| `release/simulated-input-tool/` | 当前可用版本，日常运行使用此处 |
| `tests/test_app.py` | 布局与单实例自动测试 |
| `tests/manual/` | 手动键盘测试，会向当前窗口发送字符 |
| `archive/` | 旧版程序、旧打包配置与历史构建文件，仅作历史留存 |
| `tmp/` | 构建临时文件与界面预览 |

打包后的程序在 EXE 所在目录保存自己的 `config.json`。整理目录不会合并或覆盖不同版本的设置。

## 验证

```bash
python -B -m unittest discover -s tests -p test_app.py -v
```

自动测试不发送键盘输入。`tests/manual/` 中的脚本仅在准备好目标输入窗口后手动运行。

## 权限说明

`keyboard` 库监听全局快捷键时通常需要管理员权限。建议运行 exe 或源码时使用“以管理员身份运行”。

如果没有管理员权限，程序会尝试自动提权；提权失败时会显示提示并退出。

## 注意事项

- 输入逻辑是逐字符发送，不是一次性粘贴。
- 快捷键尽量避开系统或常用软件快捷键。
- `Ctrl + A` 默认用于停止输入，可能会和“全选”冲突，可以在界面中改成其他组合键。
- 当前默认使用 `onedir`，启动时无需先解包，适合这个需要快速启动的小工具；发布时需要完整保留 `release/simulated-input-tool/` 文件夹。
