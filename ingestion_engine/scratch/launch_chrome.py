import time
from playwright.sync_api import sync_playwright

def main():
    print("Launching Chromium headed with remote debugging on port 9222...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--remote-debugging-port=9222"],
        )
        # Using a default viewport
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        print("Navigating to http://localhost:5173...")
        page.goto("http://localhost:5173")
        
        print("Browser is open and listening on port 9222.")
        print("You can interact with it on the screen, or I can connect to it.")
        print("Keeping browser open. Process is running in background...")
        
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                break
        
        browser.close()

if __name__ == "__main__":
    main()
