import keyboard
import time

print("测试修复后的键盘输入...")

# 测试用例
test_cases = [
    "chatgptnb666..",
    "Hello World!",
    "1234567890",
    "测试中文输入"
]

for i, test_text in enumerate(test_cases):
    print(f"\n测试 {i+1}: {test_text}")
    print("3秒后开始输入...")
    time.sleep(3)

    print("开始输入...")
    # 使用修复后的方式
    for char in test_text:
        keyboard.press(char)
        keyboard.release(char)
        time.sleep(0.1)  # 给点延迟
    print("输入完成!")
    time.sleep(1)

print("\n所有测试完成!")
