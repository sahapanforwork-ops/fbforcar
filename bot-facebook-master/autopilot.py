"""บอททำงานเองอัตโนมัติ (ตั้งเวลาด้วย Windows Task Scheduler ไม่ต้องเปิด Claude หรือนั่งเฝ้า)

    python autopilot.py daily      เข้ากลุ่มใหม่วันละไม่เกิน 5 กลุ่ม แล้วโพสต์กลุ่มละ 1 ครั้งต่อวัน
    python autopilot.py comments   หาโพสต์คนหารถในกลุ่ม แล้วคอมเมนต์ (รอบละไม่เกิน 4 วันละไม่เกิน 15)
    เติม --dry ต่อท้าย = ทำทุกอย่างยกเว้นกดเข้ากลุ่ม กดโพสต์ และส่งคอมเมนต์ (ไว้ลองดูก่อน)

- ใช้ cookies ที่บันทึกไว้ (บัญชีเดียวกับเมนูหลัก) ถ้า cookies หมดอายุ จะหยุดและเขียนบอกใน log
  ให้เปิด index.py ล็อกอินใหม่ 1 ครั้ง
- ข้อความ/รูปโพสต์มาจาก setting.xlsx ชีต "โพสต์ในกลุ่ม" ข้อความ/รูปคอมเมนต์มาจากชีต "ค้นหาและคอมเมนต์"
- เลือกโพสต์ที่จะคอมเมนต์ด้วย services/seeker_rules.py (ตั้งไว้เข้ม: ไม่คอมเมนต์ใต้โฆษณาร้านอื่น)
- ไม่ตอบคำถามก่อนเข้ากลุ่ม ไม่ใส่ลิงก์ ถ้า Facebook ขึ้นเตือน/บล็อก จะหยุดทันที
- ข้อมูลและ log อยู่ที่ %LOCALAPPDATA%\\bot-facebook-master\\autopilot (ไม่ขึ้น git)
"""
import datetime
import json
import os
import random
import re
import sys
import time
import traceback

from selenium import webdriver  # type: ignore
from selenium.common.exceptions import TimeoutException  # type: ignore
from selenium.webdriver.chrome.options import Options  # type: ignore
from selenium.webdriver.common.action_chains import ActionChains  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore
from selenium.webdriver.common.keys import Keys  # type: ignore

PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROGRAM_DIR)
sys.path.insert(0, PROGRAM_DIR)

import pandas as pd  # type: ignore  # noqa: E402
import services.login_facebook as lf  # noqa: E402
from services.excel import _read_sheet, cell_text, pick_variant  # noqa: E402
from services.post_in_group import post_to_group  # noqa: E402
from services.seeker_rules import judge, post_body  # noqa: E402
from utils.commands.image import resolve_images, attach_images  # noqa: E402
from utils.local_store import data_dir  # noqa: E402

STATE_DIR = os.path.join(data_dir("bot-facebook-master"), "autopilot")
LOG_DIR = os.path.join(STATE_DIR, "logs")
MEMBERS_FILE = os.path.join(STATE_DIR, "members.json")    # กลุ่มรถเช่าที่บัญชีนี้เป็นสมาชิก (ใช้โพสต์และหาคนหารถ)
JOINS_FILE = os.path.join(STATE_DIR, "joins.json")        # กลุ่มที่เคยกดเข้าร่วม และสถานะล่าสุด
POSTED_FILE = os.path.join(STATE_DIR, "posted.json")      # กลุ่ม -> วันที่โพสต์ล่าสุด
COMMENTS_FILE = os.path.join(STATE_DIR, "comments.json")  # คอมเมนต์ที่ทำไปแล้ว (กันคนเดิม/ข้อความเดิม)
LOCK_FILE = os.path.join(STATE_DIR, "running.lock")
ME_FILE = os.path.join(STATE_DIR, "me.json")              # ชื่อบัญชีเรา (กันคอมเมนต์โพสต์ตัวเอง)
PAUSE_FILE = os.path.join(STATE_DIR, "paused_until.json")  # Facebook เตือนแล้ว: พักทุกงานถึงเวลานี้
WARNING_PAUSE_HOURS = 72
AUTO_HISTORY = os.path.join(os.path.dirname(PROGRAM_DIR), "bot-facebook-auto-comment", "commented_history.txt")
HISTORY_FILE = AUTO_HISTORY if os.path.isdir(os.path.dirname(AUTO_HISTORY)) else os.path.join(STATE_DIR, "commented_history.txt")
GROUPS_FOUND = os.path.join(PROGRAM_DIR, "groups_found.xlsx")

