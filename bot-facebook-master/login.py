"""ล็อกอิน Facebook ใหม่ แล้วบันทึก cookies ให้ทั้ง 2 บอท (bot-facebook-master และ bot-facebook-auto-comment)

ใช้เมื่อ log ของ autopilot บอกว่า "ล็อกอินด้วย cookies ไม่ได้" หรือเปลี่ยนบัญชี
- เปิด Chrome หน้า Facebook ให้ล็อกอินเอง (รวมยืนยันตัวตน/2FA) รอได้นานสุด 10 นาที
- cookies ถูกเข้ารหัสเก็บในเครื่องนี้เท่านั้น ไม่อยู่ในโฟลเดอร์นี้และไม่ขึ้น git
- ระหว่างล็อกอิน อย่าเปิดบอทตัวอื่นด้วยบัญชีเดียวกันพร้อมกัน (Facebook อาจตัด session)
"""
import os
import sys
import time

PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROGRAM_DIR)
sys.path.insert(0, PROGRAM_DIR)

from selenium import webdriver  # type: ignore  # noqa: E402
from selenium.webdriver.chrome.options import Options  # type: ignore  # noqa: E402
import services.login_facebook as lf  # noqa: E402
from utils.local_store import data_dir, save_json  # noqa: E402

AUTO_COOKIES = os.path.join(data_dir("bot-facebook-auto-comment"), "cookies.dat")


def main():
    options = Options()
    options.add_argument("--disable-notifications")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    os.environ["SE_AVOID_STATS"] = "true"
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1000, 900)
    try:
        print("ล็อกอิน Facebook ในหน้าต่าง Chrome ที่เปิดขึ้นมา (รอได้ 10 นาที)")
        if not lf.login(driver):
            print("ล็อกอินไม่สำเร็จหรือหมดเวลา ลองใหม่อีกครั้ง")
            return 1
        lf.save_cookies(driver)
        save_json(AUTO_COOKIES, driver.get_cookies())
        driver.get("https://www.facebook.com/me")
        time.sleep(5)
        print(f"บันทึกแล้วทั้ง 2 บอท: {(driver.title or '').replace('| Facebook', '').strip()}")
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    sys.exit(main())
