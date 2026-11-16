"""บอทตอบแชตลูกค้าใน "คำขอส่งข้อความ" และกดยืนยันคำขอเป็นเพื่อน
ใช้บัญชี Facebook และ cookies ชุดเดียวกับเมนูหลัก (index.py)

ทำอะไรบ้าง
- ทุก 2-4 นาที เปิดหน้า "คำขอส่งข้อความ" (คนที่ยังไม่ใช่เพื่อนทักมา)
- แชตไหนทักมาภายใน 24 ชม. และยังไม่มีข้อความจาก "คุณ" เลย จะส่งข้อความใน chat_reply.xlsx ให้ 1 ครั้ง
  ถ้าตอบเองทางมือถือไปแล้ว บอทจะไม่ยุ่งกับแชตนั้นอีก
- ทุก 30 นาที เปิดหน้าคำขอเป็นเพื่อน แล้วกด "ยืนยัน" เฉพาะคำขอที่ส่งมาไม่เกิน 30 วัน (คำขอเก่าไม่แตะ)
- จำแชตที่ตอบแล้วไว้ใน chat_history.txt และเพื่อนที่กดยืนยันแล้วไว้ใน friend_history.txt (ไม่ขึ้น git)

แชตบน Facebook เข้ารหัสต้นทางถึงปลายทาง ครั้งแรกที่เปิด Facebook จะขอ PIN แชต (Messenger)
ให้ใส่ PIN เองในหน้าต่าง Chrome ของบอท ครั้งเดียว บอทใช้โปรไฟล์ Chrome ถาวรของตัวเองจึงจำไว้
บอทไม่ใส่ PIN ให้ และไม่กด "อย่ากู้คืนข้อความ" ถ้ายังไม่ใส่ PIN บอทจะไม่ส่งอะไร
บอทตอบแค่ข้อความแรกของแต่ละแชต ที่เหลือให้คนตอบต่อ

วิธีใช้
  python chat_bot.py          ทำงานไปเรื่อยๆ จนกด Ctrl+C
  python chat_bot.py --dry    ดูอย่างเดียว บอกว่าจะตอบใคร จะกดยืนยันใคร แต่ไม่ส่งและไม่กดจริง
  python chat_bot.py --once   ทำรอบเดียวแล้วจบ
"""
import argparse
import os
import random
import re
import sys
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

from openpyxl import load_workbook  # noqa: E402
from selenium import webdriver  # noqa: E402
from selenium.common.exceptions import StaleElementReferenceException  # noqa: E402
from selenium.webdriver.chrome.options import Options  # noqa: E402
from selenium.webdriver.common.action_chains import ActionChains  # noqa: E402
from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.common.keys import Keys  # noqa: E402

from services.excel import pick_variant  # noqa: E402
from services.login_facebook import login  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPLY_FILE = os.path.join(BASE_DIR, "chat_reply.xlsx")
CHAT_HISTORY = os.path.join(BASE_DIR, "chat_history.txt")
FRIEND_HISTORY = os.path.join(BASE_DIR, "friend_history.txt")
REQUESTS_URL = "https://www.facebook.com/messages/requests/"
FRIENDS_URL = "https://www.facebook.com/friends/requests/"
# โปรไฟล์ Chrome ถาวรของบอทแชต (เหมือนเป็นอุปกรณ์เครื่องหนึ่ง) ใส่ PIN แชตครั้งเดียวแล้วจำไว้
# อยู่นอกโฟลเดอร์โปรเจกต์ ไม่ขึ้น git
PROFILE_DIR = os.path.join(os.environ.get("LOCALAPPDATA", BASE_DIR), "bot-facebook-master", "chat-profile")
PIN_WAIT_SECONDS = 10 * 60        # รอให้ใส่ PIN ได้นานสุด 10 นาที

