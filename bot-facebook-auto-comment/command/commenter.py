from selenium import webdriver # type: ignore
from selenium.webdriver.common.by import By # type: ignore
from selenium.webdriver.common.keys import Keys # type: ignore
from selenium.webdriver.common.action_chains import ActionChains # type: ignore
from selenium.webdriver.support.ui import WebDriverWait # type: ignore
from selenium.webdriver.support import expected_conditions as EC # type: ignore
from selenium.webdriver.chrome.options import Options # type: ignore

import pandas as pd # type: ignore
import math
import random
import re
import time
import os
from command.facebook_login import ensure_logged_in, is_logged_in
from utils.local_store import data_dir

CONFIG_FILE = "config.xlsx"
# เก็บ cookies ในเครื่องนี้เท่านั้น (%LOCALAPPDATA%\bot-facebook-auto-comment) แบบเข้ารหัส ไม่อยู่ในโฟลเดอร์ OneDrive
COOKIES_FILE = os.path.join(data_dir("bot-facebook-auto-comment"), "cookies.dat")
# เว้นระยะระหว่างแต่ละแถว (วินาที สุ่มในช่วงนี้) คอมเมนต์/โพสต์ติด ๆ กัน Facebook จะมองว่าเป็นสแปม
WAIT_BETWEEN_ITEMS_SECONDS = (90, 180)
# ลิงก์โพสต์ที่เคยคอมเมนต์แล้ว (1 บรรทัด 1 ลิงก์) กันคอมเมนต์ซ้ำโพสต์เดิม
HISTORY_FILE = "commented_history.txt"
# โฟลเดอร์โปรแกรม ใช้หารูปที่ใส่แค่ชื่อไฟล์ เช่น images\imp_post_1x1.jpg
PROGRAM_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# หน้า Facebook มีช่องอัปโหลดไฟล์หลายช่อง (ช่องแรกของหน้ามักเป็นของกล่องโพสต์กลุ่ม หรือรับแค่วิดีโอ)
# จึงใช้ช่องที่อยู่ใกล้ช่องพิมพ์ที่สุด: เดินขึ้นจากช่องพิมพ์ทีละชั้น ช่องแรกที่เจอคือช่องรูปของกล่องนั้นเอง
NEAREST_FILE_INPUT_JS = """
let el = arguments[0] || document.activeElement;
for (let i = 0; el && i < 15; i++, el = el.parentElement) {
  const input = el.querySelector && el.querySelector('input[type=file]');
  if (input) return input;
}
return null;
"""
COMPOSER_PLACEHOLDER = '//div[@role="button"]//span[contains(text(), "เขียนอะไรสักหน่อย....")]'
DIALOG_TEXTBOX = '//div[@role="dialog"]//div[@role="textbox" and @contenteditable="true"]'
POST_BUTTON = '//div[@role="dialog"]//div[@role="button" and @aria-label="โพสต์"]'


def _url_key(url):
    """ลิงก์เดียวกันแต่ต่างโดเมน (www/web/m) หรือมี / ท้าย ให้ถือเป็นโพสต์เดียวกัน"""
    url = cell_text(url).split("?")[0].rstrip("/")
    return re.sub(r"^https?://(www\.|web\.|m\.)?facebook\.com", "facebook.com", url)


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, encoding="utf-8") as f:
        return {_url_key(line) for line in f if line.strip()}


def add_history(url):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(cell_text(url) + "\n")


def cell_text(value):
    """แปลงค่าช่องใน Excel เป็นข้อความ ช่องว่างได้ ''"""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value).strip()


def pick_variant(text):
    """ช่อง comment ใส่ได้หลายแบบ คั่นแต่ละแบบด้วยบรรทัดที่มีแค่ ---  โปรแกรมจะสุ่มใช้ 1 แบบทุกครั้ง"""
    parts = [p.strip() for p in re.split(r"(?m)^\s*-{3,}\s*$", text or "") if p.strip()]
    return random.choice(parts) if parts else (text or "")


