from playwright.sync_api import sync_playwright
import time

APPS = [
    "https://i-s-h-a-n-05-sentimentscope.streamlit.app/",
    "https://your-second-streamlit-app.streamlit.app/",  # replace with actual URL
]

def wake_app(page, url):
    print(f"Checking: {url}")
    page.goto(url, timeout=60000, wait_until="domcontentloaded")
    time.sleep(3)

    # Check if sleep page is showing
    try:
        wake_btn = page.locator("text=Yes, get this app back up!")
        if wake_btn.is_visible(timeout=4000):
            print(f"  → App is sleeping, clicking wake button...")
            wake_btn.click()
            time.sleep(20)  # Wait for app to boot
            print(f"  → Wake triggered.")
        else:
            print(f"  → App already awake.")
    except Exception as e:
        print(f"  → Could not find sleep button (app might be awake): {e}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    for url in APPS:
        page = context.new_page()
        try:
            wake_app(page, url)
        except Exception as e:
            print(f"Failed for {url}: {e}")
        finally:
            page.close()
    browser.close()
    print("Done.")