CHAT_CHECK_SECONDS = (120, 240)   # เช็กแชตใหม่ทุก 2-4 นาที
FRIEND_CHECK_SECONDS = 30 * 60    # เช็กคำขอเป็นเพื่อนทุก 30 นาที
CHAT_MAX_AGE_DAYS = 1             # ตอบเฉพาะแชตที่ทักมาภายใน 24 ชม.
FRIEND_MAX_AGE_DAYS = 30          # ยืนยันเฉพาะคำขอเป็นเพื่อนที่ส่งมาไม่ถึง 1 เดือน
MAX_REPLIES_PER_ROUND = 5
MAX_REPLIES_PER_DAY = 40
MAX_FRIENDS_PER_ROUND = 10
FRIEND_LIST_SCROLLS = 40          # คำขอเป็นเพื่อนเยอะ ต้องเลื่อนหาคำขอใหม่

UNIT_DAYS = {"นาที": 1 / 1440, "ชั่วโมง": 1 / 24, "ชม": 1 / 24, "วัน": 1, "สัปดาห์": 7, "เดือน": 30, "ปี": 365}
AGE_RE = re.compile(r"^(\d+)\s*(นาที|ชั่วโมง|ชม|วัน|สัปดาห์|เดือน|ปี)\.?$")


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def age_days(text):
    """'15 นาที' -> 0.01, '2 ชม.' -> 0.08, '6 สัปดาห์' -> 42, '8 ปี' -> 2920, อ่านไม่ออก -> None"""
    text = (text or "").strip()
    if text in ("เมื่อสักครู่", "ตอนนี้", "ไม่กี่วินาที"):
        return 0
    m = AGE_RE.match(text)
    return int(m.group(1)) * UNIT_DAYS[m.group(2)] if m else None


def check_reply_text(text):
    """คืนรายการปัญหาของข้อความตอบ ถ้าว่างแปลว่าส่งได้"""
    problems = []
    if not text.strip():
        problems.append("ข้อความว่าง")
    left = re.findall(r"\[[^\]]*\]", text)
    if left:
        problems.append("ยังมีช่องที่ต้องแก้: " + ", ".join(left))
    if any(ord(c) > 0xFFFF for c in text):
        problems.append("มีอีโมจิที่ Chrome พิมพ์ไม่ได้ (ใช้ได้แค่อีโมจิพื้นฐาน)")
    return problems


def load_reply_text():
    wb = load_workbook(REPLY_FILE, read_only=True)
    ws = wb.worksheets[0]
    value = ws["A2"].value
    wb.close()
    return str(value or "")


def load_history(path):
    if not os.path.exists(path):
        return {}
    out = {}
    for line in open(path, encoding="utf-8"):
        parts = line.rstrip("\n").split("\t")
        if parts and parts[0]:
            out[parts[0]] = parts[1:]
    return out


def add_history(path, key, *fields):
    with open(path, "a", encoding="utf-8") as f:
        f.write("\t".join([key, *fields, f"{datetime.now():%Y-%m-%d %H:%M}"]) + "\n")


def replies_today(history):
    today = f"{datetime.now():%Y-%m-%d}"
    return sum(1 for v in history.values() if v and v[0] == "replied" and v[-1].startswith(today))


# ---------- แชต ----------

LIST_REQUESTS_JS = r"""
const out = [], seen = new Set();
for (const a of document.querySelectorAll('a[href*="/requests/t/"]')) {
  const m = a.getAttribute('href').match(/\/requests\/t\/(\d+)/);
  if (!m || seen.has(m[1])) continue;
  seen.add(m[1]);
  out.push({id: m[1], href: a.getAttribute('href'), text: a.innerText || ''});
}
return out;
"""

READ_THREAD_JS = r"""
let mine = 0, theirs = 0;
for (const e of document.querySelectorAll('[aria-label]')) {
  const l = e.getAttribute('aria-label');
  const m = l.match(/^เมื่อ .+?, (.+)$/);
  if (m) { if (m[1].trim() === 'คุณ') mine++; else theirs++; continue; }
  if (/^ป้อน, ข้อความที่ส่งเมื่อ .+ โดย คุณ$/.test(l)) mine++;
}
const box = [...document.querySelectorAll('[role="textbox"][contenteditable="true"]')]
  .find(e => (e.getAttribute('aria-label') || '').startsWith('เขียนถึง'));
const pin = [...document.querySelectorAll('[role="dialog"]')].some(d => /PIN/.test(d.innerText || ''));
return {mine, theirs, box: box || null, pin};
"""


