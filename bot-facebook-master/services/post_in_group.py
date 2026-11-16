from selenium.webdriver.common.by import By # type: ignore
from selenium.webdriver.support import expected_conditions as EC # type: ignore
from selenium.webdriver.support.ui import WebDriverWait # type: ignore

from services.excel import read_post_in_group_sheet, cell_text, pick_variant
from utils.commands.image import resolve_images

import random
import time

# เว้นระยะระหว่างกลุ่ม (วินาที สุ่มในช่วงนี้) โพสต์ข้อความเดียวกันหลายกลุ่มติด ๆ กัน Facebook จะมองว่าเป็นสแปม
POST_GAP_SECONDS = (90, 180)


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
            comment = pick_variant(cell_text(row['คอมเมนต์']))
            # ใส่หลายรูปได้โดยคั่นด้วยเครื่องหมาย ,
            image_files = resolve_images(row['รูปภาพ'])
            time.sleep(5)
            driver.get(link)
            if image_files:
                file_input = driver.find_element(By.XPATH, '//input[@type="file"]')
                file_input.send_keys("\n".join(image_files))
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
            print(f"✅ โพสต์แล้ว: {link}")
        except Exception as e:
            print(f"Error occurred ({link}): {e}")
