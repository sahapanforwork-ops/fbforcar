import queue
import threading
import time

# ฟังก์ชันเพิ่มข้อความลง log queue
def log_worker(log_queue, update_log_callback):
    """ฟังก์ชันนี้ทำงานใน background thread เพื่อรับข้อความจาก queue และแสดงใน UI"""
    while True:
        try:
            message = log_queue.get()  # รอรับข้อความจาก queue
            if message == "QUIT":
                break
            update_log_callback(message)
        except queue.Empty:
            time.sleep(0.1)

# ฟังก์ชันจำลองการทำงาน
def simulate_task(total_seconds,log_queue):
    """จำลองการทำงาน โดยจะส่งข้อความไปยัง log_queue ทุกครั้ง"""
    log_queue.put("เริ่มทำงาน...")

    for i in range(total_seconds):
        log_queue.put(f"กำลังทำงาน {i+1}/{total_seconds}...")
        time.sleep(1)

    log_queue.put("การทำงานเสร็จสมบูรณ์!")
