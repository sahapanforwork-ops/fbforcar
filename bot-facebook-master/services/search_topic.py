from selenium.webdriver.common.by import By # type: ignore
from selenium.webdriver.support.ui import WebDriverWait # type: ignore
from selenium.webdriver.support import expected_conditions as EC # type: ignore

from utils.commands.search_topic import search_topic
from utils.commands.comment_feed import comment_on_feed
from services.excel import read_search_and_comment_sheet, cell_text, cell_int, pick_variant
import time


def start_search_topic(driver, checkbox):
    """checkbox=True ติ๊ก 'โพสต์ล่าสุด' ในผลค้นหา (เมนู 1.1), False ไม่ติ๊ก (เมนู 1.2)"""
    print("search topic...")
    try:
        df_search_and_comment = read_search_and_comment_sheet()
    except Exception as e:
        print(f"Error occurred: {e}")
        return

    for _, row in df_search_and_comment.iterrows():
        topic = cell_text(row['หัวข้อ'])
        if not topic:
            continue
        try:
            comment = pick_variant(cell_text(row['คอมเมนต์']))
            image = row['รูปภาพ']
            min_comment = cell_int(row['จำนวนคอมเมนต์'])
            count = cell_int(row['จำนวนครั้ง'])

            search_topic(driver, topic)
            if checkbox:
                checkbox_button = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.XPATH, '//input[@aria-label="โพสต์ล่าสุด"]'))
                )
                checkbox_button.click()
                time.sleep(5)
            comment_on_feed(driver, comment, image, min_comment, count)
        except Exception as e:
            print(f"Error occurred ({topic}): {e}")
