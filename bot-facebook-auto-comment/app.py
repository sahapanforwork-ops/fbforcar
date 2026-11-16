import tkinter as tk
import os
import sys
import queue
import threading
from utils.hardware_id_functions import copy_hardware_id
from command.commenter import start_commenting

# ให้อ่าน config.xlsx / assets/cookies.json / รูปภาพ จากโฟลเดอร์โปรแกรมเสมอ ไม่ว่าจะรันจากที่ไหน
BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

class HardwareIDApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hardware ID Viewer")
        self.root.geometry("600x400")  # ขยายขนาดหน้าต่างเล็กน้อย
        self.root.resizable(False, False)
        self.root.configure(bg="#D8E8F0")

        # สร้าง Queue สำหรับส่งข้อความ
        self.log_queue = queue.Queue()
        self.running = False

        # เรียกใช้ UI elements
        self.create_widgets()

        # ดึงข้อความจาก queue มาแสดงทุก 100ms (Tkinter ต้องอัปเดตจาก main thread เท่านั้น)
        self.root.after(100, self.poll_log)

    def create_widgets(self):
        # สร้าง Frame สำหรับจัดระเบียบ
        header_frame = tk.Frame(self.root, pady=10, bg="#D8E8F0")
        header_frame.pack(fill=tk.X, padx=10)

        # เพิ่ม TextBox สำหรับกรอก code ด้านบนสุด
        self.code_textbox_label = tk.Label(header_frame, text="กรอกรหัสที่นี่:", font=("Arial", 12), bg="#D8E8F0", fg="black")
        self.code_textbox_label.pack(side=tk.LEFT, padx=10)

        self.code_textbox = tk.Text(header_frame, height=1, width=25, font=("Arial", 12), wrap=tk.WORD, bg="#FFFFFF", fg="black", relief="flat")
        self.code_textbox.pack(side=tk.LEFT, padx=10)

        # ปุ่ม Copy Hardware ID
        self.copy_button = tk.Button(header_frame, text="Copy Hardware ID", font=("Arial", 12), command=self.copy_id, bg="#A8D8FF", fg="black", relief="flat", padx=10, pady=5, width=18, height=2, bd=0)
        self.copy_button.pack(side=tk.RIGHT, padx=10)

        # # Hardware ID Label
        # self.hardware_id_label = tk.Label(header_frame, text=f"Hardware ID: {get_hardware_id()}", font=("Arial", 12), bg="#D8E8F0", fg="black")
        # self.hardware_id_label.pack(side=tk.RIGHT, padx=10)

        # สร้าง Frame สำหรับส่วนที่เกี่ยวกับเวลา
        time_frame = tk.Frame(self.root, pady=10, bg="#D8E8F0")
        time_frame.pack(expand=True)

        # เพิ่ม Label สำหรับอธิบาย
        time_label = tk.Label(time_frame, text="ตั้งเวลาการทำงานซ้ำ (ชั่วโมง:นาที:วินาที)", font=("Arial", 12), bg="#D8E8F0", fg="black")
        time_label.pack(side=tk.TOP, pady=5)

        # Dropdown สำหรับเลือกชั่วโมง
        hour_options = [str(i) for i in range(24)]
        minute_options = [str(i) for i in range(60)]
        second_options = [str(i) for i in range(60)]

        self.hour_var = tk.StringVar(value="0")
        self.minute_var = tk.StringVar(value="0")
        self.second_var = tk.StringVar(value="0")

        hour_menu = tk.OptionMenu(time_frame, self.hour_var, *hour_options)
        minute_menu = tk.OptionMenu(time_frame, self.minute_var, *minute_options)
        second_menu = tk.OptionMenu(time_frame, self.second_var, *second_options)

        # จัดการการวางตำแหน่ง Dropdown ให้อยู่ตรงกลาง
        hour_menu.pack(side=tk.LEFT, padx=2)
        minute_menu.pack(side=tk.LEFT, padx=2)
        second_menu.pack(side=tk.LEFT, padx=2)

        # สร้าง Frame สำหรับปุ่มให้แสดงกลางจอ
        button_frame = tk.Frame(self.root, pady=10, bg="#D8E8F0")
        button_frame.pack(expand=True, pady=10)

        start_button = tk.Button(button_frame, text="เริ่มโปรแกรม", font=("Arial", 14), command=self.start_task, bg="#A8D8FF", fg="black", relief="flat", padx=15, pady=2, bd=0)
        start_button.pack()

        # ส่วนแสดง Log
        self.log_text = tk.Text(self.root, height=10, width=70, font=("Arial", 12), wrap=tk.WORD, bg="#000000", fg="#E8F4FD", relief="flat")
        self.log_text.pack(pady=5)
        self.log_text.insert(tk.END, "Log Starts Here\n")

    def copy_id(self):
        hardware_id = copy_hardware_id()
        self.log_queue.put(f"คัดลอก Hardware ID แล้ว: {hardware_id}")

    # ฟังก์ชันเริ่มโปรแกรม
    def start_task(self):
        if self.running:
            self.log_queue.put("โปรแกรมกำลังทำงานอยู่แล้ว")
            return
        self.running = True
        task_thread = threading.Thread(target=self.run_task, daemon=True)
        task_thread.start()

    def run_task(self):
        try:
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
            second = int(self.second_var.get())
            total_seconds = hour * 3600 + minute * 60 + second
            if total_seconds == 0:
                self.log_queue.put("เริ่มทำงาน (ทำรอบเดียว)")
            else:
                self.log_queue.put(f"เริ่มทำงาน (ทำซ้ำทุก {hour}:{minute:02d}:{second:02d})")
            start_commenting(total_seconds, self.log_queue)
        except Exception as e:
            self.log_queue.put(f"เกิดข้อผิดพลาด: {e}")
        finally:
            self.running = False
            self.log_queue.put("หยุดทำงานแล้ว")

    def poll_log(self):
        try:
            while True:
                self.update_log(self.log_queue.get_nowait())
        except queue.Empty:
            pass
        self.root.after(100, self.poll_log)

    def update_log(self, txt):
        self.log_text.insert('end', str(txt) + "\n")
        self.log_text.see('end')

# เรียกใช้งาน
if __name__ == "__main__":
    root = tk.Tk()
    app = HardwareIDApp(root)
    root.mainloop()
