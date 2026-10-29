import keyboard
import time

print("测试 keyboard 库的 write 函数...")

test_text = "chatgptnb666.."
print(f"要输入的文本: {test_text}")
print("\n3秒后开始输入...")
time.sleep(3)

print("开始输入...")
keyboard.write(test_text)
print("输入完成!")