# ลดลงหลัง Facebook จำกัดบัญชีข้อหาสแปมเมื่อ 19 พ.ย. 2569 (เดิม: เข้ากลุ่ม 5, โพสต์ 12, คอมเมนต์ 4/รอบ 15/วัน)
JOIN_PER_DAY = 2
RECHECK_PER_DAY = 5
MAX_POSTS_PER_DAY = 5
COMMENTS_PER_ROUND = 3
COMMENTS_PER_DAY = 8
SAME_PERSON_DAYS = 3
COMMENT_GAP_SECONDS = (180, 360)
POST_ROUND_GAP_SECONDS = (240, 480)  # เว้นระหว่างโพสต์แต่ละกลุ่มให้ห่างกว่าเดิม
JOIN_GAP_SECONDS = (25, 45)
ANONYMOUS = "ผู้มีส่วนร่วมที่ไม่ระบุตัวตน"

BKK_AREA = re.compile(r"กรุงเทพ|กทม|ปริมณฑล|นนทบุรี|ปทุม|สมุทรปราการ|รังสิต|ดอนเมือง|บางนา|ลาดพร้าว|รามคำแหง|ทั่วไทย")
SKIP_GROUP_NAME = re.compile(r"มอเตอร์ไซ|มอไซ|bike|พร้อมคนขับ|คนขับ|รถตู้|เหมารถ|เชียงใหม่|ภูเก็ต|พัทยา|ชลบุรี|ขอนแก่น|"
                             r"โคราช|อุดร|นครพนม|อยุธยา|หาดใหญ่|ระยอง|หัวหิน", re.I)
BLOCK_WORDS = ["ถูกจำกัด", "จำกัดการใช้งาน", "ไม่สามารถโพสต์", "บล็อกชั่วคราว", "สแปม", "ละเมิดมาตรฐาน",
               "temporarily blocked", "You can't post", "spam", "restricted"]
STRONG_BLOCK_WORDS = ["ถูกจำกัด", "จำกัดการใช้งาน", "บล็อกชั่วคราว", "ละเมิดมาตรฐาน", "temporarily blocked", "You can't post"]

CARDS_JS = r"""
const out = [];
const seen = new Set();
const postLink = a => /\/groups\/[^/]+\/(posts|permalink)\/[^/?#]+|story_fbid=|\/posts\/pfbid/.test(a.href);
for (const btn of document.querySelectorAll('[role="button"][aria-label^="แสดงความคิดเห็นต่อโพสต์ของ"]')) {
  let box = btn;
  for (let i = 0; i < 25 && box.parentElement; i++) {
    box = box.parentElement;
    if ([...box.querySelectorAll('a[href]')].some(postLink)) break;
  }
  const links = [...box.querySelectorAll('a[href]')].filter(postLink).map(a => a.href.split('?')[0]);
  if (!links.length || seen.has(links[0])) continue;
  seen.add(links[0]);
  const msg = box.querySelector('[data-ad-comet-preview="message"], [data-ad-preview="message"]');
  out.push({url: links[0], author: btn.getAttribute('aria-label').replace('แสดงความคิดเห็นต่อโพสต์ของ', '').trim(),
            text: (box.innerText || '').slice(0, 900), message: msg ? msg.innerText : null,
            images: [...box.querySelectorAll('img')].filter(i => i.width >= 150).length});
}
return out;
"""
# ชื่อบัญชีเรา จากช่อง "แสดงความคิดเห็นในชื่อ ..." (ใช้กันไม่ให้คอมเมนต์โพสต์ของตัวเอง)
MY_NAME_JS = r"""
const box = document.querySelector('[aria-label^="แสดงความคิดเห็นในชื่อ"]');
return box ? box.getAttribute('aria-label').replace('แสดงความคิดเห็นในชื่อ', '').trim() : '';
"""
HEADER_BUTTONS_JS = r"""
const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
return [...document.querySelectorAll('[role="button"]')].filter(vis).map(b => {
  const r = b.getBoundingClientRect();
  return (b.getAttribute('aria-label') || '') + ' ' + (b.innerText || '').trim().slice(0, 30) + '@' + Math.round(r.top);
}).filter(s => { const y = +s.split('@').pop(); return y > 120 && y < 360; }).join(' | ');
"""


