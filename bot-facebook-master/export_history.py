"""คัดลอกประวัติของ autopilot จากเครื่องนี้มาไว้ในโฟลเดอร์ history/ เพื่อขึ้น git

รีโปเป็นสาธารณะ จึงเอาข้อมูลพวกนี้ออกก่อน:
- ชื่อบัญชีเรา (me.json ไม่คัดลอก) และชื่อคนที่เราไปเจอ/คอมเมนต์ (แทนด้วย [ชื่อ])
- เบอร์โทรและไอดี LINE ของคนอื่นในข้อความโพสต์ (เบอร์และ LINE ของ IMP CarRent เก็บไว้)
- ภาพหน้าจอคำเตือน (มีหน้าบัญชีเรา) และ path ในเครื่อง
ไม่แตะ cookies ไม่แก้ไฟล์ต้นฉบับ: รันซ้ำกี่ครั้งก็ได้ ไฟล์ใน history/ จะถูกเขียนทับด้วยของล่าสุด
"""
import json
import os
import re
import sys

PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROGRAM_DIR)
from utils.local_store import data_dir  # noqa: E402

SRC = os.path.join(data_dir("bot-facebook-master"), "autopilot")
OUT = os.path.join(PROGRAM_DIR, "history")
FILES = ["posted.json", "joins.json", "members.json", "comments.json", "paused_until.json"]
ANONYMOUS = "ผู้มีส่วนร่วมที่ไม่ระบุตัวตน"
OUR_PHONE = re.compile(r"0?96[-\s]?219[-\s]?4138")
PHONE = re.compile(r"(?<!\d)0[689]\d[-\s.]?\d{3}[-\s.]?\d{4}(?!\d)|(?<!\d)0[2-7][-\s.]?\d{3}[-\s.]?\d{4}(?!\d)")
LINE_ID = re.compile(r"(?i)(?:(?:ไลน์|ไอดี)(?:\s*ไลน์|\s*id)?\s*[:：]?\s*@?|\b(?:line\s*(?:id)?|id)\s*(?:[:：]\s*@?|@))"
                     r"(?!804bunik)[a-z0-9._\-]{3,}")  # ไม่จับ "LINE MAN" (ภาษาอังกฤษต้องมี : หรือ @)
# บรรทัด log ที่มีชื่อคน: "เจอ: NAME | ...", "ข้าม (...): NAME | ...", "คอมเมนต์แล้ว (...): NAME | ...", "จะคอมเมนต์ NAME | ..."
LOG_NAME = re.compile(r"((?:เจอ|\)|จะคอมเมนต์):?\s)([^|\n]+?)(\s\|)")


def scrub_text(text, me):
    if not text:
        return text
    if me:
        text = text.replace(me, "[บัญชีเรา]")
    text = PHONE.sub(lambda m: m.group(0) if OUR_PHONE.fullmatch(m.group(0).strip()) else "[เบอร์]", text)
    text = LINE_ID.sub("[LINE]", text)
    text = re.sub(r"[A-Za-z]:\\Users\\[^\\\s]+\\AppData\\Local", r"%LOCALAPPDATA%", text)
    return text


def scrub_log_line(line, me):
    line = LOG_NAME.sub(lambda m: m.group(1) + (m.group(2) if m.group(2).strip() == ANONYMOUS else "[ชื่อ]") + m.group(3), line)
    return scrub_text(line, me)


def main():
    me = ""
    try:
        with open(os.path.join(SRC, "me.json"), encoding="utf-8") as f:
            me = json.load(f) or ""
    except (OSError, ValueError):
        pass
    os.makedirs(os.path.join(OUT, "logs"), exist_ok=True)
    for name in FILES:
        path = os.path.join(SRC, name)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if name == "comments.json":
            for c in data:
                if c.get("author") and c["author"] != ANONYMOUS:
                    c["author"] = "[ชื่อ]"
                c["body"] = scrub_text(c.get("body"), me)
        elif name == "paused_until.json":
            data["why"] = scrub_text(data.get("why"), me)
        text = json.dumps(data, ensure_ascii=False, indent=1)
        if me and me in text:
            text = text.replace(me, "[บัญชีเรา]")
        with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(text + "\n")
        print("คัดลอกแล้ว:", name)
    log_dir = os.path.join(SRC, "logs")
    for name in sorted(os.listdir(log_dir)) if os.path.isdir(log_dir) else []:
        if not name.endswith(".log"):
            continue  # ไม่เอาภาพหน้าจอคำเตือน
        with open(os.path.join(log_dir, name), encoding="utf-8", errors="replace") as f:
            lines = [scrub_log_line(x, me) for x in f]
        with open(os.path.join(OUT, "logs", name), "w", encoding="utf-8", newline="\n") as f:
            f.writelines(lines)
        print("คัดลอกแล้ว: logs/" + name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
