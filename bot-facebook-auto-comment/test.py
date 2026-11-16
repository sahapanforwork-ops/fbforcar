import random
import time
import json
import os
from selenium import webdriver  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore
from selenium.webdriver.common.keys import Keys  # type: ignore
from selenium.webdriver.common.action_chains import ActionChains  # type: ignore
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
from selenium.webdriver.support import expected_conditions as EC  # type: ignore
from selenium.webdriver.chrome.service import Service  # type: ignore
from selenium.webdriver.chrome.options import Options  # type: ignore
import pandas as pd  # type: ignore
from command.facebook_login import open_facebook_for_login

def is_cookie_valid(cookies):
    """
    ตรวจสอบว่า cookies หมดอายุหรือไม่
    """
    for cookie in cookies:
        if "expiry" in cookie and cookie["expiry"] < time.time():
            return False
    return True

def scroll_down(driver, scroll_times=3):
    """ฟังก์ชันสำหรับเลื่อนหน้าจอลง"""
    for _ in range(scroll_times):
        driver.execute_script("window.scrollBy(0, 400);")  # เลื่อนลง 1000px
        time.sleep(random.uniform(2, 4))  # รอให้เนื้อหาโหลดอย่างสุ่ม

def random_wait(min_time=1, max_time=5):
    """ฟังก์ชันสำหรับการหยุดเวลาแบบสุ่ม"""
    time.sleep(random.uniform(min_time, max_time))

def start_commenting():
    try:
        # อ่านข้อมูลจาก Excel
        config_file = "config.xlsx"
        if not os.path.exists(config_file):
            print(f"ไม่พบไฟล์ {config_file}")
            return
        config = pd.read_excel(config_file, sheet_name="Sheet1").to_dict(orient="records")
    except Exception as e:
        print(f"Error loading config: {e}")
        return

    # ตั้งค่า WebDriver
    chromedriver_path = "./assets/driver/chromedriver"

    chrome_options = Options()
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument("--disable-notifications")

    # chrome_options.add_argument('--headless')  # ใช้ headless mode หากต้องการ

    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 10)

    try:
        # โหลด cookies
        if os.path.exists("./assets/cookies.json"):
            # โหลด cookies หากไฟล์มีอยู่
            with open("./assets/cookies.json", "r", encoding="utf-8") as file:
                cookies = json.load(file)
                
                # ตรวจสอบว่า cookies หมดอายุหรือไม่
            if not is_cookie_valid(cookies):
                print("Cookies หมดอายุ กำลังเปิด Facebook เพื่อเข้าสู่ระบบใหม่...")
        else:
            # กรณีไม่มีไฟล์ cookies
            print("ไม่พบไฟล์ cookies กำลังเปิด Facebook เพื่อเข้าสู่ระบบ...")


        driver.get('https://facebook.com')
        
        for cookie in cookies:
            driver.add_cookie(cookie)
        driver.get('https://facebook.com')
        search_box = driver.find_element(By.XPATH, '//input[@type="search"]')
        search_box.send_keys("การ์ดจอ 4060")
        search_box.send_keys(Keys.RETURN)
        time.sleep(10)

        # คลิกปุ่มโพสต์ (ตามที่ให้ HTML โค้ดมา)
        post_button = driver.find_element(By.XPATH, '//span[text()="โพสต์"]')
        post_button.click()
        time.sleep(10)
        # วนลูปตาม config
        status = True
        while status:
            # เลื่อนหน้าจอลงทีละนิด ๆ
            scroll_down(driver, 3)
            time.sleep(random.uniform(2, 3))

            # สุ่มการทำกิจกรรม: 70% ไลค์, 30% คอมเมนต์
            # action_choice = random.choices(["like", "comment"], [0.5, 0.5])[0]
            for _ in range(100):
                    like_buttons = driver.find_elements(By.XPATH, "//div[@aria-label='ถูกใจ']")
                    comment_buttons = driver.find_elements(By.XPATH, "//div[@aria-label='แสดงความคิดเห็นในชื่อ EasyClick Bot']")

                # if action_choice == "like":
                    for like_button in like_buttons:
                        try:
                            # รอจนกว่าปุ่มจะสามารถคลิกได้
                            WebDriverWait(driver, 10).until(EC.element_to_be_clickable(like_button))

                            # เลื่อนหน้าจอไปที่ตำแหน่งของปุ่มถูกใจ
                            driver.execute_script("arguments[0].scrollIntoView(true);", like_button)
                            driver.execute_script("window.scrollBy(0, 300);")  # ขยับหน้าจอลงไป 100px

                            # คลิกปุ่มถูกใจ
                            driver.execute_script("arguments[0].click();", like_button)

                            print("คลิกปุ่มถูกใจสำเร็จ!")
                            random_wait(1, 3)  # เว้นระยะเวลาสักนิดก่อนคลิกปุ่มถัดไป
                        except Exception as e:
                            print("Error clicking like:", e)
                    # รีเฟรชหน้า 1 ในทุกๆ 5 รอบ
                    if random.random() < 0.2:
                        driver.refresh()
                        print("รีเฟรชหน้าเว็บ")
                        random_wait(5, 10)

                    for comment_button in comment_buttons:
                        try:
                            # รอจนกว่าปุ่มจะสามารถคลิกได้
                            WebDriverWait(driver, 10).until(EC.element_to_be_clickable(comment_button))

                            # เลื่อนหน้าจอไปที่ตำแหน่งของปุ่มคอมเมนต์
                            driver.execute_script("arguments[0].scrollIntoView(true);", comment_button)
                            driver.execute_script("window.scrollBy(0, 300);")  # ขยับหน้าจอลงไป 100px

                            # คลิกปุ่มคอมเมนต์
                            driver.execute_script("arguments[0].click();", comment_button)

                            random_wait(2, 4)  # เว้นระยะเวลาก่อนคอมเมนต์

                            # พิมพ์คอมเมนต์แบบสุ่ม
                            comment_box = driver.find_element(By.XPATH, "//div[@aria-label='แสดงความคิดเห็นในชื่อ EasyClick Bot']")

                            comment_box.send_keys("🔧 อัพเกรดประสบการณ์การเล่นเกมให้ลื่นไหล! 🚀 การ์ดจอ 4060 สุดคุ้ม ราคานี้ไม่ควรพลาด 🔥 รวดเร็ว มั่นใจ กับประสิทธิภาพที่คุณต้องการ คลิกเลย! 🎮👇 https://s.shopee.co.th/6KpFXE8dm4")  # สามารถปรับข้อความได้

                            # กดปุ่มส่ง
                            comment_box.send_keys(Keys.RETURN)

                            print("คอมเมนต์สำเร็จ!")
                            random_wait(3, 5)  # เว้นระยะเวลาก่อนทำการสุ่มครั้งถัดไป
                        except Exception as e:
                            print("Error commenting:", e)

                    # รีเฟรชหน้า 1 ในทุกๆ 5 รอบ
                    if random.random() < 0.2:
                        driver.refresh()
                        print("รีเฟรชหน้าเว็บ")
                        random_wait(5, 10)

                # เลื่อนหน้าจอลงทีละนิด ๆ ก่อนทำการสุ่มกิจกรรมใหม่
                    scroll_down(driver, 1)

                    time.sleep(random.uniform(60, 120))  # เว้นระยะเวลาระหว่างรอบการทำงาน

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        driver.quit()

start_commenting()