class Stop(Exception):
    """Facebook เตือน/บล็อก หรือล็อกอินไม่ได้: หยุดงานทั้งหมดทันที
    pause=True (Facebook เตือน): พักทุกงานของบอทต่ออีก WARNING_PAUSE_HOURS ชั่วโมง"""

    def __init__(self, msg, pause=False):
        super().__init__(msg)
        self.pause = pause


# ---------------- เก็บข้อมูลและ log ----------------
def today():
    return datetime.date.today().isoformat()


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line, flush=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(os.path.join(LOG_DIR, f"{today()}.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def group_key(url):
    m = re.search(r"/groups/([^/?#]+)", str(url))
    return m.group(1) if m else str(url)


def post_key(url):
    url = str(url).split("?")[0].rstrip("/")
    return re.sub(r"^https?://(www\.|web\.|m\.)?facebook\.com", "facebook.com", url)


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, encoding="utf-8") as f:
        return {post_key(line.strip()) for line in f if line.strip()}


def add_history(url):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(post_key(url).replace("facebook.com", "https://www.facebook.com", 1) + "\n")


def clean_author(label):
    return re.sub(r",?\s*([\d,.]+\s*(พัน)?\s*)?ความคิดเห็น.*$", "", label or "").strip()


# ---------------- Chrome / Facebook ----------------
def start_chrome():
    options = Options()
    options.add_argument("--disable-notifications")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    os.environ["SE_AVOID_STATS"] = "true"
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1100, 950)
    lf.LOGIN_TIMEOUT_SECONDS = 15  # ไม่มีคนนั่งล็อกอินให้ ถ้า cookies ใช้ไม่ได้ให้หยุดเลย
    if not lf.login(driver):
        driver.quit()
        raise Stop("ล็อกอินด้วย cookies ไม่ได้ (หมดอายุ?) เปิด index.py แล้วล็อกอินใหม่ 1 ครั้ง")
    return driver


def facebook_warning(driver):
    """คืนคำเตือนของ Facebook ถ้ามี (คำถามก่อนเข้ากลุ่มที่พูดถึงสแปมไม่นับ)"""
    dialogs = driver.execute_script(
        "return [...document.querySelectorAll('[role=dialog]')].filter(d => d.getBoundingClientRect().width > 0)"
        ".map(d => d.innerText.slice(0, 400)).filter(t => !t.includes('การตรวจสอบการเข้าร่วม')).join(' | ')") or ""
    body = driver.execute_script("return document.body.innerText") or ""
    hit = [w for w in BLOCK_WORDS if w.lower() in dialogs.lower()] + \
          [w for w in STRONG_BLOCK_WORDS if w.lower() in body.lower()]
    return ", ".join(sorted(set(hit)))


