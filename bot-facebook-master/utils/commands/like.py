
from selenium.webdriver.common.by import By # type: ignore

from utils.commands.is_displayed import is_displayed

import time
import random
def like(driver):
    try:
        like_buttons = driver.find_elements(By.XPATH, '//span[@data-ad-rendering-role="ถูกใจ_button" and not(@style)]')
        for button in like_buttons:
            if is_displayed(driver, button):
                button.click()
                time.sleep(1)
                print("Successfully liked the post")
                break
    except Exception:
        print("Error occurred while liking the post")

def random_like(driver):
    if random.random() < 0.3:  # 30% chance to call like()
        like(driver)
