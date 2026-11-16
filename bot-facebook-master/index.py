from selenium import webdriver # type: ignore
from selenium.webdriver.chrome.options import Options # type: ignore

from services.login_facebook import login
from utils.select_choice import select, select_time, select_auto
from services.search_topic import start_search_topic
from services.comment_in_group import start_comment_in_group
from services.comment_in_post import start_comment_in_post
from services.post_in_group import start_post_in_group
from services.auto_play import auto
from services.comment_in_group_advance import start_comment_in_group_advance
import os
import sys
import time

# ให้พิมพ์ภาษาไทย/อีโมจิออกหน้าจอได้เสมอ (กันโปรแกรมพังเมื่อหน้าจอไม่ใช่ UTF-8)
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ให้อ่าน setting.xlsx / facebook_cookies.json / รูปภาพ จากโฟลเดอร์โปรแกรมเสมอ ไม่ว่าจะรันจากที่ไหน
BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

user_login = True

if user_login:
    print("🔓 Successfully logged in!")
    choice = select()
    time_count = select_time()
    play_auto = False
    if time_count >= 1:
        play_auto = select_auto()

    options = Options()
    options.add_argument('--disable-notifications')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Selenium จะหา/ดาวน์โหลด ChromeDriver ที่ตรงกับ Chrome ในเครื่องให้เอง
    # ปิดการส่งสถิติการใช้งานของ Selenium Manager ไปที่ plausible.io
    os.environ["SE_AVOID_STATS"] = "true"
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(600, 800)
    try:
        if login(driver):
            status = True
            while status:
                if choice == '1.1':
                    start_search_topic(driver, True)
                elif choice == '1.2':
                    start_search_topic(driver, False)
                elif choice == '2.1':
                    start_comment_in_group(driver, True)
                elif choice == '2.2':
                    start_comment_in_group(driver, False)
                elif choice == '3':
                    start_comment_in_group_advance(driver)
                elif choice == '4':
                    start_comment_in_post(driver)
                elif choice == '5':
                    start_post_in_group(driver)

                if time_count <= 0:
                    status = False
                    print("✅ ทำงานครบแล้ว")
                elif play_auto and choice != '4':
                    auto(driver, time_count)
                else:
                    print(f"⏳ รอ {time_count} นาที แล้วจะทำรอบถัดไป (กด Ctrl + C เพื่อหยุด)")
                    time.sleep(time_count * 60)

    except KeyboardInterrupt:
        print("\n🛑 Program stopped!")
    finally:
        driver.quit()  # Close the browser

else:
    print("🔒 Login failed!")