def check_warning(driver, where):
    hit = facebook_warning(driver)
    if hit:
        shot = os.path.join(LOG_DIR, f"warning_{datetime.datetime.now():%Y%m%d_%H%M%S}.png")
        driver.save_screenshot(shot)
        raise Stop(f"Facebook ขึ้นเตือน ({hit}) ตอน {where} หยุดทุกอย่างแล้ว ดูภาพ: {shot}", pause=True)


def paused_until():
    """คืนเวลาที่ยังพักอยู่ (datetime) หรือ None ถ้าไม่ได้พัก"""
    p = load(PAUSE_FILE, {})
    try:
        until = datetime.datetime.fromisoformat(p["until"])
    except (KeyError, TypeError, ValueError):
        return None
    return until if until > datetime.datetime.now() else None


def pause(why):
    until = datetime.datetime.now() + datetime.timedelta(hours=WARNING_PAUSE_HOURS)
    save(PAUSE_FILE, {"until": until.isoformat(timespec="minutes"), "why": why})
    log(f"พักบอททั้งหมดถึง {until:%Y-%m-%d %H:%M} (ลบไฟล์ {PAUSE_FILE} ถ้าจะเริ่มก่อนกำหนด)")


def membership(driver):
    words = driver.execute_script(HEADER_BUTTONS_JS) or ""
    if "ยกเลิกคำขอ" in words:
        return "รอแอดมินอนุมัติ"
    if "เข้าร่วมแล้ว" in words or "เป็นสมาชิก" in words:
        return "เป็นสมาชิกแล้ว"
    if "เข้าร่วมกลุ่ม" in words:
        return "ยังไม่ได้เข้าร่วม"
    return "ไม่แน่ใจ"


# ---------------- งานประจำวัน: เข้ากลุ่ม + โพสต์ ----------------
def join_candidates(members, joins):
    df = pd.read_excel(GROUPS_FOUND)
    have = {group_key(m["url"]) for m in members} | set(joins)
    rows = []
    for _, r in df.iterrows():
        url, name = cell_text(r.get("ลิงก์")), cell_text(r.get("ชื่อกลุ่ม"))
        cat, area = cell_text(r.get("หมวด")), cell_text(r.get("พื้นที่ (จากชื่อกลุ่ม)"))
        if "/groups/" not in url or group_key(url) in have or cat[:1] not in ("1", "2", "3"):
            continue
        if SKIP_GROUP_NAME.search(name) or (area and not BKK_AREA.search(area)):
            continue
        members_n = pd.to_numeric(r.get("สมาชิก"), errors="coerce")
        rows.append((0 if cat[:1] in ("1", "2") else 1, -(0 if pd.isna(members_n) else members_n), url, name))
    rows.sort()
    return [{"url": u, "name": n} for _, _, u, n in rows]