def thread_name(text):
    skip = {"กำลังใช้งาน", "คำขอส่งข้อความ", ""}
    lines = [s.strip() for s in text.split("\n")]
    return next((s for s in lines if s not in skip), "?")


def thread_age(text):
    """อายุแชตจากรายการ: ข้อความหลังจุด '·' ตัวสุดท้าย เช่น '... · 15 นาที'"""
    flat = re.sub(r"\s+", " ", text)
    return age_days(flat.rsplit("·", 1)[1]) if "·" in flat else None


def pin_dialog_open(driver):
    return any("PIN" in (d.text or "") for d in driver.find_elements(By.CSS_SELECTOR, '[role="dialog"]'))


def wait_for_pin(driver):
    """แชตเข้ารหัส: ถ้าขึ้นหน้าต่าง 'ป้อน PIN เพื่อกู้คืนแชท' ให้คนใส่ PIN เองในหน้าต่าง Chrome ของบอท
    บอทไม่ใส่ PIN ให้ และไม่กดปิดหรือกด 'อย่ากู้คืนข้อความ' เด็ดขาด ใส่ครั้งเดียว โปรไฟล์ของบอทจะจำไว้"""
    if not pin_dialog_open(driver):
        return True
    log("🔐 Facebook ขอ PIN แชต: ใส่ PIN Messenger ในหน้าต่าง Chrome ของบอทเอง (ใส่ครั้งเดียว ครั้งต่อไปไม่ต้อง)")
    log("   อย่ากดปิดหรือกด 'อย่ากู้คืนข้อความ' บอทจะรอให้ใส่ 10 นาที")
    deadline = time.time() + PIN_WAIT_SECONDS
    while time.time() < deadline:
        time.sleep(3)
        if not pin_dialog_open(driver):
            log("ใส่ PIN แล้ว ทำงานต่อ")
            time.sleep(8)  # รอข้อความเก่ากู้คืน
            return True
    log("ยังไม่ได้ใส่ PIN ข้ามการตอบแชตรอบนี้ (ไม่ส่งอะไร)")
    return False


def type_message(driver, box, text):
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].focus();", box)
    box.click()
    time.sleep(1)
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line:
            box.send_keys(line)
        if i < len(lines) - 1:  # ขึ้นบรรทัดใหม่โดยไม่ส่ง
            ActionChains(driver).key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
    time.sleep(random.uniform(1, 2))
    box.send_keys(Keys.ENTER)


