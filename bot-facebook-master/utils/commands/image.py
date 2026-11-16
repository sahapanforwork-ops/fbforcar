from services.excel import has_value, cell_text, pick_variant

import os
import time

# โฟลเดอร์โปรแกรม (bot-facebook-master) ใช้หารูปที่ใส่แค่ชื่อไฟล์ เช่น images\imp_post_4x5.jpg
PROGRAM_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# หน้า Facebook มีช่องอัปโหลดไฟล์หลายช่อง ช่องแรกของหน้ากลุ่มรับแค่วิดีโอ จึงต้องใช้ช่องที่อยู่ใกล้ช่องพิมพ์ที่สุด
# (เดินขึ้นจากช่องพิมพ์ทีละชั้น ช่องแรกที่เจอคือช่องรูปของกล่องโพสต์/คอมเมนต์นั้นเอง)
NEAREST_FILE_INPUT_JS = """
let el = arguments[0] || document.activeElement;
for (let i = 0; el && i < 15; i++, el = el.parentElement) {
  const input = el.querySelector && el.querySelector('input[type=file]');
  if (input) return input;
}
return null;
"""


def resolve_images(value, separator=","):
    """แปลงค่าช่อง 'รูปภาพ' เป็นรายการ path เต็มของไฟล์ที่มีอยู่จริง

    - ช่องว่าง หรือ '-' = ไม่ใช้รูป
    - หลายรูปในโพสต์เดียว คั่นด้วย ,  เช่น images\\a.png, images\\b.png
    - หลายชุดให้สุ่มใช้ทีละชุด คั่นด้วยบรรทัดที่มีแค่ ---  (เหมือนช่องข้อความ)
    - ใส่ได้ทั้ง path เต็ม (C:\\Users\\...\\a.png) หรือ path ในโฟลเดอร์โปรแกรม (images\\a.png)
    - ไฟล์ที่หาไม่เจอจะถูกข้ามพร้อมแจ้งเตือน
    """
    value = pick_variant(cell_text(value))
    if not has_value(value):
        return []
    parts = value.split(separator) if separator else [value]
    paths = []
    for part in parts:
        part = part.strip().strip('"')
        if not has_value(part):
            continue
        part = os.path.expanduser(part)
        candidates = [os.path.abspath(part), os.path.join(PROGRAM_DIR, part)]
        found = next((p for p in candidates if os.path.isfile(p)), None)
        if found:
            paths.append(os.path.abspath(found))
        else:
            print(f"⚠️ ไม่พบไฟล์รูป: {part} (ข้ามรูปนี้)")
    return paths


def resolve_image(value):
    """เหมือน resolve_images แต่ใช้ทั้งช่องเป็นไฟล์เดียว คืนค่า path หรือ None"""
    paths = resolve_images(value, separator=None)
    return paths[0] if paths else None


def attach_images(driver, paths, near=None, wait=10):
    """ใส่รูปลงช่องอัปโหลดของกล่องที่ near อยู่ (ช่องพิมพ์โพสต์หรือคอมเมนต์ ไม่ใส่ = ช่องที่กำลังพิมพ์อยู่)
    ช่องที่รับได้รูปเดียว (เช่นคอมเมนต์) จะใส่แค่รูปแรก คืนค่า True ถ้าส่งไฟล์แล้ว"""
    if not paths:
        return False
    try:
        file_input = driver.execute_script(NEAREST_FILE_INPUT_JS, near)
        if file_input is None:
            print("⚠️ ไม่พบช่องอัปโหลดรูปของกล่องนี้")
            return False
        if len(paths) > 1 and not file_input.get_attribute("multiple"):
            paths = paths[:1]
        file_input.send_keys("\n".join(paths))
        time.sleep(wait)
        print(f"🖼️ ใส่รูปแล้ว {len(paths)} รูป")
        return True
    except Exception as e:
        print(f"⚠️ อัปโหลดรูปไม่สำเร็จ: {e}")
        return False


def upload_image(driver, image, near=None):
    """อัปโหลดรูป 1 รูป (จากค่าช่อง 'รูปภาพ') ลงกล่องคอมเมนต์ที่ near อยู่ คืนค่า True ถ้าส่งไฟล์สำเร็จ"""
    path = resolve_image(image)
    if not path:
        return False
    return attach_images(driver, [path], near=near, wait=5)
