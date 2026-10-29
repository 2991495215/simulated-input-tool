# 模拟输入工具

Windows 模拟输入工具：读取剪贴板文本，按随机或固定速度逐字符输入，支持自定义全局快捷键、系统托盘与单实例运行。

**[下载最新版 EXE](https://github.com/2991495215/simulated-input-tool/releases/latest/download/simulated-input-tool.exe)** · [查看版本说明](https://github.com/2991495215/simulated-input-tool/releases/latest)

单文件 EXE，免安装，无需安装 Python，也无需附带 `_internal` 文件夹。首次运行会在 EXE 旁生成 `config.json`，用于保存个人设置。

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
- 单文件 EXE，下载后直接运行

## 下载与首次运行

1. 点击上方“下载最新版 EXE”，保存 `simulated-input-tool.exe`。
2. 放到自己有写入权限的固定文件夹，方便保存设置和后续更新。
3. 双击运行，在 Windows 权限提示中允许管理员权限；取消授权则程序退出。
4. 首次启动需要解包内置依赖，可能稍慢。

### 从旧版升级

1. 先在系统托盘中退出旧程序；关闭窗口默认只是隐藏到托盘。
2. 用新 EXE 替换旧 EXE。若换了文件夹，把原来的 `config.json` 一起放到新 EXE 旁。
3. 运行新 EXE；使用桌面快捷方式时，确认它指向新 EXE。

旧设置会继续使用，包括自定义快捷键。下方默认快捷键仅适用于没有已有配置的情况。

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
| 随机速度 | 每个字符之间，在界面设置的“最小延迟”和“最大延迟”范围内随机等待 |
| 固定速度 | 每个字符之间使用相同的固定延迟 |

延迟单位都是毫秒。数值越小，输入越快。

## 配置文件

设置可直接在界面修改并自动保存，一般无需手动编辑配置。EXE 运行时，`config.json` 位于 EXE 所在文件夹；从源码运行时，位于 `main.py` 所在文件夹，与启动命令的当前目录无关。

首次运行的默认配置：

```json
{
  "min_speed": 50,
  "max_speed": 150,
  "hotkey": "ctrl+alt+v",
  "stop_hotkey": "ctrl+a",
  "use_random_speed": true,
  "fixed_speed": 100,
  "hide_to_tray": true,
  "asked_hide_to_tray": false
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

默认使用 `simulated-input-tool.spec`，采用 PyInstaller `onefile` 打包，并排除无关的科学计算库、非 Windows 托盘后端和部分 Pillow 组件：

```bash
pyinstaller --clean --noconfirm --distpath release --workpath tmp/build simulated-input-tool.spec
```

生成的单文件产物为 `release/simulated-input-tool.exe`，下载后直接运行，无需附带 `_internal` 文件夹。首次使用会在 EXE 同目录生成 `config.json`。

## 目录说明

| 位置 | 用途 |
| --- | --- |
| `main.py` | 源码入口 |
| `requirements.txt` | Python 依赖 |
| `simulated-input-tool.spec` | 当前打包配置 |
| `config.json` | 源码运行时的个人设置 |
| `release/simulated-input-tool.exe` | 单文件程序，日常运行使用此处 |
| `tests/test_app.py` | 界面布局、单实例与单文件提权环境的自动测试 |
| `tests/manual/` | 手动键盘测试，会向当前窗口发送字符 |
| `archive/` | 旧版程序、旧打包配置与历史构建文件，仅作历史留存 |
| `tmp/` | 构建临时文件与界面预览 |

个人配置、构建产物和历史归档以本地目录为准，不一定包含在源码下载中。

## 验证

```bash
python -B -m unittest discover -s tests -p test_app.py -v
```

自动测试不发送键盘输入。`tests/manual/` 中的脚本仅在准备好目标输入窗口后手动运行。

## 权限说明

Windows 下，程序启动时会检查管理员权限；没有权限时会自动请求提权，取消或提权失败则退出。EXE 和源码运行均采用此流程。

## 注意事项

- 输入逻辑是逐字符发送，不是一次性粘贴。
- 快捷键尽量避开系统或常用软件快捷键。
- `Ctrl + A` 默认用于停止输入，可能会和“全选”冲突，可以在界面中改成其他组合键。
- 单文件版启动时会先解包依赖，因此可能比文件夹版启动慢。
