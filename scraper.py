from playwright.sync_api import sync_playwright
import time
import sys
import os
import re

# --- User Input and Setup ---

# Confirm chapter_list.txt is ready
if not os.path.exists("chapter_list.txt"):
    print("\n❌ 'chapter_list.txt' not found!")
    print("Please create this file in the same folder as the script and fill it with chapter URLs, one per line.")
    sys.exit()

confirmation = input("\n🚀 Have you added URLs to 'chapter_list.txt'? (y/n): ").strip().lower()
if confirmation not in ["y", "yes"]:
    print("\n📄 Please add chapter URLs to 'chapter_list.txt' (one per line) and run the script again.")
    sys.exit()

# Ask for output filename
filename_input = input("\n📂 Enter output filename (e.g., World Keeper 300-400): ").strip()
# Ensure the filename ends with .txt, providing a default if none is given.
if not filename_input:
    output_file = "scraped_chapters.txt"
else:
    output_file = filename_input if filename_input.lower().endswith(".txt") else f"{filename_input}.txt"


# --- Helper Functions ---

def get_site_config(url):
    """Returns the correct CSS selectors for content and title based on the URL."""
    if "scribblehub.com" in url:
        # CORRECTED AGAIN: Based on the provided source, the correct title class is 'chapter-title'.
        return "#chp_raw", "div.chapter-title"
    elif "royalroad.com" in url:
        return ".chapter-content", "h1"   # Content selector, Title selector
    return None, None

def scrape_chapter_content(page, url, timeout_ms):
    """Navigates to a URL and scrapes the chapter title and content."""
    try:
        content_selector, title_selector = get_site_config(url)
        if not content_selector:
            print(f"⚠️ Unsupported site: {url}")
            return None, None

        page.goto(url, timeout=timeout_ms)
        
        # ADDED: Proactively click the GDPR/cookie banner if it appears on the page.
        try:
            page.get_by_role("button", name="Got it!").click(timeout=3000)
        except Exception:
            pass # It's okay if the banner isn't there; just continue.

        page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
        
        # Wait for the specific content elements to be ready
        page.wait_for_selector(title_selector, state="attached", timeout=timeout_ms)
        page.wait_for_selector(content_selector, state="attached", timeout=timeout_ms)
        
        title_element = page.query_selector(title_selector)
        title = title_element.inner_text().strip() if title_element else "Untitled Chapter"

        content_element = page.query_selector(content_selector)
        content = content_element.inner_text().strip() if content_element else ""
        
        return title, content
    except Exception as e:
        # A more detailed error message helps in debugging
        print(f"❌ Error loading or scraping {url}: {type(e).__name__} - {e}")
        return None, None

def parse_input_file(filepath):
    """
    Reads chapter_list.txt and returns a list of tuples.
    Format: (line_index, title_if_scraped, url)
    """
    entries = []
    with open(filepath, "r", encoding="utf-8") as f:
        for i, line in enumerate(f.readlines()):
            line = line.strip()
            if not line:
                continue
            
            # Regex to check for the '✔' mark and capture the title and URL
            match = re.match(r"✔\s*(.*?)\s+(https?://\S+)", line)
            if match:
                title = match.group(1).strip()
                url = match.group(2).strip()
                entries.append((i, title, url))
            else:
                # If no checkmark, the line is just a URL
                entries.append((i, None, line))
    return entries

def update_input_file(filepath, index, title, url):
    """Marks a chapter as completed in chapter_list.txt."""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    lines[index] = f"✔ {title} {url}\n"
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(lines)

def append_to_output_file(filepath, title, content):
    """Appends a single formatted chapter to the output file."""
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(f"\n--- {title} ---\n\n{content}\n")

def parse_output_file(filepath):
    """
    Reads an existing output file and parses its chapters into a dictionary.
    This uses a reliable regex method instead of splitting strings.
    """
    chapters = {}
    if not os.path.exists(filepath):
        return chapters
        
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Regex to find all "--- TITLE ---\n\nCONTENT" blocks
    pattern = re.compile(r"---\s*(.*?)\s*---\n\n(.*?)(?=\n---|\Z)", re.DOTALL)
    matches = pattern.findall(content)
    
    for title, text in matches:
        chapters[title.strip()] = text.strip()
        
    return chapters

