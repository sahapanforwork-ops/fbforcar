"""กติกาเลือกโพสต์ที่จะคอมเมนต์ (ใช้ตอนบอททำงานเองอัตโนมัติ ไม่มีคนช่วยดู)

ตั้งใจให้เข้มไว้ก่อน: ยอมพลาดคนหารถบางคน ดีกว่าไปคอมเมนต์ใต้โฆษณาของร้านอื่น
ปรับตามที่เจ้าของรถเลือกเองจริงเมื่อ 16 พ.ย. 2569
"""
import re

# คนกำลังหารถ
SEEK = re.compile(r"หาเช่า|หารถ|อยากเช่า|ต้องการเช่า|ต้องการรถ|ตามหารถ|ใครมีรถ|มีใครปล่อย|ใครปล่อยเช่า|หาเจ้าของรถ|ขอเช่า|รบกวนหารถ|อยากได้รถเช่า")

# โพสต์ของร้าน/เต็นท์รถ (ไม่คอมเมนต์ใต้โฆษณาของคนอื่น)
SHOP = re.compile(
    r"(?<!ใครมี)รถว่าง|พร้อมให้บริการ|ยินดีให้บริการ|บริการรถ|ราคาเริ่ม|เริ่มต้น(เพียง|ที่)?\s*\d|สนใจทัก|สนใจติดต่อ|"
    r"line\s*(id)?\s*[:@]|ไลน์\s*[:@]|รหัสผู้ประกอบการ|\bMN\s*-?\s*\d|A-JT|ส่งฟรี|รับส่งฟรี|ส่งรถถึงที่|"
    r"ใครกำลัง(มอง)?หา|ใครที่กำลัง(มอง)?หา|ป้ายขาว|ป้ายแดง|ออกรถ|ดาวน์|ผ่อน|เงินจอง|ฝากร้าน|โปรโมชั่น|"
    r"\d{2,3}[- ]?\d{3}[- ]?\d{4}|เรามีรถ|มีรถให้เลือก|ปล่อยเช่า(?!.{0,6}(ไหม|มั้ย|บ้าง|\?))",
    re.I)

# รถที่ไม่ใช่แบบเรา (เรามี BYD Dolphin รถเล็ก 5 ที่นั่ง ขับเอง)
WRONG_CAR = re.compile(
    r"7\s*ที่|เจ็ดที่|[89]\s*ที่|1[0-5]\s*ที่|รถตู้|ตู้\s*vip|กระบะ|กะบะ|pick\s*-?up|\bvan\b|มอเตอร์ไซ|มอไซ|จักรยานยนต์|"
    r"xpander|fortuner|pajero|alphard|staria|\bh-?1\b|innova|veloz|xl7|cr-?v|everest|bmw|benz|เบนซ์|mercedes|"
    r"porsche|lexus|volvo|camry|harrier|mustang|sienta|ไฮบริด|hybrid|ดีเซล|ไม่เอา(รถ)?(ไฟฟ้า|ev)|"
    r"เฉพาะ(รถ)?(น้ำมัน|เบนซิน)|พร้อมคนขับ|มีคนขับ|เหมารถ",
    re.I)

# รับรถไกลจากกรุงเทพฯ และปริมณฑล (ไปเที่ยวต่างจังหวัดได้ แต่รับรถต้องอยู่แถว กทม.)
FAR = ("เชียงใหม่|เชียงราย|ภูเก็ต|กระบี่|ขอนแก่น|อุดร|โคราช|นครราชสีมา|หาดใหญ่|สงขลา|ระยอง|พัทยา|ชลบุรี|ศรีราชา|"
       "หัวหิน|อยุธยา|สุราษ|พิษณุโลก|นครสวรรค์|อุบล|ลำปาง|แม่สอด|สกลนคร|นครพนม|เพชรบูรณ์|ลพบุรี|สระบุรี|"
       "ราชบุรี|กาญจนบุรี|ฉะเชิงเทรา|ปราจีน|จันทบุรี|ตราด|บุรีรัมย์|สุรินทร์|ศรีสะเกษ|ร้อยเอ็ด|มหาสารคาม|เลย|น่าน|แพร่")
