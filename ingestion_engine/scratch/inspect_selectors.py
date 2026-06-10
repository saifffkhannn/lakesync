from playwright.sync_api import sync_playwright

def inspect():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0]
        
        selectors = {
            "Source Schema": 'label:has-text("Source Schema") + div select',
            "Target Schema": 'label:has-text("Target Schema") + div select',
            "Source Table": 'label:has-text("Source Table") + div select',
            "Target Table": 'label:has-text("Target Table") + div select',
        }
        
        for name, sel in selectors.items():
            loc = page.locator(sel)
            if loc.count() > 0:
                opts = loc.locator('option').all_inner_texts()
                print(f"{name}: count={loc.count()}, options={opts[:10]}")
            else:
                print(f"{name}: not found with selector '{sel}'")

if __name__ == "__main__":
    inspect()
