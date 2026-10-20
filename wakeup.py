import os
import sys
from playwright.sync_api import sync_playwright

default_url = "https://panda-royal.streamlit.app/"
url = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PANDA_APP_URL", default_url)

print(f"Connecting to Streamlit App: {url}")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    try:
        page.goto(url, timeout=60000)
        button = page.locator("button:has-text('Yes, get this app back up')")
        button.wait_for(state="visible", timeout=30000)
        if button.is_visible():
            print("Sleep detected. Clicking 'Yes, get this app back up!'...")
            button.first.click()
            page.wait_for_timeout(30000)
            print("Successfully clicked wake-up button.")
        else:
            print("App is currently awake.")
    except Exception as e:
        print(f"App is already awake or sleep button not found: {e}")
        page.screenshot(path="wakeup_debug.png")
    finally:
        browser.close()