def check_chats(driver, reply_text, dry):
    history = load_history(CHAT_HISTORY)
    if replies_today(history) >= MAX_REPLIES_PER_DAY:
        log(f"วันนี้ตอบครบ {MAX_REPLIES_PER_DAY} แชตแล้ว พักการตอบถึงพรุ่งนี้")
        return
    driver.get(REQUESTS_URL)
    time.sleep(random.uniform(7, 10))
    threads = driver.execute_script(LIST_REQUESTS_JS) or []
    new = []
    for t in threads:
        age = thread_age(t["text"])
        if t["id"] in history or age is None or age > CHAT_MAX_AGE_DAYS:
            continue
        new.append(t)
    log(f"คำขอส่งข้อความทั้งหมด {len(threads)} แชต, ใหม่ที่ยังไม่ได้ตอบ {len(new)} แชต")

    sent = 0
    for t in new:
        if sent >= MAX_REPLIES_PER_ROUND:
            break
        name = thread_name(t["text"])
        driver.get("https://www.facebook.com" + t["href"])
        time.sleep(random.uniform(6, 9))
        if not wait_for_pin(driver):
            return
        info = driver.execute_script(READ_THREAD_JS)
        if info["mine"] > 0:
            log(f"ข้าม {name}: ตอบเองไปแล้ว")
            if not dry:
                add_history(CHAT_HISTORY, t["id"], "human")
            continue
        if info["theirs"] == 0:
            log(f"ข้าม {name}: อ่านแชตไม่ออก จะลองใหม่รอบหน้า")
            continue
        if not info["box"]:
            log(f"ข้าม {name}: ไม่เจอช่องพิมพ์ข้อความ จะลองใหม่รอบหน้า")
            continue
        text = pick_variant(reply_text)
        if dry:
            log(f"[ทดลอง] จะตอบ {name} (ลูกค้าส่งมา {info['theirs']} ข้อความ) แต่ไม่ส่งจริง")
            continue
        type_message(driver, info["box"], text)
        time.sleep(5)
        after = driver.execute_script(READ_THREAD_JS)
        if after["mine"] > 0:
            add_history(CHAT_HISTORY, t["id"], "replied")
            sent += 1
            log(f"✅ ตอบ {name} แล้ว")
        else:
            log(f"❓ ส่งให้ {name} แล้วแต่ยังไม่เห็นข้อความในแชต จะเช็กใหม่รอบหน้า")
        time.sleep(random.uniform(15, 40))


# ---------- คำขอเป็นเพื่อน ----------

LIST_FRIENDS_JS = r"""
const out = [], seen = new Set();
for (const b of document.querySelectorAll('[role="button"][aria-label^="ยืนยัน "]')) {
  if (!(b.innerText || '').includes('ยืนยัน')) continue;
  const name = b.getAttribute('aria-label').slice('ยืนยัน '.length);
  if (seen.has(name)) continue;
  seen.add(name);
  // ปุ่มอยู่ในกล่องแยกจากชื่อ/อายุ ไต่ขึ้นไปจนเจอกล่องที่มีชื่อคนนั้น = การ์ดของคนนั้น
  let card = b;
  for (let i = 0; i < 10 && card.parentElement; i++) {
    card = card.parentElement;
    if ((card.innerText || '').includes(name)) break;
  }
  out.push({name, text: card.innerText || '', button: b});
}
return out;
"""

# รายการคำขอโหลดเพิ่มเมื่อเลื่อน "กล่องรายการ" ลงสุด (เลื่อนหน้าเว็บหรือ scrollIntoView ไม่โหลดเพิ่ม)
SCROLL_FRIENDS_JS = r"""
let e = document.querySelector('[role="button"][aria-label^="ยืนยัน "], [role="button"][aria-label^="ลบ "]');
while (e && !(e.scrollHeight > e.clientHeight + 5 && /auto|scroll/.test(getComputedStyle(e).overflowY))) e = e.parentElement;
if (e) e.scrollTop = e.scrollHeight; else window.scrollTo(0, document.body.scrollHeight);
"""


def friend_age(card_text):
    for line in card_text.split("\n"):
        days = age_days(line)
        if days is not None:
            return days
    return None


