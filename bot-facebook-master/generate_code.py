from utils.commands.hardware import generate_code


code = input("กรุณากรอก Hardware ID: ")
print(f"Code ที่ได้คือ: {generate_code(code)}")