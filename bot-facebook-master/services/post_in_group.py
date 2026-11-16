from selenium.webdriver.common.by import By # type: ignore
from selenium.webdriver.support import expected_conditions as EC # type: ignore
from selenium.webdriver.support.ui import WebDriverWait # type: ignore

from services.excel import read_post_in_group_sheet, cell_text, pick_variant
from utils.commands.image import resolve_images, attach_images

import random
import time

# เว้นระยะระหว่างกลุ่ม (วินาที สุ่มในช่วงนี้) โพสต์ข้อความเดียวกันหลายกลุ่มติด ๆ กัน Facebook จะมองว่าเป็นสแปม
POST_GAP_SECONDS = (90, 180)

COMPOSER_PLACEHOLDER = '//div[@role="button"]//span[contains(text(), "เขียนอะไรสักหน่อย....")]'
DIALOG_TEXTBOX = '//div[@role="dialog"]//div[@role="textbox" and @contenteditable="true"]'
POST_BUTTON = '//div[@role="dialog"]//div[@role="button" and @aria-label="โพสต์"]'

# จำนวนรูปตัวอย่างในหน้าต่างโพสต์ที่มีช่องพิมพ์อยู่ (รูปที่ใส่แล้วจะขึ้นเป็น blob:)
PREVIEW_COUNT_JS = """
const box = arguments[0];
const dialog = box && box.closest('[role=dialog]');
return dialog ? [...dialog.querySelectorAll('img')].filter(i => i.src.startsWith('blob:')).length : 0;
"""


def wait_for_previews(driver, textbox, count, timeout=40):
    """รอจนรูปขึ้นในหน้าต่างโพสต์ครบ count รูป คืนค่าจำนวนที่ขึ้น"""
    shown = 0
    end = time.time() + timeout
    while time.time() < end:
        shown = driver.execute_script(PREVIEW_COUNT_JS, textbox) or 0
        if shown >= count:
            break
        time.sleep(1)
    return shown


def post_to_group(driver, link, text, image_files, dry_run=False):
    """โพสต์ 1 กลุ่ม: เปิดกล่องโพสต์ ใส่รูป พิมพ์ข้อความ แล้วกด 'โพสต์'
    dry_run=True ทำทุกอย่างยกเว้นกด 'โพสต์' (ไว้ทดสอบ)"""
    driver.get(link)
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, COMPOSER_PLACEHOLDER))).click()
    time.sleep(5)
    textbox = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, DIALOG_TEXTBOX)))

    # ใส่รูปก่อนพิมพ์ ลิงก์ในข้อความจะได้ไม่ขึ้นเป็นกล่องตัวอย่างเว็บแทนรูป
    if image_files:
        if attach_images(driver, image_files, near=textbox, wait=3):
            shown = wait_for_previews(driver, textbox, len(image_files))
            if shown < len(image_files):
                print(f"⚠️ รูปขึ้น {shown}/{len(image_files)} รูป")
            time.sleep(3)
        else:
            print("⚠️ ใส่รูปไม่ได้ จะโพสต์แค่ข้อความ")
        textbox = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, DIALOG_TEXTBOX)))
        textbox.click()
        time.sleep(1)

    textbox.send_keys(text)
    time.sleep(2)
    post_button = WebDriverWait(driver, 30).until(
        lambda d: next((b for b in d.find_elements(By.XPATH, POST_BUTTON)
                        if b.is_displayed() and b.get_attribute("aria-disabled") != "true"), False)
    )
    if dry_run:
        print(f"🧪 ทดลอง: พร้อมโพสต์แล้วแต่ไม่กด ({link})")
        return False
    post_button.click()
    return True


def start_post_in_group(driver):
    print("post in group...")
    try:
        df_post_in_group = read_post_in_group_sheet()
    except Exception as e:
        print(f"Error occurred: {e}")
        return

    rows = [row for _, row in df_post_in_group.iterrows() if cell_text(row['ลิงค์กลุ่ม'])]
    for index, row in enumerate(rows):
        link = cell_text(row['ลิงค์กลุ่ม'])
        if index > 0:
            gap = random.uniform(*POST_GAP_SECONDS)
            print(f"⏳ รอ {gap / 60:.1f} นาที ก่อนโพสต์กลุ่มถัดไป ({index + 1}/{len(rows)})")
            time.sleep(gap)
        try:
            text = pick_variant(cell_text(row['คอมเมนต์']))
            # หลายรูปในโพสต์เดียว คั่นด้วย ,  หลายชุดให้สุ่ม คั่นด้วยบรรทัด ---
            image_files = resolve_images(row['รูปภาพ'])
            time.sleep(5)
            if post_to_group(driver, link, text, image_files):
                print(f"✅ โพสต์แล้ว: {link}")
        except Exception as e:
            print(f"Error occurred ({link}): {e}")
