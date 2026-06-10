import os
import time
from playwright.sync_api import sync_playwright

def select_option_with_wait(page, locator_str, match_str, default_val):
    print(f"Selecting option in '{locator_str}' matching '{match_str}' (default: '{default_val}')...")
    select_el = page.locator(locator_str).first
    select_el.wait_for(state="visible", timeout=20000)
    
    # Wait until options are loaded from the database (meaning more than just the placeholder)
    for _ in range(15):
        opts = [o.strip() for o in select_el.locator('option').all_inner_texts() if o.strip()]
        real_opts = [o for o in opts if 'choose' not in o.lower() and 'select' not in o.lower()]
        if len(real_opts) >= 1:
            break
        time.sleep(1)
        
    opts = [o.strip() for o in select_el.locator('option').all_inner_texts() if o.strip()]
    print(f"Found options: {opts}")
    lbl = next((o for o in opts if o.lower() == match_str.lower() or match_str.lower() in o.lower()), None)
    if not lbl:
        lbl = next((o for o in opts if o.strip()), default_val)
    print(f"Selected: '{lbl}'")
    select_el.select_option(label=lbl)

def run_control():
    print("Connecting to the headed Chrome instance on port 9222...")
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Ensure we are on the landing page/dashboard
        print("Navigating to http://localhost:5173 to start fresh...")
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        # If we are on the landing page, click Get Started
        if len(page.locator('button:has-text("Get Started")').all()) > 0:
            print("Clicking 'Get Started'...")
            page.click('button:has-text("Get Started")')
            time.sleep(2)
            
        # -------------------------------------------------------------
        # STEP 1: Full Load Setup
        # -------------------------------------------------------------
        print("Clicking 'New Pipeline'...")
        page.locator('button:has-text("New Pipeline")').first.click()
        time.sleep(2)
        
        print("Choosing 'Full Load' strategy...")
        page.click('button:has-text("Full Load")')
        time.sleep(1)
        
        print("Clicking 'Test & Continue'...")
        page.click('button:has-text("Test & Continue")')
        
        # Wait for Step 2 Table Selection to load
        print("Waiting for Table Selection step...")
        page.wait_for_selector('text=Source Table Mapper', timeout=20000)
        time.sleep(2)
        
        print("Selecting Schema: production...")
        select_option_with_wait(page, 'label:has-text("Select Schema") + div select', 'production', 'production')
        time.sleep(3)
        
        # Select brands table checkmark
        print("Selecting table: brands...")
        page.locator('label:has-text("brands")').first.click()
        time.sleep(1)
        
        # Click Start Full Load
        print("Clicking 'Start Full Load Migration'...")
        page.click('button:has-text("Start Full Load Migration")')
        time.sleep(3)
        
        # Poll Full Load Ingestion progress
        print("Polling Full Load progress...")
        for _ in range(40):
            badge = page.locator('div.rounded-full.border.text-\\[11px\\]').first
            status_text = badge.inner_text().strip() if badge.count() > 0 else "UNKNOWN"
            print(f"Current status: {status_text}")
            if "COMPLETED" in status_text.upper():
                print("Full Load Completed successfully!")
                break
            if "FAILED" in status_text.upper():
                print("Full Load Failed!")
                break
            time.sleep(2)
            
        print("Returning to Dashboard...")
        page.click('button:has-text("View Dashboard")')
        time.sleep(3)
        
        # -------------------------------------------------------------
        # STEP 2: Incremental Load Setup
        # -------------------------------------------------------------
        print("Clicking 'New Pipeline' for Incremental Load...")
        page.locator('button:has-text("New Pipeline")').first.click()
        time.sleep(2)
        
        print("Choosing 'Incremental Load' strategy...")
        page.click('button:has-text("Incremental Load")')
        time.sleep(1)
        
        print("Clicking 'Test & Continue'...")
        page.click('button:has-text("Test & Continue")')
        
        # Wait for Selection Step
        print("Waiting for Resource Selection step...")
        page.wait_for_selector('text=Resource Selection', timeout=20000)
        time.sleep(2)
        
        # Select schemas
        print("Selecting Source Schema...")
        select_option_with_wait(page, 'label:has-text("Source Schema") + div select', 'production', 'production')
        time.sleep(2)
        
        print("Selecting Target Schema...")
        select_option_with_wait(page, 'label:has-text("Target Schema") + div select', 'production', 'PRODUCTION')
        time.sleep(3)
        
        # Select table pairing
        print("Selecting Source Table...")
        select_option_with_wait(page, 'label:has-text("Source Table") + div select', 'brands', 'brands')
        time.sleep(1)
        
        print("Selecting Target Table...")
        select_option_with_wait(page, 'label:has-text("Target Table") + div select', 'brands', 'BRANDS')
        time.sleep(1)
        
        print("Clicking 'Add Pairing'...")
        page.click('button:has-text("Add Pairing")')
        time.sleep(2)
        
        print("Clicking 'Configure Mappings'...")
        page.click('button:has-text("Configure Mappings")')
        
        # Wait for Step 3 Mapping
        print("Waiting for Mapping step...")
        page.wait_for_selector('text=Column Mapping System', timeout=20000)
        time.sleep(2)
        
        # Select watermark column
        print("Selecting Watermark column: LastModifiedDate...")
        select_option_with_wait(page, 'label:has-text("Source Watermark Column") + div select', 'LastModifiedDate', 'LastModifiedDate')
        time.sleep(2)
        
        # Click Execute Pipeline
        print("Clicking 'Execute Pipeline'...")
        page.click('button:has-text("Execute Pipeline")')
        time.sleep(3)
        
        # Poll Incremental Ingestion progress
        print("Polling Incremental progress...")
        for _ in range(40):
            badge = page.locator('div.rounded-full.border.text-\\[11px\\]').first
            status_text = badge.inner_text().strip() if badge.count() > 0 else "UNKNOWN"
            print(f"Current Status: {status_text}")
            if "COMPLETED" in status_text.upper():
                print("Incremental Load Completed successfully!")
                break
            if "FAILED" in status_text.upper():
                print("Incremental Load Failed!")
                break
            time.sleep(2)
            
        print("Returning to Dashboard...")
        page.click('button:has-text("View Dashboard")')
        time.sleep(3)
        
        print("Interactive Control flow finished successfully!")

if __name__ == "__main__":
    run_control()