def resolve_images(value, log_queue):
    """แปลงช่อง image เป็น path เต็มของไฟล์ที่มีอยู่จริง

    - หลายรูปในโพสต์เดียว คั่นด้วย ,  (คอมเมนต์ใช้แค่รูปแรก)
    - หลายชุดให้สุ่มใช้ทีละชุด คั่นด้วยบรรทัดที่มีแค่ ---  (เหมือนช่อง comment)
    - ใส่ได้ทั้ง path เต็ม หรือ path ในโฟลเดอร์โปรแกรม (images\a.png) ช่องว่างหรือ '-' = ไม่ใช้รูป
    """
    paths = []
    for part in pick_variant(cell_text(value)).split(","):
        part = part.strip().strip('"')
        if not part or part == "-":
            continue
        part = os.path.expanduser(part)
        found = next((p for p in (os.path.abspath(part), os.path.join(PROGRAM_DIR, part)) if os.path.isfile(p)), None)
        if found:
            paths.append(os.path.abspath(found))
        else:
            log_queue.put(f"ไม่พบไฟล์รูป: {part} (ข้ามรูปนี้)")
    return paths


def attach_images(driver, paths, near, log_queue, wait=10):
    """ใส่รูปลงช่องอัปโหลดของกล่องที่ near (ช่องพิมพ์) อยู่ ช่องที่รับรูปเดียวจะใส่แค่รูปแรก คืนค่า True ถ้าส่งไฟล์แล้ว"""
    file_input = driver.execute_script(NEAREST_FILE_INPUT_JS, near)
    if file_input is None:
        log_queue.put("ไม่พบช่องอัปโหลดรูปของกล่องนี้ ส่งแค่ข้อความ")
        return False
    if len(paths) > 1 and not file_input.get_attribute("multiple"):
        paths = paths[:1]
    file_input.send_keys("\n".join(paths))
    time.sleep(wait)
    log_queue.put(f"upload image {len(paths)} รูป: {', '.join(os.path.basename(p) for p in paths)}")
    return True


def count_previews(driver, textbox):
    """จำนวนรูปที่ขึ้นแล้วในหน้าต่างโพสต์ที่มีช่องพิมพ์นี้"""
    return driver.execute_script(
        "const d = arguments[0] && arguments[0].closest('[role=dialog]');"
        "return d ? [...d.querySelectorAll('img')].filter(i => i.src.startsWith('blob:')).length : 0;", textbox) or 0


def load_config(log_queue):
    if not os.path.exists(CONFIG_FILE):
        log_queue.put(f"ไม่พบไฟล์ {CONFIG_FILE} ในโฟลเดอร์ {os.getcwd()}")
        return None
    df = pd.read_excel(CONFIG_FILE, sheet_name="Sheet1", engine="openpyxl")
    df.columns = [str(c).strip().lower() for c in df.columns]
    missing = [c for c in ("action", "comment", "url", "image") if c not in df.columns]
    if missing:
        log_queue.put(f"{CONFIG_FILE} ไม่มีคอลัมน์: {', '.join(missing)}")
        return None
    rows = df.dropna(how="all").to_dict(orient="records")
    return [row for row in rows if cell_text(row["url"])]


def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--disable-notifications")  # ปิดการแจ้งเตือน
    # chrome_options.add_argument('--headless')  # ใช้ headless mode หากต้องการ
    # Selenium จะหา/ดาวน์โหลด ChromeDriver ที่ตรงกับ Chrome ในเครื่องให้เอง
    # ปิดการส่งสถิติการใช้งานของ Selenium Manager ไปที่ plausible.io
    os.environ["SE_AVOID_STATS"] = "true"
    return webdriver.Chrome(options=chrome_options)


