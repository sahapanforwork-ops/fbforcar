from selenium.webdriver.common.by import By # type: ignore
from selenium.webdriver.common.keys import Keys # type: ignore
from selenium.webdriver.common.action_chains import ActionChains # type: ignore
from selenium.webdriver.support import expected_conditions as EC # type: ignore

from utils.commands.scroll import scroll
from utils.commands.is_displayed import is_displayed
from utils.commands.like import random_like
from services.excel import read_comment_in_group_sheet
from utils.commands.image import upload_image

import time
import re  
import hashlib
import random
seen_posts = set()

def start_comment_in_group_advance(driver,sort):
    try:
        print("คอมเมนต์ในกลุ่ม...")
        df_comment_in_group = read_comment_in_group_sheet()
        print(df_comment_in_group)
        for _, row in df_comment_in_group.iterrows():
            link = row['ลิงค์กลุ่ม']
            comment = row['คอมเมนต์']
            image = row['รูปภาพ']
            count = row['จำนวนครั้งในการหาโพสต์']
            time.sleep(5)
            if sort:
                driver.get(f"{link}/?sorting_setting=CHRONOLOGICAL")
            else:
                driver.get(link)

            
            for _ in range(int(count)):
                driver.get('')

                time.sleep(10)
                for _ in range(10):  # เลื่อน 10 ครั้ง
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(3)  # รอให้โหลดข้อมูลเพิ่ม

                keywords = ["ตามหาบ้าน", "หาบ้าน", "บ้านเช่า", "หาคอนโด", "บ้านพร้อมที่ดิน", "หาที่พัก", "หาบ้านพัก", "ตามหาบ้านพัก"]
                exclude_keywords = ["www", "http", "6000"]

                # สร้างเงื่อนไขสำหรับ keywords
                keywords_condition = " or ".join([f'contains(text(), "{kw}")' for kw in keywords])

                # สร้างเงื่อนไขสำหรับ exclude_keywords
                exclude_condition = " and ".join([f'not(contains(text(), "{kw}"))' for kw in exclude_keywords])

                # สร้าง XPath
                xpath_query = f"//div[({keywords_condition}) and {exclude_condition}]"

                # ค้นหาโพสต์ที่ตรงตามเงื่อนไข
                posts = driver.find_elements(By.XPATH, xpath_query)

                # แสดงผลโพสต์ที่เจอและเลื่อนหน้าจอไปยังตำแหน่งโพสต์
                for post in posts:
                    if not post.text.strip():
                        continue  # ข้ามโพสต์นี้ไป
                    post_hash = hashlib.sha256(post.text.encode('utf-8')).hexdigest()

                    # ถ้าโพสต์นี้เคยเจอมาก่อนแล้ว (เช็คจาก hash)
                    if post_hash in seen_posts:
                        continue  # ข้ามโพสต์นี้ไป

                    # เพิ่ม hash ของโพสต์ลงในเซต
                    seen_posts.add(post_hash)
                    # แสดงข้อความโพสต์
                    print(post.text)
                    
                    # เลื่อนหน้าจอไปยังตำแหน่งของโพสต์
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'start'});", post)
                    time.sleep(2)
                    try:
                        comment_buttons = post.find_elements(By.XPATH, '//span[@data-ad-rendering-role="comment_button"]')
                        for comment_button in comment_buttons :
                            if is_displayed(driver,comment_button):
                                comment_button.click()
                                print("คลิกที่ปุ่ม 'แสดงความคิดเห็น' แล้ว")
                                actions = ActionChains(driver)
                                lines = comment.split("\n")
                                for i, line in enumerate(lines):
                                    actions.send_keys(line)
                                    if i < len(lines) - 1:  # ถ้าไม่ใช่บรรทัดสุดท้ายให้กด SHIFT+ENTER
                                        actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT)

                                actions.perform()
                                time.sleep(3)  # หน่วงเวลา 3 วินาที
                                # ส่ง RETURN (Enter) และ ESCAPE เพื่อปิดช่องคอมเมนต์
                                # actions.send_keys(Keys.RETURN).send_keys(Keys.ESCAPE).perform()
                    except Exception as e:
                        print(f"ไม่พบปุ่ม 'แสดงความคิดเห็น' หรือไม่สามารถคลิกได้: {e}")
                    sleep_time = random.uniform(1, 10)
                    time.sleep(sleep_time)  # รอเวลาที่สุ่ม

                time.sleep(5)

    except:
            print("การทำงานผิดพลาด")
