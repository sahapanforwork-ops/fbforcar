from selenium.webdriver.common.by import By  # type: ignore
from utils.local_store import data_dir, save_json, load_json
import time
import os

# เก็บ cookies ในเครื่องนี้เท่านั้น (%LOCALAPPDATA%\bot-facebook-master) แบบเข้ารหัส ไม่อยู่ในโฟลเดอร์ OneDrive
COOKIES_FILE = os.path.join(data_dir("bot-facebook-master"), "facebook_cookies.dat")
LOGIN_TIMEOUT_SECONDS = 600  # รอให้ล็อกอินเองได้นานสุด 10 นาที


def is_logged_in(driver):
    """เช็คว่าหน้าปัจจุบันล็อกอิน Facebook อยู่จริงหรือไม่"""
    url = driver.current_url
    if any(part in url for part in ("/login", "checkpoint", "two_step_verification", "recover")):
        return False
    if driver.find_elements(By.NAME, "email") and driver.find_elements(By.NAME, "pass"):
        return False  # ยังมีฟอร์มล็อกอินอยู่
    return driver.get_cookie("c_user") is not None


def load_cookies(driver):
    cookies = load_json(COOKIES_FILE)
    for cookie in cookies:
        try:
            driver.add_cookie(cookie)
        except Exception:
            pass  # ข้าม cookie ที่ใช้ไม่ได้


def save_cookies(driver):
    save_json(COOKIES_FILE, driver.get_cookies())
    print(f"Cookies have been saved (encrypted, this PC only): {COOKIES_FILE}")


def login(driver):
    driver.get('https://www.facebook.com/')

    # If cookies exist, load them
    if os.path.exists(COOKIES_FILE):
        print("Saved cookies found. Loading...")
        try:
            load_cookies(driver)
            driver.get('https://www.facebook.com/')  # โหลดหน้าใหม่ให้ cookies มีผล
            time.sleep(3)
            if is_logged_in(driver):
                print("Successfully logged in using cookies!")
                return True
            print("⚠️ Cookies หมดอายุหรือใช้ไม่ได้แล้ว ต้องล็อกอินใหม่")
        except Exception as e:
            print(f"⚠️ โหลด cookies ไม่สำเร็จ ({e}) ต้องล็อกอินใหม่")

    # ล็อกอินเองในหน้าต่าง Chrome ที่เปิดขึ้นมา
    driver.get('https://www.facebook.com/login')
    print("Please log in to Facebook manually in the Chrome window.")
    print("(ถ้ามียืนยันตัวตน/2FA ให้ทำให้เสร็จ โปรแกรมจะไปต่อเองเมื่อเข้าหน้าแรกของ Facebook ได้)")
    deadline = time.time() + LOGIN_TIMEOUT_SECONDS
    while time.time() < deadline:
        try:
            if is_logged_in(driver):
                print("Login successful!")
                save_cookies(driver)
                return True
        except Exception:
            pass  # หน้ากำลังเปลี่ยน ลองใหม่รอบหน้า
        time.sleep(2)

    print("🔒 หมดเวลารอล็อกอิน")
    return False