def join_groups(driver, members, joins, dry):
    rechecks = [k for k, j in joins.items() if j["status"] in ("รอแอดมินอนุมัติ", "ไม่แน่ใจ", "ต้องตอบคำถาม (ให้ทำเอง)")]
    for k in rechecks[:RECHECK_PER_DAY]:
        driver.get(joins[k]["url"])
        time.sleep(random.uniform(7, 9))
        status = membership(driver)
        if status != joins[k]["status"]:
            log(f"กลุ่มที่รออยู่: {joins[k]['name'][:40]} -> {status}")
        joins[k].update(status=status, checked=today())
        if status == "เป็นสมาชิกแล้ว" and k not in {group_key(m["url"]) for m in members}:
            members.append({"url": joins[k]["url"], "name": joins[k]["name"]})
    left = JOIN_PER_DAY - sum(1 for j in joins.values() if j.get("date") == today() and j["status"] != "ไม่ใช้")
    if left <= 0:
        log(f"วันนี้เข้ากลุ่มใหม่ครบ {JOIN_PER_DAY} กลุ่มแล้ว")
    for g in join_candidates(members, joins)[:max(0, left)]:
        driver.get(g["url"])
        time.sleep(random.uniform(7, 9))
        status = membership(driver)
        if status == "ยังไม่ได้เข้าร่วม":
            buttons = [b for b in driver.find_elements(
                By.XPATH, '//div[@role="button"][@aria-label="เข้าร่วมกลุ่ม" or .//span[normalize-space(.)="เข้าร่วมกลุ่ม"]]')
                if b.is_displayed() and 120 < driver.execute_script("return arguments[0].getBoundingClientRect().top", b) < 360]
            if dry:
                log(f"ทดลอง: จะกดเข้าร่วม {g['name'][:45]}")
                continue
            if buttons:
                buttons[0].click()
                time.sleep(random.uniform(6, 8))
                dialog = " ".join(d.text for d in driver.find_elements(By.XPATH, '//div[@role="dialog"]') if d.is_displayed())
                if any(w in dialog for w in ("คำถาม", "ตอบ", "กฎ")):
                    status = "ต้องตอบคำถาม (ให้ทำเอง)"  # ไม่ตอบคำถามแทนเจ้าของบัญชี
                    driver.switch_to.active_element.send_keys(Keys.ESCAPE)
                else:
                    driver.get(g["url"])
                    time.sleep(random.uniform(6, 8))
                    status = membership(driver)
            check_warning(driver, f"เข้ากลุ่ม {g['name'][:30]}")
        joins[group_key(g["url"])] = {"url": g["url"], "name": g["name"], "status": status, "date": today()}
        if status == "เป็นสมาชิกแล้ว":
            members.append({"url": g["url"], "name": g["name"]})
        log(f"เข้ากลุ่ม: {g['name'][:45]} -> {status}")
        time.sleep(random.uniform(*JOIN_GAP_SECONDS))


def post_round(driver, members, posted, dry):
    rows = [r for _, r in _read_sheet("โพสต์ในกลุ่ม", ["ลิงค์กลุ่ม", "คอมเมนต์", "รูปภาพ"]).iterrows() if cell_text(r["คอมเมนต์"])]
    text_cell, image_cell = rows[0]["คอมเมนต์"], rows[0]["รูปภาพ"]
    todo = [m for m in members if not m.get("no_post") and posted.get(group_key(m["url"])) != today()]
    log(f"โพสต์วันนี้: {len(todo)} กลุ่ม (สมาชิกทั้งหมด {len(members)} กลุ่ม)")
    done = 0
    for m in todo[:MAX_POSTS_PER_DAY]:
        if done:
            time.sleep(random.uniform(*POST_ROUND_GAP_SECONDS))
        name = m.get("name", "")[:40]
        try:
            pressed = post_to_group(driver, m["url"], pick_variant(cell_text(text_cell)), resolve_images(image_cell), dry_run=dry)
        except TimeoutException:
            body = driver.execute_script("return document.body.innerText") or ""
            if "ขายสินค้า" in body:
                m["no_post"] = True
                log(f"โพสต์ไม่ได้: {name} เป็นกลุ่มแบบลงขายสินค้า (จะไม่โพสต์กลุ่มนี้อีก)")
            else:
                log(f"โพสต์ไม่ได้: {name} (ไม่เจอช่องโพสต์ อาจยังไม่ได้เป็นสมาชิก)")
            continue
        if not pressed:
            continue
        time.sleep(10)
        check_warning(driver, f"โพสต์ {name}")
        posted[group_key(m["url"])] = today()
        done += 1
        driver.get(m["url"])
        time.sleep(random.uniform(7, 9))
        body = driver.execute_script("return document.body.innerText") or ""
        state = "รอแอดมินอนุมัติ" if "รออนุมัติ" in body else ("ขึ้นแล้ว" if "BYD Dolphin" in body else "ส่งแล้ว (ไม่เห็นในฟีด)")
        log(f"โพสต์แล้ว: {name} -> {state}")
    return done


