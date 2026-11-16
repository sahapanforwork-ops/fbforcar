from selenium.webdriver.common.by import By # type: ignore
from selenium.webdriver.common.keys import Keys # type: ignore
from selenium.webdriver.common.action_chains import ActionChains # type: ignore

from utils.commands.scroll import scroll
from utils.commands.is_displayed import is_displayed
from utils.commands.like import random_like
from utils.commands.image import upload_image

import time
import re

# ปุ่ม "xx ความคิดเห็น" ใต้โพสต์ (class ของ Facebook เปลี่ยนบ่อย ถ้าหาโพสต์ไม่เจอเลยให้อัปเดตตรงนี้)
COMMENT_COUNT_SELECTOR = '.html-span.xdj266r.x11i5rnm.xat24cr.x1mh8g0r.xexx8yu.x4uap5.x18d9i69.xkhd6sd.x1hl2dhg.x16tdsg8.x1vvkbs.x1sur9pj.xkrqix3'

# เลื่อนจอติดกันกี่ครั้งโดยไม่เจอโพสต์ที่เข้าเงื่อนไข แล้วให้เลิกหา (กันวนไม่รู้จบ)
MAX_SCROLLS_WITHOUT_MATCH = 30


def comment_on_feed(driver, comment, image, min_comment, count):
    """เลื่อนฟีดหน้าปัจจุบัน แล้วคอมเมนต์โพสต์ที่มีคอมเมนต์อย่างน้อย min_comment จนครบ count โพสต์"""
    commented = 0
    scrolls_without_match = 0
    done_buttons = set()

    while commented < count and scrolls_without_match < MAX_SCROLLS_WITHOUT_MATCH:
        comment_buttons = driver.find_elements(By.CSS_SELECTOR, COMMENT_COUNT_SELECTOR)
        scroll(driver)
        time.sleep(1)

        matched = False
        for button in comment_buttons:
            try:
                if button.id in done_buttons or not is_displayed(driver, button):
                    continue
                random_like(driver)
                text = button.text
                number_match = re.search(r'\d+', text)
                if not number_match or "แชร์" in text or int(number_match.group()) < min_comment:
                    continue

                done_buttons.add(button.id)
                time.sleep(1)
                button.click()
                time.sleep(5)
                upload_image(driver, image)

                # ส่งข้อความคอมเมนต์
                actions = ActionChains(driver)
                actions.send_keys(comment).perform()
                time.sleep(3)  # หน่วงเวลา 3 วินาที

                # ส่ง RETURN (Enter) และ ESCAPE เพื่อปิดช่องคอมเมนต์
                actions.send_keys(Keys.RETURN).send_keys(Keys.ESCAPE).perform()
                time.sleep(1)
                commented += 1
                print(f"✅ คอมเมนต์แล้ว {commented}/{count}")
                matched = True
                break
            except Exception as e:
                # ปุ่มหายไปจากหน้า (Facebook โหลดฟีดใหม่) หรือคลิกไม่ได้ ข้ามไปปุ่มถัดไป
                print(f"ข้ามโพสต์นี้: {type(e).__name__}")
                continue

        scrolls_without_match = 0 if matched else scrolls_without_match + 1

    if commented < count:
        print(f"⚠️ หาโพสต์ที่เข้าเงื่อนไขได้ {commented}/{count} โพสต์ แล้วหยุดหา "
              f"(เลื่อนจอ {MAX_SCROLLS_WITHOUT_MATCH} ครั้งไม่เจอโพสต์ใหม่)")
    return commented
