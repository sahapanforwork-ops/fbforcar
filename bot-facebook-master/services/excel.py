import math
import random
import re

import pandas as pd # type: ignore

file_path = "setting.xlsx"


def pick_variant(text):
    """ช่องข้อความใส่ได้หลายแบบ คั่นแต่ละแบบด้วยบรรทัดที่มีแค่ ---  โปรแกรมจะสุ่มใช้ 1 แบบทุกครั้ง
    (ข้อความเหมือนกันทุกโพสต์ Facebook จะมองว่าเป็นสแปม)"""
    parts = [p.strip() for p in re.split(r"(?m)^\s*-{3,}\s*$", text or "") if p.strip()]
    return random.choice(parts) if parts else (text or "")


def has_value(value):
    """True ถ้าช่องใน Excel มีค่าจริง (ไม่ว่าง ไม่ใช่ NaN และไม่ใช่ '-')"""
    if value is None:
        return False
    if isinstance(value, float) and math.isnan(value):
        return False
    text = str(value).strip()
    return text != "" and text != "-"


def cell_text(value, default=""):
    """แปลงค่าช่องเป็นข้อความ ช่องว่างจะได้ default"""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return default
    return str(value).strip()


def cell_int(value, default=0):
    """แปลงค่าช่องเป็นตัวเลข ช่องว่างหรือไม่ใช่ตัวเลขจะได้ default"""
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _read_sheet(sheet_name, required_columns):
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        raise ValueError(
            f"ชีต '{sheet_name}' ใน {file_path} ไม่มีคอลัมน์: {', '.join(missing)} "
            f"(คอลัมน์ที่มี: {', '.join(df.columns)})"
        )
    # ข้ามแถวที่ว่างทั้งแถว
    return df.dropna(how="all")


# อ่านไฟล์ Excel
def read_excel_file():
    return pd.read_excel(file_path, sheet_name=None, engine="openpyxl")

# ฟังก์ชันสำหรับการอ่านข้อมูลจากชีท "ค้นหาและคอมเมนต์"
def read_search_and_comment_sheet():
    return _read_sheet("ค้นหาและคอมเมนต์", ["หัวข้อ", "คอมเมนต์", "รูปภาพ", "จำนวนคอมเมนต์", "จำนวนครั้ง"])

# ฟังก์ชันสำหรับการอ่านข้อมูลจากชีท "คอมเมนต์ในกลุ่ม"
def read_comment_in_group_sheet():
    return _read_sheet("คอมเมนต์ในกลุ่ม", ["ลิงค์กลุ่ม", "คอมเมนต์", "รูปภาพ", "จำนวนคอมเมนต์", "จำนวนครั้ง"])

def read_comment_in_group_advance_sheet():
    return _read_sheet(
        "คอมเมนต์ในกลุ่มadvance",
        ["ลิงค์กลุ่ม", "คอมเมนต์", "รูปภาพ", "คำที่ต้องกาาค้นหา", "คำที่ไม่ต้องการ", "จำนวนครั้งในการหาโพสต์"],
    )

# ฟังก์ชันสำหรับการอ่านข้อมูลจากชีท "คอมเมนต์ในโพสต์"
def read_comment_in_post_sheet():
    return _read_sheet("คอมเมนต์ในโพสต์", ["ลิงค์โพสต์", "คอมเมนต์", "รูปภาพ"])

# ฟังก์ชันสำหรับการอ่านข้อมูลจากชีท "โพสต์ในกลุ่ม"
def read_post_in_group_sheet():
    return _read_sheet("โพสต์ในกลุ่ม", ["ลิงค์กลุ่ม", "คอมเมนต์", "รูปภาพ"])