def daily(dry):
    members, joins, posted = load(MEMBERS_FILE, []), load(JOINS_FILE, {}), load(POSTED_FILE, {})
    driver = start_chrome()
    try:
        join_groups(driver, members, joins, dry)
        if not dry:
            save(MEMBERS_FILE, members)
            save(JOINS_FILE, joins)
        n = post_round(driver, members, posted, dry)
        log(f"สรุปงานประจำวัน: โพสต์ {n} กลุ่ม")
    finally:
        if not dry:
            save(MEMBERS_FILE, members)
            save(JOINS_FILE, joins)
            save(POSTED_FILE, posted)
        driver.quit()


# ---------------- หาคนหารถ + คอมเมนต์ ----------------
def scan(driver, members, history, recent):
    found = []
    recent_people = {c["author"] for c in recent if c["author"] and c["author"] != ANONYMOUS}
    recent_texts = {c["body"][:60] for c in recent if len(c.get("body") or "") >= 15}
    me_seen = load(ME_FILE, "")
    for m in members:
        driver.get(m["url"].rstrip("/") + "/?sorting_setting=CHRONOLOGICAL")
        time.sleep(random.uniform(7, 9))
        cards = {}
        for _ in range(6):
            for c in driver.execute_script(CARDS_JS) or []:
                cards.setdefault(c["url"], c)
            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(random.uniform(2.5, 4))
        me = driver.execute_script(MY_NAME_JS) or me_seen
        if me and me != me_seen:
            save(ME_FILE, me)
        me_seen = me
        hits = 0
        for c in cards.values():
            author = clean_author(c["author"])
            ok, why = judge(c["text"], c["images"], c["message"], author=author, me=me)
            body = re.sub(r"\s+", " ", c["message"] or post_body(c["text"]))[:200]
            if ok and post_key(c["url"]) in history:
                ok, why = False, "เคยคอมเมนต์แล้ว"
            elif ok and (author in recent_people or (len(body) >= 15 and body[:60] in recent_texts)):
                ok, why = False, f"คอมเมนต์คนนี้/ข้อความนี้ไปแล้วใน {SAME_PERSON_DAYS} วัน"
            if ok:
                found.append({"url": c["url"], "author": author, "body": body, "group": m.get("name", "")})
                if author != ANONYMOUS:
                    recent_people.add(author)
                if len(body) >= 15:
                    recent_texts.add(body[:60])
                hits += 1
                log(f"  เจอ: {author[:25]} | {body[:90]}")
            elif why not in ("เก่ากว่า 1 วัน", "ไม่ใช่คนหารถ", "โพสต์ของเรา"):
                log(f"  ข้าม ({why}): {author[:25]} | {body[:70]}")
        log(f"หาในกลุ่ม {m.get('name', '')[:35]}: {len(cards)} โพสต์ เข้าเงื่อนไข {hits}")
        time.sleep(random.uniform(4, 8))
    return found


def comment_on(driver, target, text, image, dry):
    driver.get(target["url"])
    time.sleep(random.uniform(6, 8))
    boxes = driver.find_elements(By.XPATH, '//*[contains(@aria-label,"แสดงความคิดเห็นในชื่อ")]')
    if not boxes:
        log(f"  ข้าม: โพสต์นี้ปิดคอมเมนต์ ({target['url']})")
        return None
    box = boxes[0]
    me = box.get_attribute("aria-label").replace("แสดงความคิดเห็นในชื่อ", "").strip()
    if me and me != load(ME_FILE, ""):
        save(ME_FILE, me)
    if me and target["author"] == me:
        log(f"  ข้าม: โพสต์ของเราเอง ({target['url']})")
        return None
    box.click()
    attach_images(driver, image, near=box, wait=8)
    actions = ActionChains(driver).move_to_element(box).click().send_keys(text)
    if dry:
        actions.perform()
        log(f"  ทดลอง: พิมพ์คอมเมนต์แล้วแต่ไม่ส่ง ({target['url']})")
        return True
    actions.send_keys(Keys.RETURN).perform()
    add_history(target["url"])
    time.sleep(8)
    check_warning(driver, "คอมเมนต์")
    seen = driver.execute_script(
        "return [...document.querySelectorAll('[role=article]')].some(a => (a.getAttribute('aria-label') || '').startsWith('ความคิดเห็นจาก ' + arguments[0]))", me)
    log(f"  คอมเมนต์แล้ว{' (เห็นคอมเมนต์ของเราแล้ว)' if seen else ' (ยังไม่เห็นในหน้า อาจโหลดช้า)'}: {target['author'][:25]} | {target['body'][:70]}")
    return True


