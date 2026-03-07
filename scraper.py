def get_all_chapter_links(story_url):
    """Launches Brave to scrape chapter links."""
    print("🌐 Launching Brave Browser...")
    urls = []
    
    # --- CONFIG: PATH TO BRAVE EXE ---
    # Update this if your Brave is installed somewhere else!
    BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

    if not os.path.exists(BRAVE_PATH):
        print(f"❌ Error: Could not find Brave at: {BRAVE_PATH}")
        print("Please check the path in the script and try again.")
        return []

    with sync_playwright() as p:
        # Create a folder to save cookies so you only solve CAPTCHA once
        user_data_dir = os.path.join(os.getcwd(), "brave_data")
        
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir, 
                executable_path=BRAVE_PATH, # <--- THIS USES BRAVE
                headless=False, # Must be False to solve Captcha
                args=[
                    "--disable-blink-features=AutomationControlled", # Hides "Robot" flag
                    "--no-sandbox"
                ]
            )
        except Exception as e:
            print(f"❌ Could not launch Brave. Is it open? Close all Brave windows and try again.\nError: {e}")
            return []

        page = context.pages[0] if context.pages else context.new_page()

        try:
            print(f"📄 Loading story page: {story_url}")
            page.goto(story_url, timeout=90000) # Increased timeout for CAPTCHA solving

            # --- CAPTCHA PAUSE ---
            if page.locator("text=Verify you are human").count() > 0 or "Just a moment" in page.title():
                print("\n⚠️  Cloudflare detected! Please solve the CAPTCHA in the Brave window.")
                print("⏳ Waiting for you to solve it...")
                try:
                    # Wait up to 5 minutes for you to solve it and the content to load
                    page.wait_for_selector(".toc_ol, #chapters", state="attached", timeout=300000)
                    print("✅ CAPTCHA solved/Bypassed.")
                except:
                    print("❌ Timed out waiting for CAPTCHA solution.")
            # ---------------------

            try:
                page.get_by_role("button", name="Got it!").click(timeout=5000)
            except TimeoutError:
                pass

            if "scribblehub.com" in story_url:
                page.wait_for_selector(".toc_ol", timeout=30000)
                urls = get_scribblehub_links(page)
            elif "royalroad.com" in story_url:
                page.wait_for_selector("#chapters", timeout=30000)
                urls = get_royalroad_links(page)
            
            if urls:
                print("🔃 Reversing chapter order to chronological...")
                urls.reverse()
        except TimeoutError:
            print("\n❌ Timed out waiting for the page to load.")
        except Exception as e:
            print(f"❌ An error occurred: {e}")
        finally:
            context.close() # Close the specific context, not the whole browser object
            print(f"✅ Found {len(urls)} chapter links.")
            return urls
