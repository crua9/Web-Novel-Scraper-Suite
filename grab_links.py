print("...script is starting...")

# It's good practice to put all imports inside a try...except block
# to provide clear error messages if a required library is missing.
try:
    from playwright.sync_api import sync_playwright, TimeoutError
    import math
    import sys
    import os
    import json
except ImportError as e:
    print("\n" + "="*60)
    print("❌ ERROR: A REQUIRED LIBRARY IS MISSING.")
    print(f"   Details: {e}")
    print("\n   It looks like 'playwright' is not installed correctly.")
    print("   Please run the following two commands in your terminal:")
    print("\n   1. pip install playwright")
    print("   2. playwright install")
    print("\n" + "="*60)
    input("\nPress Enter to exit.")
    sys.exit()

def get_all_chapter_links(story_url):
    """
    Launches a browser, navigates to the story URL, finds all chapters,
    and scrapes the link for each one. Supports ScribbleHub and Royal Road.
    """
    print("🌐 Launching browser...")
    with sync_playwright() as p:
        # Using a try...finally block ensures the browser is closed even if errors occur.
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        urls = []

        try:
            print(f"📄 Loading story page: {story_url}")
            page.goto(story_url, timeout=60000)

            # --- Site-Specific Logic ---
            if "scribblehub.com" in story_url:
                print("🔷 ScribbleHub Detected. Looking for all chapters...")
                
                try:
                    page.get_by_role("button", name="Got it!").click(timeout=5000)
                    print("✅ Cookie consent accepted.")
                except TimeoutError:
                    print("👍 No cookie consent banner found.")
                
                page.wait_for_selector(".toc_ol", timeout=30000)
                page.get_by_title("Show All Chapters").click()
                
                print("⏳ Waiting for all chapters to load... (this might take a minute)")
                page.wait_for_selector("#pagination-mesh-toc", state="hidden", timeout=120000)
                print("✅ TOC fully loaded.")

                links = page.query_selector_all(".toc_ol .toc_a")
                for link in links:
                    href = link.get_attribute("href")
                    if href:
                        urls.append(href.strip())
                
                print("🔃 Reversing chapter order to chronological for ScribbleHub...")
                urls.reverse()

            elif "royalroad.com" in story_url:
                print("🔷 Royal Road Detected. Looking for all chapters...")
                base_url = "https://www.royalroad.com"

                page.wait_for_selector("#chapters", timeout=30000)
                print("✅ Chapter table found. Attempting to extract data directly...")

                # Royal Road embeds all chapter data in a JavaScript variable.
                # This is faster and more reliable than waiting for the page to render all rows.
                chapters_data = page.evaluate("() => window.chapters")

                if chapters_data and isinstance(chapters_data, list):
                    print(f"✅ Extracted data for {len(chapters_data)} chapters from the page script.")
                    for chapter in chapters_data:
                        if chapter.get('url'):
                            urls.append(base_url + chapter['url'])
                else:
                    # Fallback method in case the JavaScript variable is not found
                    print("⚠️ Could not find embedded script data. Scraping visible table rows as a fallback.")
                    links = page.query_selector_all("#chapters tbody tr.chapter-row a")
                    for link in links:
                        href = link.get_attribute("href")
                        if href:
                            # Royal Road links are already chronological, and relative
                            urls.append(base_url + href.strip())
            
            else:
                print(f"❌ Unsupported URL: {story_url}")
                return []

        except TimeoutError as e:
            print(f"\n❌ Timed out waiting for an element: {e}")
            print("   This can happen with large stories or slow connections.")
            return []
        except Exception as e:
            print(f"❌ An error occurred during scraping: {e}")
            page.screenshot(path="debug_screenshot.png")
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            print("📸 Saved debug_screenshot.png and debug_page.html for inspection.")
            return []
        finally:
            if 'browser' in locals() and browser.is_connected():
                browser.close()
                print("✅ Browser closed.")

        print(f"✅ Found {len(urls)} chapter links.")
        return urls

def save_chunks(urls, base_name, chunk_size):
    if not urls:
        return
        
    output_dir = "links"
    if not os.path.exists(output_dir):
        print(f"📁 Creating subdirectory: {output_dir}")
        os.makedirs(output_dir)
        
    total = len(urls)
    chunks = math.ceil(total / chunk_size)
    print(f"\n📦 Splitting into {chunks} file(s)...")

    for i in range(chunks):
        start_index = i * chunk_size
        end_index = min(start_index + chunk_size, total)
        chunk_data = urls[start_index:end_index]
        start_chap = start_index + 1
        end_chap = end_index
        filename = os.path.join(output_dir, f"{base_name} {start_chap}-{end_chap}.txt")

        try:
            with open(filename, "w", encoding="utf-8") as f:
                for url in chunk_data:
                    f.write(url + "\n")
            print(f"✅ Saved chapters {start_chap}–{end_chap} to {filename}")
        except Exception as e:
            print(f"❌ Failed to save {filename}: {e}")

def main():
    print("\n📘 Chapter Link Grabber")
    story_url = input("🔗 Enter story URL (ScribbleHub or Royal Road): ").strip()

    if not ("scribblehub.com/series/" in story_url or "royalroad.com/fiction/" in story_url):
        print("⚠️ Invalid URL. Must be a ScribbleHub series page or a Royal Road fiction page.")
        return

    base_name = input("📝 What should the output files be named? (e.g. World Keeper Links): ").strip()
    if not base_name:
        print("⚠️ File name cannot be empty. Exiting.")
        return
        
    try:
        chunk_size_input = input("🔢 How many links per file? (e.g. 100): ").strip()
        chunk_size = int(chunk_size_input) if chunk_size_input else 100
    except ValueError:
        print("⚠️ Invalid number. Using default: 100")
        chunk_size = 100

    print("\n🚀 Starting scrape...")
    urls = get_all_chapter_links(story_url)
    if not urls:
        print("❌ No chapter links found. Exiting.")
        return

    save_chunks(urls, base_name, chunk_size)
    print(f"\n🎉 Done! Total chapters scraped: {len(urls)}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # This is a global catch-all to ensure any unexpected error is displayed.
        print("\n" + "="*60)
        print("💥 AN UNEXPECTED ERROR OCCURRED!")
        print(f"   Error Type: {type(e).__name__}")
        print(f"   Error Details: {e}")
        print("="*60)
    finally:
        # This ensures the user has time to read the error message before the window closes.
        input("\nPress Enter to exit.")