def check_friends(driver, dry):
    history = load_history(FRIEND_HISTORY)
    driver.get(FRIENDS_URL)
    time.sleep(random.uniform(7, 10))
    accepted, seen, old, unknown = 0, set(), 0, 0
    last_count, still = 0, 0
    for _ in range(FRIEND_LIST_SCROLLS):
        cards = driver.execute_script(LIST_FRIENDS_JS) or []
        for c in cards:
            if c["name"] in seen:
                continue
            seen.add(c["name"])
            days = friend_age(c["text"])
            if days is None:
                unknown += 1
                continue
            if days >= FRIEND_MAX_AGE_DAYS:  # "1 เดือน" ถือว่าเก่าแล้ว, "4 สัปดาห์" ยังใหม่
                old += 1
                continue
            if c["name"] in history or accepted >= MAX_FRIENDS_PER_ROUND:
                continue
            if dry:
                log(f"[ทดลอง] จะกดยืนยันเพื่อน {c['name']} (ส่งคำขอมา {days:.1f} วัน) แต่ไม่กดจริง")
                accepted += 1
                continue
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", c["button"])
                time.sleep(random.uniform(1, 2))
                c["button"].click()
            except StaleElementReferenceException:
                seen.discard(c["name"])  # รายการขยับ หาใหม่รอบเลื่อนถัดไป
                continue
            time.sleep(random.uniform(3, 5))
            add_history(FRIEND_HISTORY, c["name"], "accepted")
            accepted += 1
            log(f"✅ ยืนยันเพื่อน {c['name']} แล้ว")
            time.sleep(random.uniform(4, 10))
        if len(seen) == last_count:
            still += 1
            if still >= 3:
                break  # เลื่อน 3 ครั้งแล้วไม่มีคำขอเพิ่ม แปลว่าครบแล้ว
        else:
            still = 0
        last_count = len(seen)
        # หาปุ่มใหม่ทุกครั้ง เพราะการ์ดที่กดยืนยันไปแล้วจะเปลี่ยนหน้าตา (ปุ่มเดิมใช้ไม่ได้)
        driver.execute_script(SCROLL_FRIENDS_JS)
        time.sleep(random.uniform(3, 5))
    log(f"คำขอเป็นเพื่อนที่ดู {len(seen)} รายการ: ยืนยัน{'(ทดลอง)' if dry else ''} {accepted}, "
        f"เก่าเกิน {FRIEND_MAX_AGE_DAYS} วัน {old}, อ่านอายุไม่ออก {unknown}")


# ---------- โปรแกรมหลัก ----------

def make_driver():
    options = Options()
    options.add_argument("--disable-notifications")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")  # อุปกรณ์ถาวรของบอท จำ PIN แชตไว้
    os.environ["SE_AVOID_STATS"] = "true"
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1200, 900)
    return driver


def main(argv=None):
    ap = argparse.ArgumentParser(description="บอทตอบแชตลูกค้าและกดยืนยันคำขอเป็นเพื่อน")
    ap.add_argument("--dry", action="store_true", help="ดูอย่างเดียว ไม่ส่งข้อความ ไม่กดยืนยัน")
    ap.add_argument("--once", action="store_true", help="ทำรอบเดียวแล้วจบ")
    args = ap.parse_args(argv)

    reply_text = load_reply_text()
    problems = [p for v in re.split(r"(?m)^\s*-{3,}\s*$", reply_text) for p in check_reply_text(v)]
    if problems:
        log("แก้ข้อความใน chat_reply.xlsx ก่อน: " + " | ".join(problems))
        return 1

    driver = make_driver()
    try:
        if not login(driver):
            return 1
        log("เริ่มทำงาน" + (" (โหมดทดลอง ไม่ส่งจริง)" if args.dry else "") + " กด Ctrl+C เพื่อหยุด")
        next_friend_check = 0
        while True:
            for job in (lambda: check_chats(driver, reply_text, args.dry),
                        lambda: check_friends(driver, args.dry) if time.time() >= next_friend_check else None):
                try:
                    job()
                except Exception as e:  # หน้าเว็บเปลี่ยนกลางคัน ฯลฯ ทำรอบหน้าต่อ
                    log(f"⚠️ มีปัญหา: {type(e).__name__}: {str(e).splitlines()[0][:150] if str(e) else ''}")
                    if "invalid session" in str(e).lower() or "no such window" in str(e).lower():
                        raise
            if time.time() >= next_friend_check:
                next_friend_check = time.time() + FRIEND_CHECK_SECONDS
            if args.once:
                break
            wait = random.uniform(*CHAT_CHECK_SECONDS)
            log(f"รอ {wait / 60:.1f} นาที แล้วเช็กใหม่")
            time.sleep(wait)
    except KeyboardInterrupt:
        log("หยุดแล้ว")
    finally:
        driver.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
