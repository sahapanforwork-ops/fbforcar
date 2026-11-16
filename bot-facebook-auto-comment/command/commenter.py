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
    """แปลงช่อง image (คั่นหลายรูปด้วย ,) เป็น path เต็มของไฟล์ที่มีอยู่จริง

    ใส่ได้ทั้ง path เต็ม หรือชื่อไฟล์ในโฟลเดอร์โปรแกรม ช่องว่างหรือ '-' = ไม่ใช้รูป
    """
    paths = []
    for part in cell_text(value).split(","):
        part = part.strip().strip('"')
        if not part or part == "-":
            continue
        full_path = os.path.abspath(os.path.expanduser(part))
        if os.path.isfile(full_path):
            paths.append(full_path)
        else:
            log_queue.put(f"ไม่พบไฟล์รูป: {part} (ข้ามรูปนี้)")
    return paths


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


def run_item(driver, item, log_queue):
    """ทำ 1 แถว คืนค่า False ถ้าข้าม (ไม่ได้เปิดหน้าเว็บ) เพื่อไม่ต้องรอเว้นระยะ"""
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
            file_input = driver.find_element(By.XPATH, '//input[@type="file"]')
            file_input.send_keys(images[0])  # คอมเมนต์ใส่ได้ 1 รูป
            time.sleep(10)
            log_queue.put(f"upload image {images[0]}")

        # ใช้ ActionChains เพื่อพิมพ์ข้อความและส่ง
        actions = ActionChains(driver)
        actions.move_to_element(comment_box).click().send_keys(comment, Keys.RETURN).perform()
        add_history(url)
        log_queue.put(f'Comment added: {comment}')

    elif action == "post":
        if images:
            file_input = driver.find_element(By.XPATH, '//input[@type="file"]')
            file_input.send_keys("\n".join(images))
            log_queue.put(f"upload image {len(images)} รูป")
            time.sleep(10)
        else:
            post_box = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//div[@role="button"]//span[contains(text(), "เขียนอะไรสักหน่อย....")]'))
            )
            post_box.click()
            time.sleep(5)

        element = driver.switch_to.active_element
        element.send_keys(comment)
        post_button = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//div[@role="button" and @aria-label="โพสต์"]'))
        )
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
