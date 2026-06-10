import os
import time
from playwright.sync_api import sync_playwright

artifact_dir = r"C:\Users\Admin\.gemini\antigravity-ide\brain\a95a9045-a9a4-42be-8c38-ba406b40da3d"

def select_option_with_wait(page, locator_str, match_str, default_val):
    select_el = page.locator(locator_str).first
    # Wait until options length is > 1 (i.e. has more than just the placeholder)
    print(f"Waiting for select options to load for: {locator_str}")
    for _ in range(30):
        opts = [o.strip() for o in select_el.locator('option').all_inner_texts() if o.strip()]
        # Filter out placeholders like "Choose schema...", "Select..."
        real_opts = [o for o in opts if 'choose' not in o.lower() and 'select' not in o.lower()]
        if len(real_opts) >= 1:
            break
        time.sleep(1)
        
    opts = [o.strip() for o in select_el.locator('option').all_inner_texts() if o.strip()]
    print(f"Options found: {opts}")
    lbl = next((o for o in opts if o.lower() == match_str.lower() or match_str.lower() in o.lower()), default_val)
    print(f"Selecting option: {lbl}")
    select_el.select_option(label=lbl)

def run_test():
    with sync_playwright() as p:
        print("Launching Chromium in HEADED mode (headless=False) so you can see it and take control...")
        # Launch headed and with slow_mo to allow user interaction
        browser = p.chromium.launch(headless=False, slow_mo=800)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        
        # 1. Open Landing Page
        print("Navigating to UI at http://localhost:5173 ...")
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=os.path.join(artifact_dir, "01_landing_page.png"))
        
        # Click "Get Started"
        print("Entering Dashboard...")
        page.click('button:has-text("Get Started")')
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(artifact_dir, "02_dashboard.png"))
        
        # Click "New Pipeline"
        print("Entering Ingestion Wizard...")
        page.click('button:has-text("New Pipeline")')
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(artifact_dir, "03_wizard_credentials.png"))
        
        # Choose FULL Load
        print("Choosing FULL Load strategy...")
        page.click('button:has-text("Full Load")')
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(artifact_dir, "04_strategy_full.png"))
        
        # Click "Test & Continue"
        print("Testing Connection & Continuing...")
        page.click('button:has-text("Test & Continue")')
        
        # This will query schemas and transition to Step 2. Give it up to 20 seconds.
        page.wait_for_selector('text=Source Table Mapper', timeout=20000)
        page.screenshot(path=os.path.join(artifact_dir, "05_table_selection.png"))
        
        # Step 2: Selection (Full Load)
        print("Selecting Schema: production...")
        select_option_with_wait(page, 'div:has(label:has-text("Select Schema")) select', 'production', 'production')
        page.wait_for_timeout(3000)
        page.screenshot(path=os.path.join(artifact_dir, "06_schema_selected.png"))
        
        # Click table 'brands'
        print("Selecting table: brands...")
        page.click('label:has-text("brands")')
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(artifact_dir, "07_brands_selected.png"))
        
        # Click "Start Full Load Migration"
        print("Starting Full Load Migration...")
        page.click('button:has-text("Start Full Load Migration")')
        page.wait_for_timeout(5000)
        page.screenshot(path=os.path.join(artifact_dir, "08_full_load_execution.png"))
        
        # Wait for the status progress to reach 100% / COMPLETED
        print("Polling Full Load progress...")
        completed = False
        for i in range(40):
            badge = page.locator('div.rounded-full.border.text-\\[11px\\]').first
            status_text = badge.inner_text().strip() if badge.count() > 0 else ""
            print(f"Current status: {status_text}")
            if "COMPLETED" in status_text.upper():
                print("Full Load Completed!")
                completed = True
                break
            if "FAILED" in status_text.upper():
                print("Full Load Failed!")
                break
            time.sleep(3)
        
        if not completed:
            print("Full Load polling timed out or failed.")
            
        page.screenshot(path=os.path.join(artifact_dir, "09_full_load_completed.png"))
        
        # Now click "View Dashboard"
        print("Returning to Dashboard...")
        page.click('button:has-text("View Dashboard")')
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(artifact_dir, "10_dashboard_with_history.png"))
        
        # -------------------------------------------------------------
        # Part 2: Incremental Load
        # -------------------------------------------------------------
        # Click "New Pipeline"
        print("Starting Incremental Load setup...")
        page.click('button:has-text("New Pipeline")')
        page.wait_for_timeout(2000)
        
        # Choose Incremental Load strategy
        print("Choosing INCREMENTAL Load strategy...")
        page.click('button:has-text("Incremental Load")')
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(artifact_dir, "11_strategy_incremental.png"))
        
        # Click "Test & Continue"
        print("Testing Connection & Continuing...")
        page.click('button:has-text("Test & Continue")')
        
        # Wait for Step 2
        page.wait_for_selector('text=Resource Selection', timeout=20000)
        page.screenshot(path=os.path.join(artifact_dir, "12_selection_incremental.png"))
        
        # Select schemas
        print("Selecting schemas...")
        select_option_with_wait(page, 'div:has(label:has-text("Source Schema")) select', 'production', 'production')
        page.wait_for_timeout(2000)
        select_option_with_wait(page, 'div:has(label:has-text("Target Schema")) select', 'production', 'PRODUCTION')
        page.wait_for_timeout(3000)
        page.screenshot(path=os.path.join(artifact_dir, "13_schemas_selected_incremental.png"))
        
        # Select table pairing
        print("Selecting table pairing (brands -> brands)...")
        select_option_with_wait(page, 'div:has(label:has-text("Source Table")) select', 'brands', 'brands')
        page.wait_for_timeout(1000)
        select_option_with_wait(page, 'div:has(label:has-text("Target Table")) select', 'brands', 'BRANDS')
        page.wait_for_timeout(1000)
        
        # Click "Add Pairing"
        print("Clicking Add Pairing...")
        page.click('button:has-text("Add Pairing")')
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(artifact_dir, "14_pairing_added.png"))
        
        # Click "Configure Mappings"
        print("Clicking Configure Mappings...")
        page.click('button:has-text("Configure Mappings")')
        page.wait_for_selector('text=Column Mapping System', timeout=20000)
        page.screenshot(path=os.path.join(artifact_dir, "15_column_mapping.png"))
        
        # Select watermark column
        print("Selecting Watermark column: LastModifiedDate...")
        select_option_with_wait(page, 'div:has(label:has-text("Source Watermark Column")) select', 'LastModifiedDate', 'LastModifiedDate')
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(artifact_dir, "16_watermark_set.png"))
        
        # Click "Execute Pipeline"
        print("Executing Incremental Pipeline...")
        page.click('button:has-text("Execute Pipeline")')
        page.wait_for_timeout(5000)
        page.screenshot(path=os.path.join(artifact_dir, "17_incremental_execution.png"))
        
        # Wait for the status progress to reach 100% / COMPLETED
        print("Polling Incremental progress...")
        completed = False
        for i in range(40):
            badge = page.locator('div.rounded-full.border.text-\\[11px\\]').first
            status_text = badge.inner_text().strip() if badge.count() > 0 else ""
            print(f"Current status: {status_text}")
            if "COMPLETED" in status_text.upper():
                print("Incremental Load Completed!")
                completed = True
                break
            if "FAILED" in status_text.upper():
                print("Incremental Load Failed!")
                break
            time.sleep(3)
            
        if not completed:
            print("Incremental Load polling timed out or failed.")
            
        page.screenshot(path=os.path.join(artifact_dir, "18_incremental_completed.png"))
        
        # Click "View Dashboard"
        print("Viewing final Dashboard...")
        page.click('button:has-text("View Dashboard")')
        page.wait_for_timeout(5000)  # Keep browser open a bit so user can see dashboard
        page.screenshot(path=os.path.join(artifact_dir, "19_final_dashboard.png"))
        
        browser.close()
        print("Test completed successfully.")

if __name__ == "__main__":
    run_test()