def comments(dry):
    members = load(MEMBERS_FILE, [])
    done = load(COMMENTS_FILE, [])
    cutoff = (datetime.date.today() - datetime.timedelta(days=SAME_PERSON_DAYS)).isoformat()
    recent = [c for c in done if c["date"] >= cutoff]
    left = min(COMMENTS_PER_ROUND, COMMENTS_PER_DAY - sum(1 for c in done if c["date"] == today()))
    if left <= 0:
        log(f"วันนี้คอมเมนต์ครบ {COMMENTS_PER_DAY} ครั้งแล้ว ไม่ทำรอบนี้")
        return
    row = _read_sheet("ค้นหาและคอมเมนต์", ["คอมเมนต์", "รูปภาพ"]).iloc[0]
    driver = start_chrome()
    try:
        found = scan(driver, members, load_history(), recent)
        log(f"รอบนี้เจอคนหารถที่เข้าเงื่อนไข {len(found)} โพสต์ จะคอมเมนต์ {min(left, len(found))}")
        made = 0
        for t in found:
            if made >= left:
                break
            if dry:  # ทดลอง: ไม่เปิดโพสต์ของคนอื่น แค่บอกว่าจะคอมเมนต์ที่ไหน
                log(f"  ทดลอง: จะคอมเมนต์ {t['author'][:25]} | {t['url']}")
                made += 1
                continue
            if made:
                time.sleep(random.uniform(*COMMENT_GAP_SECONDS))
            text = pick_variant(cell_text(row["คอมเมนต์"])).replace("\n", " ")
            result = comment_on(driver, t, text, resolve_images(row["รูปภาพ"])[:1], dry)
            if result is None:
                if not dry:
                    add_history(t["url"])
                continue
            made += 1
            if not dry:
                done.append({"url": t["url"], "author": t["author"], "body": t["body"], "date": today()})
                save(COMMENTS_FILE, done)
        log(f"สรุปรอบคอมเมนต์: คอมเมนต์ {made} โพสต์")
    finally:
        driver.quit()


# ---------------- main ----------------
def main(argv):
    job = argv[0] if argv else ""
    dry = "--dry" in argv
    if job not in ("daily", "comments"):
        print(__doc__)
        return 2
    os.makedirs(STATE_DIR, exist_ok=True)
    until = paused_until()
    if until:
        log(f"{job}: พักอยู่เพราะ Facebook เตือน ถึง {until:%Y-%m-%d %H:%M} ข้ามรอบนี้")
        return 0
    if os.path.exists(LOCK_FILE) and time.time() - os.path.getmtime(LOCK_FILE) < 3 * 3600:
        log(f"{job}: มีงานอื่นของบอทกำลังทำอยู่ ข้ามรอบนี้")
        return 0
    with open(LOCK_FILE, "w") as f:
        f.write(f"{job} {os.getpid()}")
    log(f"===== เริ่ม {job}{' (ทดลอง)' if dry else ''} =====")
    try:
        (daily if job == "daily" else comments)(dry)
        return 0
    except Stop as e:
        log(f"หยุด: {e}")
        if e.pause and not dry:
            pause(str(e))
        return 1
    except Exception as e:
        log(f"ผิดพลาด: {type(e).__name__}: {e}\n{traceback.format_exc(limit=4)}")
        return 1
    finally:
        os.remove(LOCK_FILE)
        log(f"===== จบ {job} =====")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
