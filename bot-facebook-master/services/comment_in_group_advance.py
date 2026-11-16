from selenium.webdriver.common.by import By # type: ignore
from selenium.webdriver.common.keys import Keys # type: ignore
from selenium.webdriver.common.action_chains import ActionChains # type: ignore

from services.excel import read_comment_in_group_advance_sheet, has_value, cell_text, cell_int, pick_variant
from utils.commands.image import upload_image
from utils.commands.scroll import scroll_post
import time
import hashlib
import random


seen_posts = set()


def xpath_literal(text):
    """ทำข้อความให้ใส่ใน XPath ได้ แม้มีเครื่องหมาย ' หรือ \""""
    if '"' not in text:
        return f'"{text}"'
    if "'" not in text:
        return f"'{text}'"
    parts = text.split('"')
    return "concat(" + ", '\"', ".join(f'"{p}"' for p in parts) + ")"


def split_words(value):
    return [w.strip() for w in cell_text(value).split(',') if w.strip()]


def build_post_xpath(keywords, exclude_keywords):
    # กำหนดพื้นที่ค้นหาโพสต์ (รวม 2 เงื่อนไข)
    base_xpath = (
        '//div[contains(@data-ad-comet-preview, "message")] '
        '| '
        '//div[contains(@class, "x6s0dn4") and contains(@class, "x78zum5") and contains(@class, "xdt5ytf") and contains(@class, "x5yr21d") and contains(@class, "xl56j7k") and contains(@class, "x10l6tqk") and contains(@class, "x17qophe") and contains(@class, "x13vifvy") and contains(@class, "xh8yej3")]'
    )

    # ค้นหาเฉพาะโพสต์ที่มีคำที่ต้องการ (ไม่ใส่คำ = เอาทุกโพสต์)
    keywords_condition = " or ".join(
        f'contains(string(.), {xpath_literal(kw)})' for kw in keywords
    ) or "true()"

    # กรองโพสต์ที่มีคำที่ไม่ต้องการ
    exclude_condition = " and ".join(
        f'not(contains(string(.), {xpath_literal(kw)}))' for kw in exclude_keywords
    ) or "true()"

    # ไม่เอาโพสต์ที่มี emoji
    exclude_icons = "not(descendant::img[contains(@src, 'emoji.php')])"

    # ไม่เอาโพสต์ที่มีปุ่ม "ดูเพิ่มเติม"
    exclude_view_more = 'not(descendant::div[@role="button" and text()="ดูเพิ่มเติม"])'

    # ไม่เอาโพสต์ที่มีลิงก์ https://
    exclude_https = "not(contains(string(.), 'https://'))"

    # ไม่เอาโพสต์ที่อยู่ภายใต้ div[@class='html-div x11i5rnm xat24cr ...']
    exclude_under_html_div = "not(ancestor::div[@class='html-div x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd x1y332i5'])"

    return (
        f"({base_xpath})[({keywords_condition}) and ({exclude_condition}) and ({exclude_icons}) "
        f"and ({exclude_view_more}) and ({exclude_https}) and ({exclude_under_html_div})]"
    )


def comment_on_post(driver, post, comment, image):
    """คอมเมนต์โพสต์นี้ คืนค่า True ถ้าคอมเมนต์แล้ว, False ถ้าข้ามโพสต์"""
    if not post.text.strip():
        return False
    post_hash = hashlib.sha256(post.text.encode('utf-8')).hexdigest()

    # ถ้าโพสต์นี้เคยเจอมาก่อนแล้ว (เช็คจาก hash)
    if post_hash in seen_posts:
        return False

    containers = post.find_elements(By.XPATH, 'ancestor::div[@role="article" and @class="x1a2a7pz"]')
    if not containers:
        return False
    aria_describedby = containers[0].get_attribute("aria-describedby")
    if not aria_describedby:
        return False
    print(f"Find Post aria-describedby: {aria_describedby}")
    post_scope = f"//div[contains(normalize-space(@aria-describedby), {xpath_literal(aria_describedby)})]"

    # ข้ามโพสต์ที่มีภาพ
    if driver.find_elements(By.XPATH, f"{post_scope}//div[contains(@class, 'x6s0dn4 x1jx94hy x78zum5 xdt5ytf x6ikm8r x10wlt62 x1n2onr6 xh8yej3')]"):
        return False
    if driver.find_elements(By.XPATH, f"{post_scope}//div[@class='html-div x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd x1y332i5']"):
        return False

    # เพิ่ม hash ของโพสต์ลงในเซต
    seen_posts.add(post_hash)
    y_offset = post.location["y"] - 100  # ขยับขึ้นไปอีก 100px เพื่อให้เห็นโพสต์ชัดขึ้น
    driver.execute_script(f"window.scrollTo(0, {y_offset});")
    time.sleep(5)

    comment_button = driver.find_element(By.XPATH, f'{post_scope}//span[@data-ad-rendering-role="comment_button"]')
    time.sleep(1)
    comment_button.click()
    time.sleep(20)

    actions = ActionChains(driver)
    sub_images = cell_text(image).split("||") if has_value(image) else []

    lines = comment.split("||")
    for i, line in enumerate(lines):
        if i < len(sub_images):
            upload_image(driver, sub_images[i])
        # แยกแต่ละบรรทัดในแต่ละส่วนด้วย '\n'
        sub_lines = line.split("\\n")
        for sub_line in sub_lines:
            actions.send_keys(sub_line)
            actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT)
        time.sleep(random.uniform(3, 10))
        # ส่ง RETURN (Enter) เพื่อส่งคอมเมนต์
        actions.send_keys(Keys.RETURN).perform()
        print("comment success")
        time.sleep(random.uniform(3, 10))
    actions.send_keys(Keys.ESCAPE).perform()
    return True


def start_comment_in_group_advance(driver):
    print("Commenting in the group...")
    try:
        df_comment_in_group = read_comment_in_group_advance_sheet()
    except Exception as e:
        print(f"Error occurred: {e}")
        return

    for _, row in df_comment_in_group.iterrows():
        link = cell_text(row['ลิงค์กลุ่ม']).rstrip('/')
        if not link:
            continue
        try:
            comment = pick_variant(cell_text(row['คอมเมนต์']))
            image = row['รูปภาพ']
            count = cell_int(row['จำนวนครั้งในการหาโพสต์'])
            keywords = split_words(row['คำที่ต้องกาาค้นหา'])
            exclude_keywords = split_words(row['คำที่ไม่ต้องการ'])
            xpath_query = build_post_xpath(keywords, exclude_keywords)

            driver.get(f"{link}/?sorting_setting=CHRONOLOGICAL")
            time.sleep(10)

            for _ in range(count):
                scroll_post(driver)
                time.sleep(5)  # รอให้โหลดข้อมูลเพิ่ม

                # ค้นหาโพสต์ที่ตรงตามเงื่อนไข
                posts = driver.find_elements(By.XPATH, xpath_query)

                for post in posts:
                    try:
                        if comment_on_post(driver, post, comment, image):
                            break
                    except Exception as e:
                        print(f"Could not find the 'Comment' button or unable to click: {e}")
                        time.sleep(random.uniform(1, 10))  # รอเวลาที่สุ่ม

            time.sleep(5)
        except Exception as e:
            print(f"Error occurred ({link}): {e}")
