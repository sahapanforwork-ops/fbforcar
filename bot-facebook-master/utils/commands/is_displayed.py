def is_displayed(driver, button):
    try:
        result = driver.execute_script('''
            const elem = arguments[0];
            const rect = elem.getBoundingClientRect();
            const inViewport = (
                rect.top >= 0 &&
                rect.left >= 0 &&
                rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                rect.right <= (window.innerWidth || document.documentElement.clientWidth)
            );

            const style = window.getComputedStyle(elem);
            const visible = style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';

            const hasSize = rect.width > 0 && rect.height > 0;

            const isNotCovered = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2) === elem;

            return inViewport && visible && hasSize && isNotCovered;
        ''', button)

        return result
    except Exception as e:
        print(f"An error occurred while checking the button's visibility: {e}")
        return False  # Return False if an error occurs