FAR_PICKUP = re.compile(rf"(รับรถ|รับที่|พิกัด|อยู่|แถว|สนามบิน)\s*(ที่|แถว|จ\.|จังหวัด)?\s*({FAR})")

# เช่ารายเดือนแค่ 1-5 เดือน (รายเดือนของเราสัญญาขั้นต่ำ 6 เดือน)
SHORT_MONTHS = re.compile(r"(?<![\d,.])([1-5]|หนึ่ง|สอง|สาม|สี่|ห้า)\s*เดือน(?!หน้า)|เดือนนึง|เดือนเดียว")

# โพสต์ภายใน 24 ชม.
RECENT = re.compile(r"เมื่อสักครู่|\d+\s*(นาที|ชั่วโมง|ชม\.)")

NUMBER = re.compile(r"\d{1,3}(?:,\d{3})+|\d+")
DAILY_MAX_TOO_LOW = 900      # งบต่อวันไม่เกินนี้ ห่างจาก 1,300 เกินไป
MONTHLY_MAX_TOO_LOW = 20000  # งบต่อเดือนไม่เกินนี้ ห่างจาก 24,000 เกินไป


def budget_too_low(text):
    """อ่านงบจากข้อความ เช่น 'วันละ 700-800', '15,000/เดือน' คืนค่าเหตุผล หรือ None"""
    daily, monthly = [], []
    for m in NUMBER.finditer(text):
        n = int(m.group().replace(",", ""))
        before, after = text[max(0, m.start() - 20):m.start()], text[m.end():m.end() + 12]
        if re.search(r"ปี\s*$|ค\.?ศ|พ\.?ศ", before) or re.match(r"\s*(กม|km|กิโล|โล|คน|ที่|ชม|นาที|%)", after):
            continue
        near = before + " " + after
        if "เดือน" in near and n >= 3000:
            monthly.append(n)
        elif re.search(r"วัน|บาท|งบ|ราคา|฿", near) and 100 <= n < 3000:
            daily.append(n)
    if daily and max(daily) <= DAILY_MAX_TOO_LOW:
        return f"งบต่อวัน {max(daily)}"
    if monthly and max(monthly) <= MONTHLY_MAX_TOO_LOW:
        return f"งบต่อเดือน {max(monthly):,}"
    return None


def post_body(text):
    """ตัดหัวโพสต์ (ชื่อคน เวลา วันที่) และท้ายโพสต์ (ช่องคอมเมนต์ ยอดไลก์) ออก เหลือแต่ข้อความ"""
    text = re.sub(r"\s+", " ", text or "")
    heads = list(re.finditer(r"(นาที|ชั่วโมง|ชม\.?|วัน|เมื่อวาน|เมื่อสักครู่)\s*·\s*", text[:350]))
    if heads:
        text = text[heads[-1].end():]
    return re.split(r"แสดงความคิดเห็นในชื่อ|ดูเพิ่มเติม", text)[0].strip()


def judge(card_text, images=0, message=None):
    """คืนค่า (ควรคอมเมนต์ไหม, เหตุผล) จากข้อความทั้งการ์ดโพสต์ (message = เนื้อโพสต์อย่างเดียว ถ้าอ่านแยกได้)"""
    raw = re.sub(r"\s+", " ", card_text or "")
    body = re.sub(r"\s+", " ", message).strip() if message else post_body(raw)
    if "BYD Dolphin" in raw or "IMP CarRent" in raw:
        return False, "โพสต์ของเรา"
    if not RECENT.search(raw[:250]):
        return False, "เก่ากว่า 1 วัน"
    if not SEEK.search(body):
        return False, "ไม่ใช่คนหารถ"
    if SHOP.search(body) or len(body) > 350 or images >= 3:
        return False, "โฆษณาของร้าน/เต็นท์รถ"
    for rule, why in ((WRONG_CAR, "รถคนละแบบ"), (FAR_PICKUP, "รับรถไกลจาก กทม."), (SHORT_MONTHS, "รายเดือนสั้นกว่า 6 เดือน")):
        m = rule.search(body)
        if m:
            return False, f"{why} ({m.group(0)})"
    low = budget_too_low(body)
    if low:
        return False, low
    return True, "คนหารถ เข้าเงื่อนไข"
