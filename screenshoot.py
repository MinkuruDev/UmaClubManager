import os

from time import sleep
from typing import Optional
from cloakbrowser import launch

def take_screenshot(yyyymm: str) -> Optional[str]:
    """
    Take a screenshot of the fan progress report page for the specified month and save it as a PNG file.
    The function launches a headless browser, navigates to the local URL of the fan report, 
    and captures a screenshot of the relevant section of the page. 
    The screenshot is saved in the "Screenshots" directory with the filename format "YYYYMM.png".
    Args:
        yyyymm (str): The month for which to take the screenshot, in the format "YYYYMM".
    Returns:
        Optional[str]: The path to the saved screenshot if successful, otherwise None.
    """
    url = f"localhost:5000/fans?month={yyyymm}"
    try:
        browser = launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        sleep(2)
        os.makedirs("Screenshots", exist_ok=True)
        page.locator(".table-container.glass-panel").screenshot(path=f"Screenshots/{yyyymm}.png")
        return f"Screenshots/{yyyymm}.png"
    except Exception as e:
        print(f"Error taking screenshot: {e}")
        return None

if __name__ == "__main__":
    take_screenshot("202605")
