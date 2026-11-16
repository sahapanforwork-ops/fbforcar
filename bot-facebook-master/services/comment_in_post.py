from selenium.webdriver.common.by import By # type: ignore
from selenium.webdriver.common.keys import Keys # type: ignore
from selenium.webdriver.common.action_chains import ActionChains # type: ignore
from selenium.webdriver.support import expected_conditions as EC # type: ignore
from selenium.webdriver.support.ui import WebDriverWait # type: ignore

from services.excel import read_comment_in_post_sheet, cell_text, pick_variant
from utils.commands.image import upload_image

import time


def start_comment_in_post(driver):
    print("comment in post...")
    try:
        df_comment_in_post = read_comment_in_post_sheet()
    except Exception as e:
        print(f"Error occurred: {e}")
        return

    for _, row in df_comment_in_post.iterrows():
        link = cell_text(row['ลิงค์โพสต์'])
        if not link:
            continue
        try:
            comment = pick_variant(cell_text(row['คอมเมนต์']))
            image = row['รูปภาพ']
            time.sleep(5)
            driver.get(link)
            comment_box = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//div[@role="textbox" and @contenteditable="true"]'))
            )
            comment_box.click()
            if upload_image(driver, image, near=comment_box):
                time.sleep(5)
            # ใช้ ActionChains เพื่อพิมพ์ข้อความและส่ง
            actions = ActionChains(driver)
            actions.move_to_element(comment_box).click().send_keys(comment).perform()
            time.sleep(1)
            actions.send_keys(Keys.RETURN).perform()
            print(f"✅ คอมเมนต์แล้ว: {link}")
            time.sleep(5)
        except Exception as e:
            print(f"Error occurred ({link}): {e}")
