import time
from playwright.sync_api import sync_playwright

def main():
    print("Starting Playwright UI automation for data migration...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print("Navigating to frontend...")
        for i in range(15):
            try:
                page.goto("http://localhost:5173/login", timeout=10000)
                break
            except Exception as e:
                print(f"Waiting for frontend to be ready... ({i+1}/15)")
                time.sleep(2)
        else:
            raise Exception("Frontend server not reachable.")

        print("Logging in...")
        page.fill("input[type='email']", "admin@synthlake.ai")
        page.fill("input[type='password']", "password")
        page.click("button[type='submit']")

        page.wait_for_url("**/dashboard")
        print("Reached Dashboard.")

        print("Clicking New Migration...")
        page.click("button:has-text('New Migration')")
        
        page.wait_for_url("**/config")
        print("Reached Config Page.")

        print("Filling Source configuration...")
        source_section = page.locator("section:has-text('Source')")
        source_section.locator("select").select_option("sapsqlserver")
        source_section.locator("input[placeholder='server_name']").fill("192.168.68.62")
        source_section.locator("input[placeholder='port']").fill("1433")
        source_section.locator("input[placeholder='user']").fill("sa")
        source_section.locator("input[placeholder='password']").fill("India123")
        source_section.locator("input[placeholder='database']").fill("SampleDB")

        print("Filling Cloud configuration...")
        cloud_section = page.locator("section:has-text('Cloud')")
        cloud_section.locator("select").select_option("AWS")
        cloud_section.locator("input[placeholder='aws_region']").fill("eu-north-1")
        # Trigger blur or enter to ensure the custom combobox registers the value
        page.keyboard.press("Enter")
        cloud_section.locator("input[placeholder='aws_access_key_id']").fill("YOUR_AWS_ACCESS_KEY_ID")
        cloud_section.locator("input[placeholder='aws_secret_access_key']").fill("YOUR_AWS_SECRET_ACCESS_KEY")
        cloud_section.locator("input[placeholder='s3_bucket_name']").fill("stageddataparqe")

        print("Filling Target configuration...")
        target_section = page.locator("section:has-text('Target')")
        target_section.locator("select").select_option("snowflake")
        target_section.locator("input[placeholder='account']").fill("LFMGUZH-LWB53750")
        target_section.locator("input[placeholder='user']").fill("SAIADITHYA")
        target_section.locator("input[placeholder='password']").fill("Synthlake@2026")
        target_section.locator("input[placeholder='warehouse']").fill("COMPUTE_WH")
        target_section.locator("input[placeholder='database']").fill("SAMPLEDB")

        print("Saving configuration...")
        page.click("button:has-text('Save Configuration')")
        
        print("Waiting for Go To Source Mapper button...")
        page.wait_for_selector("button:has-text('Go To Source Mapper')", timeout=15000)
        page.click("button:has-text('Go To Source Mapper')")
        
        print("Reached Source Mapper.")
        page.wait_for_url("**/mapper")

        print("Waiting for metadata to sync...")
        page.wait_for_selector("select", state="attached", timeout=30000)
        time.sleep(2)
        
        print("Selecting Schema: Sales...")
        page.locator("select").select_option("Sales")

        print("Selecting Tables...")
        page.wait_for_selector("text=Select All")
        page.click("button:has-text('Select All')")

        print("Starting Migration...")
        page.click("button:has-text('Start Migration')")
        
        print("Waiting for Progress Page...")
        page.wait_for_url("**/progress")
        print("Reached Progress Page. Waiting for completion...")

        completed = False
        for i in range(120): # up to 4 minutes
            # Check if text "Pipeline completed successfully" exists
            if page.locator("text=Pipeline completed").count() > 0:
                print("Pipeline completed successfully detected!")
                completed = True
                break
            if page.locator("text=Pipeline failed").count() > 0 or page.locator("text=Migration failed").count() > 0:
                print("Pipeline failed detected!")
                break
            time.sleep(2)
            
        if not completed:
            print("Timeout or failure occurred during migration.")

        browser.close()
        print("Automation finished.")

if __name__ == "__main__":
    main()
