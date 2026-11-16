# facebook_login.py
import os
import time
from selenium.webdriver.common.by import By # type: ignore
from utils.local_store import save_json, load_json

LOGIN_TIMEOUT_SECONDS = 600  # รอให้ล็อกอินเองได้นานสุด 10 นาที


def is_logged_in(driver):
    """เช็คว่าหน้าปัจจุบันล็อกอิน Facebook อยู่จริงหรือไม่"""
    url = driver.current_url
    if any(part in url for part in ("/login", "checkpoint", "two_step_verification", "recover")):
        return False
    if driver.find_elements(By.NAME, "email") and driver.find_elements(By.NAME, "pass"):
        return False  # ยังมีฟอร์มล็อกอินอยู่
    return driver.get_cookie("c_user") is not None


def save_cookies(driver, cookies_file_path, log_queue):
    try:
        os.makedirs(os.path.dirname(cookies_file_path) or ".", exist_ok=True)
        save_json(cookies_file_path, driver.get_cookies())
        log_queue.put(f"บันทึก cookies แบบเข้ารหัสในเครื่องนี้แล้ว: {cookies_file_path}")
    except Exception as e:
        log_queue.put(f"บันทึก cookies ไม่สำเร็จ: {e}")


def load_cookies(driver, cookies_file_path):
    cookies = load_json(cookies_file_path)
    for cookie in cookies:
        try:
            driver.add_cookie(cookie)
        except Exception:
            pass  # ข้าม cookie ที่ใช้ไม่ได้


def ensure_logged_in(driver, cookies_file_path, log_queue):
    """ล็อกอินด้วย cookies ถ้าใช้ได้ ไม่งั้นรอให้ผู้ใช้ล็อกอินเองในหน้าต่าง Chrome เดียวกัน"""
    driver.get("https://www.facebook.com/")

    if os.path.exists(cookies_file_path):
        try:
            load_cookies(driver, cookies_file_path)
            driver.get("https://www.facebook.com/")
            time.sleep(3)
            if is_logged_in(driver):
                log_queue.put("เข้าสู่ระบบด้วย cookies สำเร็จ")
                return True
            log_queue.put("Cookies หมดอายุแล้ว กรุณาล็อกอิน Facebook ในหน้าต่าง Chrome")
        except Exception as e:
            log_queue.put(f"โหลด cookies ไม่สำเร็จ ({e}) กรุณาล็อกอิน Facebook ในหน้าต่าง Chrome")
    else:
        log_queue.put("ไม่พบไฟล์ cookies กรุณาล็อกอิน Facebook ในหน้าต่าง Chrome")

    driver.get("https://www.facebook.com/login")
    log_queue.put("รอล็อกอิน... (ถ้ามียืนยันตัวตน/2FA ให้ทำให้เสร็จ โปรแกรมจะไปต่อเอง)")
    deadline = time.time() + LOGIN_TIMEOUT_SECONDS
    while time.time() < deadline:
        try:
            if is_logged_in(driver):
                log_queue.put("ล็อกอินสำเร็จ")
                save_cookies(driver, cookies_file_path, log_queue)
                return True
        except Exception:
            pass  # หน้ากำลังเปลี่ยน ลองใหม่รอบหน้า
        time.sleep(2)

    log_queue.put("หมดเวลารอล็อกอิน (10 นาที)")
    return False
