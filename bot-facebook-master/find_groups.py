"""ค้นหากลุ่ม Facebook ตามคำค้น แล้วเก็บรายชื่อกลุ่มลง groups_found.xlsx (อ่านอย่างเดียว ไม่กดเข้าร่วม ไม่โพสต์)

วิธีใช้:
    python find_groups.py                       ใช้คำค้นใน KEYWORDS ด้านล่าง
    python find_groups.py "รถเช่า เชียงใหม่" "เช่ารถ ภูเก็ต"   ใช้คำค้นที่พิมพ์ต่อท้าย

ล็อกอินใช้ cookies เดียวกับ index.py (ถ้ายังไม่เคยล็อกอิน จะเปิด Chrome ให้ล็อกอินเองก่อน)
"""
import os
import random
import re
import sys
import time
from urllib.parse import quote

import pandas as pd  # type: ignore
from selenium import webdriver  # type: ignore
from selenium.webdriver.chrome.options import Options  # type: ignore

from services.login_facebook import login

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "groups_found.xlsx")

KEYWORDS = [
    "รถเช่า",
    "หารถเช่า",
    "เช่ารถ รายเดือน",
    "รถเช่า รายวัน",
    "เช่ารถขับ Grab",
    "BYD Dolphin",
    "BYD",
    "รถยนต์ไฟฟ้า",
    "รถ EV",
]
SCROLLS_PER_KEYWORD = 5  # เลื่อนผลค้นหากี่ครั้งต่อคำ (ยิ่งมากยิ่งได้กลุ่มเยอะ แต่ช้าลง)

# อ่านการ์ดผลค้นหาทุกใบที่มีลิงก์ไปกลุ่ม: ชื่อกลุ่ม + ข้อความในการ์ด (ประเภท · สมาชิก · โพสต์ต่อวัน)
COLLECT_JS = r"""
const skip = /\/groups\/(feed|discover|joins|create|search|notifications|categories|your_groups)(\/|$|\?)/;
const groupKey = href => { if (skip.test(href)) return null; const m = href.match(/\/groups\/([^/?#]+)/); return m ? m[1] : null; };
const hasMembers = t => /สมาชิก|members?\b/i.test(t);
const out = [], seen = new Set();
for (const a of document.querySelectorAll('a[href*="/groups/"]')) {
  const key = groupKey(a.href);
  if (!key || seen.has(key)) continue;
  const name = (a.innerText || '').trim();
  if (!name) continue;
  // ไต่ขึ้นไปหากรอบการ์ดของกลุ่มนี้: เจอบรรทัดสมาชิกแล้วไต่ต่ออีกนิดเพื่อให้ได้ปุ่ม เข้าร่วม/เยี่ยมชม
  // แต่หยุดก่อนถึงกล่องที่มีกลุ่มอื่นปนอยู่
  let box = a, extra = 0;
  for (let i = 0; i < 20 && box.parentElement && box.parentElement !== document.body; i++) {
    const up = box.parentElement;
    const keys = new Set([...up.querySelectorAll('a[href*="/groups/"]')].map(x => groupKey(x.href)).filter(Boolean));
    if (keys.size > 1) break;
    box = up;
    const role = box.getAttribute('role');
    if (role === 'article' || role === 'listitem') break;
    if (hasMembers(box.innerText || '') && ++extra > 4) break;
  }
  const text = box.innerText || '';
  if (!hasMembers(text)) continue;
  seen.add(key);
  const host = a.href.match(/^https?:\/\/[^/]+/)[0].replace(/\/\/(web|m)\.facebook/, '//www.facebook');
  out.push({ url: host + '/groups/' + key + '/', name: name, text: text.slice(0, 800) });
}
return out;
"""

_UNITS = {"k": 1e3, "พัน": 1e3, "หมื่น": 1e4, "แสน": 1e5, "m": 1e6, "ล้าน": 1e6}
_NUM = r"([\d][\d,.]*)\s*(k|m|พัน|หมื่น|แสน|ล้าน)?"


def parse_members(text):
    """'สมาชิก 1.5 แสน คน' / 'สมาชิก 2.3K คน' / '12K members' -> จำนวนเต็ม (หาไม่เจอ = None)"""
    for pattern in (r"สมาชิก\s*" + _NUM, _NUM + r"\s*(?:คน\s*)?(?:สมาชิก|members?\b)"):
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            number = float(m.group(1).replace(",", ""))
            return int(round(number * _UNITS.get((m.group(2) or "").lower(), 1)))
    return None