def run_item(driver, item, log_queue, dry_run=False):
    """ทำ 1 แถว คืนค่า False ถ้าข้าม (ไม่ได้เปิดหน้าเว็บ) เพื่อไม่ต้องรอเว้นระยะ
    dry_run=True ทำทุกอย่างยกเว้นกดส่งคอมเมนต์/กด 'โพสต์' (ไว้ทดสอบ)"""
    url = cell_text(item["url"])
    comment = pick_variant(cell_text(item["comment"]))
    action = cell_text(item["action"]).lower()

    if action == "comment" and _url_key(url) in load_history():
        log_queue.put(f"ข้าม: เคยคอมเมนต์โพสต์นี้แล้ว ({url})")
        return False
    images = resolve_images(item["image"], log_queue)

    driver.get(url)
    log_queue.put(f"Go to url {url}")
    time.sleep(3)
    if not is_logged_in(driver):
        log_queue.put("หลุดจากระบบ ต้องล็อกอินใหม่")
        if not ensure_logged_in(driver, COOKIES_FILE, log_queue):
            raise RuntimeError("ล็อกอินไม่สำเร็จ")
        driver.get(url)
        time.sleep(3)

    if action == "comment":
        # รอให้ comment box โหลด
        comment_box = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//*[contains(@aria-label,"แสดงความคิดเห็นในชื่อ")]'))
        )
        comment_box.click()

        if images:
            attach_images(driver, images[:1], comment_box, log_queue)  # คอมเมนต์ใส่ได้ 1 รูป

        # ใช้ ActionChains เพื่อพิมพ์ข้อความและส่ง
        actions = ActionChains(driver)
        if dry_run:
            actions.move_to_element(comment_box).click().send_keys(comment).perform()
            log_queue.put(f"ทดลอง: พิมพ์คอมเมนต์แล้วแต่ไม่ส่ง ({url})")
            return True
        actions.move_to_element(comment_box).click().send_keys(comment, Keys.RETURN).perform()
        add_history(url)
        log_queue.put(f'Comment added: {comment}')

    elif action == "post":
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, COMPOSER_PLACEHOLDER))).click()
        time.sleep(5)
        textbox = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, DIALOG_TEXTBOX)))
        # ใส่รูปก่อนพิมพ์ ลิงก์ในข้อความจะได้ไม่ขึ้นเป็นกล่องตัวอย่างเว็บแทนรูป
        if images:
            if attach_images(driver, images, textbox, log_queue, wait=3):
                end = time.time() + 40
                while count_previews(driver, textbox) < len(images) and time.time() < end:
                    time.sleep(1)
                shown = count_previews(driver, textbox)
                if shown < len(images):
                    log_queue.put(f"รูปขึ้น {shown}/{len(images)} รูป")
                time.sleep(3)
            textbox = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, DIALOG_TEXTBOX)))
            textbox.click()
            time.sleep(1)

        textbox.send_keys(comment)
        time.sleep(2)
        post_button = WebDriverWait(driver, 30).until(
            lambda d: next((b for b in d.find_elements(By.XPATH, POST_BUTTON)
                            if b.is_displayed() and b.get_attribute("aria-disabled") != "true"), False)
        )
        if dry_run:
            log_queue.put(f"ทดลอง: พร้อมโพสต์แล้วแต่ไม่กด ({url})")
            return True
        post_button.click()
        log_queue.put(f'Post added: {comment}')

    else:
        log_queue.put(f"ไม่รู้จัก action '{action}' (ใช้ได้แค่ comment หรือ post) ข้ามแถวนี้")


def start_commenting(interval, log_queue):
    """interval = เวลารอก่อนทำรอบถัดไป (วินาที) ถ้าเป็น 0 จะทำรอบเดียวแล้วหยุด"""
    try:
        config = load_config(log_queue)
    except Exception as e:
        log_queue.put(f"Error loading config: {e}")
        return
    if not config:
        log_queue.put("ไม่มีรายการให้ทำใน config.xlsx")
        return

    try:
        driver = create_driver()
    except Exception as e:
        log_queue.put(f"เปิด Chrome ไม่สำเร็จ: {e}")
        return

    try:
        if not ensure_logged_in(driver, COOKIES_FILE, log_queue):
            return

        round_number = 1
        while True:
            log_queue.put(f"เริ่มรอบที่ {round_number}")
            for number, item in enumerate(config, 1):
                acted = True
                try:
                    acted = run_item(driver, item, log_queue) is not False
                except Exception as e:
                    log_queue.put(f"ทำรายการไม่สำเร็จ ({cell_text(item['url'])}): {type(e).__name__} {e}")
                if acted and number < len(config):
                    gap = random.uniform(*WAIT_BETWEEN_ITEMS_SECONDS)
                    log_queue.put(f"รอ {gap / 60:.1f} นาที ก่อนทำรายการถัดไป ({number + 1}/{len(config)})")
                    time.sleep(gap)

            if interval <= 0:
                log_queue.put("ทำงานครบแล้ว (ไม่ได้ตั้งเวลาทำซ้ำ)")
                break

            # รอช่วงเวลาที่กำหนดก่อนคอมเมนต์ต่อ
            log_queue.put(f"Wait Next: รอ {interval} วินาที")
            time.sleep(interval)
            round_number += 1

    except Exception as e:
        log_queue.put(f"An error occurred: {e}")

    finally:
        driver.quit()
