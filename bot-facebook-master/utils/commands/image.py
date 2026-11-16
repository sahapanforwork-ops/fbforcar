from selenium.webdriver.common.by import By  # type: ignore

from services.excel import has_value, cell_text

import os
import time


def resolve_images(value, separator=","):
    """แปลงค่าช่อง 'รูปภาพ' เป็นรายการ path เต็มของไฟล์ที่มีอยู่จริง

    - ช่องว่าง หรือ '-' = ไม่ใช้รูป
    - ใส่ได้ทั้ง path เต็ม (C:\\Users\\...\\a.png) หรือชื่อไฟล์ที่อยู่ในโฟลเดอร์โปรแกรม (a.png)
    - ไฟล์ที่หาไม่เจอจะถูกข้ามพร้อมแจ้งเตือน
    """
    if not has_value(value):
        return []
    parts = cell_text(value).split(separator) if separator else [cell_text(value)]
    paths = []
    for part in parts:
        part = part.strip().strip('"')
        if not has_value(part):
            continue
        full_path = os.path.abspath(os.path.expanduser(part))
        if os.path.isfile(full_path):
            paths.append(full_path)
        else:
            print(f"⚠️ ไม่พบไฟล์รูป: {part} (ข้ามรูปนี้)")
    return paths


def resolve_image(value):
    """เหมือน resolve_images แต่ใช้ทั้งช่องเป็นไฟล์เดียว คืนค่า path หรือ None"""
    paths = resolve_images(value, separator=None)
    return paths[0] if paths else None


def upload_image(driver, image, input_index=-1):
    """อัปโหลดรูป 1 รูปลงช่อง input[type=file] คืนค่า True ถ้าส่งไฟล์สำเร็จ"""
    path = resolve_image(image)
    if not path:
        return False
    try:
        file_inputs = driver.find_elements(By.XPATH, '//input[@type="file"]')
        if not file_inputs:
            print("⚠️ ไม่พบช่องอัปโหลดรูปในหน้านี้")
            return False
        file_inputs[input_index].send_keys(path)
        time.sleep(5)
        print("Image added to the comment.")
        return True
    except Exception as e:
        print(f"⚠️ อัปโหลดรูปไม่สำเร็จ: {e}")
        return False
