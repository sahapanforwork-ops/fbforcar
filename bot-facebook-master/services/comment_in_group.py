from services.excel import read_comment_in_group_sheet, cell_text, cell_int, pick_variant
from utils.commands.comment_feed import comment_on_feed

import time


def start_comment_in_group(driver, sort):
    """sort=True เรียงโพสต์ล่าสุดก่อน (เมนู 2.1), sort=False ใช้ลำดับปกติของกลุ่ม (เมนู 2.2)"""
    print("comment in group...")
    try:
        df_comment_in_group = read_comment_in_group_sheet()
    except Exception as e:
        print(f"Error occurred: {e}")
        return

    for _, row in df_comment_in_group.iterrows():
        link = cell_text(row['ลิงค์กลุ่ม']).rstrip('/')
        if not link:
            continue
        try:
            comment = pick_variant(cell_text(row['คอมเมนต์']))
            image = row['รูปภาพ']
            min_comment = cell_int(row['จำนวนคอมเมนต์'])
            count = cell_int(row['จำนวนครั้ง'])
            time.sleep(5)
            if sort:
                driver.get(f"{link}/?sorting_setting=CHRONOLOGICAL")
            else:
                driver.get(link)  # ใส่ Group ID
            comment_on_feed(driver, comment, image, min_comment, count)
        except Exception as e:
            print(f"Error occurred ({link}): {e}")