def build_final_file(output_filepath, all_chapters_data, input_filepath):
    """
    Writes the final output file from scratch, ensuring all chapters are in the
    correct order as defined by chapter_list.txt.
    """
    # 1. Get the correct order of titles from the input file
    ordered_titles = []
    entries = parse_input_file(input_filepath)
    for _, title, _ in entries:
        if title: # Only include chapters that have been scraped and have a title
            ordered_titles.append(title)

    # 2. Write the file from scratch in the correct order
    print(f"\n rebuilding {output_filepath} in the correct order...")
    with open(output_filepath, "w", encoding="utf-8") as f:
        for title in ordered_titles:
            if title in all_chapters_data:
                content = all_chapters_data[title]
                f.write(f"\n--- {title} ---\n\n{content}\n")
    print("✅ Final file built successfully.")


# --- Main Scraper Logic ---

def run_scraper():
    """Main function to orchestrate the scraping process."""
    input_filepath = "chapter_list.txt"
    entries = parse_input_file(input_filepath)
    
    urls_to_scrape = [(index, url) for index, title, url in entries if not title]
    
    if not urls_to_scrape:
        print("\n✅ All chapters in 'chapter_list.txt' have already been scraped.")
        # Even if nothing new is scraped, we run the re-order to fix any past ordering issues.
        print("\n running a final check to ensure correct chapter order...")
        all_chapters = parse_output_file(output_file)
        if all_chapters:
            build_final_file(output_file, all_chapters, input_filepath)
        return

    print("\n🧠 Heads up:")
    print("* A browser window will open — do NOT minimize or close it.")
    print("* The browser will close automatically when finished.")
    input("\nPress Enter to begin scraping...")

    scraped_something_new = False
    failed_urls = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        total_to_scrape = len(urls_to_scrape)
        for i, (index, url) in enumerate(urls_to_scrape):
            print(f"\n scraping [{i+1}/{total_to_scrape}]: {url}")
            
            delay = 2  # Start with a 2-second delay
            for attempt in range(3): # 3 retries
                timeout = (attempt + 1) * 20000 # 20s, 40s, 60s
                title, content = scrape_chapter_content(page, url, timeout)

                if title and content is not None:
                    print(f"✅ Scraped and appended: {title}")
                    append_to_output_file(output_file, title, content)
                    update_input_file(input_filepath, index, title, url)
                    scraped_something_new = True
                    break
                else:
                    print(f"  -> Retry {attempt + 1} failed. Waiting {delay}s...")
                    time.sleep(delay)
                    delay *= 2 # Double the delay for the next retry
            else: # This 'else' belongs to the 'for' loop, runs if it finishes without break
                print(f"⛔ All retries failed for: {url}")
                failed_urls.append(url)
        
        browser.close()

    # --- Final File Assembly ---
    # This now happens only ONCE, after all scraping is done, to ensure order.
    if scraped_something_new:
        print("\n Re-ordering final text file...")
        all_chapters = parse_output_file(output_file)
        build_final_file(output_file, all_chapters, input_filepath)
    
    # --- Summary ---
    saved_count = len(urls_to_scrape) - len(failed_urls)
    skipped_count = len(entries) - len(urls_to_scrape)
    failed_count = len(failed_urls)

    print("\n📊 Summary:")
    print(f"✅ Saved {saved_count} new chapters.")
    print(f"⏭️ Skipped {skipped_count} already-saved chapters.")
    print(f"❌ Failed to scrape {failed_count} chapters.")

    if failed_urls:
        with open("failed_chapters.txt", "w", encoding="utf-8") as f:
            f.write("\nThe following URLs could not be scraped:\n")
            for url in failed_urls:
                f.write(f"{url}\n")
        print("\n- A list of failed URLs has been saved to 'failed_chapters.txt'.")
        print("- You can run the script again to retry them.")
    else:
        # Check if anything was scraped before printing success
        if scraped_something_new:
             print("\n🎉 All new chapters scraped successfully!")

if __name__ == "__main__":
    run_scraper()