def parse_card(name, text):
    parts = [p.strip() for p in re.split(r"[·\n]", text) if p.strip()]
    privacy = "สาธารณะ" if re.search(r"สาธารณะ|\bPublic\b", text) else "ส่วนตัว" if re.search(r"ส่วนตัว|\bPrivate\b", text) else ""
    members_part = next((p for p in parts if re.search(r"สมาชิก|members?\b", p, re.IGNORECASE)), "")
    posts = next((p for p in parts if re.search(r"ต่อวัน|ต่อสัปดาห์|ต่อเดือน|ต่อปี|\ba (day|week|month|year)\b", p)), "")
    if re.search(r"เข้าร่วมแล้ว|เยี่ยมชม|ดูกลุ่ม|\bVisit\b|\bJoined\b", text):
        status = "เป็นสมาชิกแล้ว"
    elif re.search(r"เข้าร่วม|\bJoin\b", text):
        status = "ยังไม่ได้เข้าร่วม"
    else:
        status = ""
    noise = {name, members_part, posts, "สาธารณะ", "ส่วนตัว", "Public", "Private",
             "เข้าร่วม", "เข้าร่วมกลุ่ม", "เยี่ยมชม", "ดูกลุ่ม", "Join", "Visit", "Join group"}
    about = " ".join(p for p in parts if p not in noise and not re.search(r"สมาชิก|members?\b", p))[:200]
    return {
        "ชื่อกลุ่ม": name,
        "ลิงก์": None,
        "ประเภท": privacy,
        "สมาชิก": parse_members(text),
        "สมาชิก (ตามที่ FB แสดง)": members_part,
        "ความถี่โพสต์": posts,
        "สถานะของฉัน": status,
        "รายละเอียด": about,
    }


def search_groups(driver, keyword, scrolls=SCROLLS_PER_KEYWORD):
    driver.get("https://www.facebook.com/search/groups/?q=" + quote(keyword))
    time.sleep(random.uniform(5, 8))
    for _ in range(scrolls):
        driver.execute_script("window.scrollBy(0, 1500);")
        time.sleep(random.uniform(2, 4))
    rows = []
    for item in driver.execute_script(COLLECT_JS) or []:
        row = parse_card(item["name"], item["text"])
        row["ลิงก์"] = item["url"]
        rows.append(row)
    return rows


def save(found):
    if not found:
        return
    df = pd.DataFrame(list(found.values()))
    df = df.sort_values("สมาชิก", ascending=False, na_position="last")
    df.to_excel(OUTPUT_FILE, index=False)


def run(driver, keywords):
    found = {}
    for i, keyword in enumerate(keywords, 1):
        try:
            rows = search_groups(driver, keyword)
        except Exception as e:
            print(f"⚠️ ค้นหา '{keyword}' ไม่สำเร็จ: {type(e).__name__} {e}")
            continue
        new = 0
        for row in rows:
            if row["ลิงก์"] in found:
                found[row["ลิงก์"]]["คำค้นที่เจอ"] += ", " + keyword
            else:
                row["คำค้นที่เจอ"] = keyword
                found[row["ลิงก์"]] = row
                new += 1
        print(f"[{i}/{len(keywords)}] '{keyword}': เจอ {len(rows)} กลุ่ม (ใหม่ {new}) รวม {len(found)} กลุ่ม", flush=True)
        save(found)  # บันทึกทุกคำ ถ้าปิดกลางคันก็ยังได้ผลที่หาไว้แล้ว
        time.sleep(random.uniform(5, 10))
    return found


def main():
    os.chdir(BASE_DIR)
    keywords = sys.argv[1:] or KEYWORDS
    options = Options()
    options.add_argument("--disable-notifications")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    os.environ["SE_AVOID_STATS"] = "true"
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1000, 900)
    try:
        if not login(driver):
            print("🔒 ล็อกอินไม่สำเร็จ หยุดทำงาน")
            return
        found = run(driver, keywords)
        if found:
            print(f"✅ เสร็จแล้ว เจอทั้งหมด {len(found)} กลุ่ม บันทึกที่ {OUTPUT_FILE}")
        else:
            print("⚠️ ไม่เจอกลุ่มเลย (หน้าค้นหาของ Facebook อาจเปลี่ยนรูปแบบ)")
    except KeyboardInterrupt:
        print("\n🛑 หยุดแล้ว (ผลที่หาได้ถูกบันทึกไว้แล้ว)")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
