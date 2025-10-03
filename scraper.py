from playwright.sync_api import sync_playwright, TimeoutError
import time
import sys
import os
import re

# --- Constants ---
SUBFOLDER_PREF_FILE = "_subfolder_pref.txt"

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

# --- NEW: Subfolder Selection Logic ---
subfolder_name = ""
if os.path.exists(SUBFOLDER_PREF_FILE):
    with open(SUBFOLDER_PREF_FILE, "r", encoding="utf-8") as f:
        last_folder = f.read().strip()
    if last_folder:
        use_last = input(f"\n📁 The last used subfolder was '{last_folder}'. Use this folder again? (y/n): ").strip().lower()
        if use_last in ['y', 'yes']:
            subfolder_name = last_folder

# If no previous folder was found or the user wants a new one
if not subfolder_name:
    subfolder_name = input("\n📂 Enter the name for the subfolder to save files in (e.g., World Keeper): ").strip()

# Validate and save the preference
if not subfolder_name:
    print("⚠️ Subfolder name cannot be empty. Exiting.")
    sys.exit()

with open(SUBFOLDER_PREF_FILE, "w", encoding="utf-8") as f:
    f.write(subfolder_name)

os.makedirs(subfolder_name, exist_ok=True)
print(f"✅ Files will be saved in the '{subfolder_name}' subfolder.")

# Ask for output filename (base name)
filename_input = input(f"\n📂 Enter output filename for inside '{subfolder_name}' (e.g., World Keeper 300-400): ").strip()
if not filename_input:
    base_output_filename = "scraped_chapters.txt"
else:
    base_output_filename = filename_input if filename_input.lower().endswith(".txt") else f"{filename_input}.txt"

# Construct full path for the output file
output_file = os.path.join(subfolder_name, base_output_filename)

# Ask to save author's notes
save_notes_input = input("\n📝 Save author's notes to a separate file? (y/n): ").strip().lower()
save_author_notes = save_notes_input in ["y", "yes"]
notes_output_file = ""
if save_author_notes:
    base_name, ext = os.path.splitext(base_output_filename)
    notes_filename = f"{base_name} Author notes{ext}"
    notes_output_file = os.path.join(subfolder_name, notes_filename)
    print(f"🗒️  Author's notes will be saved to: {notes_output_file}")


# --- Helper Functions ---

def get_site_config(url):
    """Returns the correct CSS selectors for content and title based on the URL."""
    if "scribblehub.com" in url:
        return "#chp_raw", "div.chapter-title"
    elif "royalroad.com" in url:
        return ".chapter-content", "h1"  # Content selector, Title selector
    return None, None

def scrape_chapter_content(page, url, timeout_ms):
    """Navigates to a URL and scrapes title, content, and author's notes."""
    try:
        content_selector, title_selector = get_site_config(url)
        if not content_selector:
            print(f"⚠️ Unsupported site: {url}")
            return None, None, None

        page.goto(url, timeout=timeout_ms)
        
        try:
            page.get_by_role("button", name="Got it!").click(timeout=3000)
        except Exception:
            pass 

        page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
        
        page.wait_for_selector(title_selector, state="attached", timeout=timeout_ms)
        page.wait_for_selector(content_selector, state="attached", timeout=timeout_ms)
        
        author_notes = None
        # Extract and Remove Author's Notes
        if "scribblehub.com" in url:
            notes_element = page.query_selector('.wi_authornotes')
            if notes_element:
                author_notes = notes_element.inner_text().strip()
                page.evaluate("document.querySelector('.wi_authornotes')?.remove()")
        elif "royalroad.com" in url:
            notes_element = page.query_selector('.author-note-portlet')
            if notes_element:
                author_notes = notes_element.inner_text().strip()
                page.evaluate("document.querySelector('.author-note-portlet')?.remove()")

        title_element = page.query_selector(title_selector)
        title = title_element.inner_text().strip() if title_element else "Untitled Chapter"

        content_element = page.query_selector(content_selector)
        content = content_element.inner_text().strip() if content_element else ""
        
        return title, content, author_notes
    except Exception as e:
        print(f"❌ Error loading or scraping {url}: {type(e).__name__} - {e}")
        return None, None, None

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
            
            match = re.match(r"✔\s*(.*?)\s+(https?://\S+)", line)
            if match:
                title = match.group(1).strip()
                url = match.group(2).strip()
                entries.append((i, title, url))
            else:
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

def append_to_notes_file(filepath, title, notes):
    """Appends a chapter's author notes to the specified file."""
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(f"\n--- {title} ---\n\n{notes}\n")

def parse_output_file(filepath):
    """Reads an existing output file and parses its chapters into a dictionary."""
    chapters = {}
    if not os.path.exists(filepath):
        return chapters
        
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
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
    ordered_titles = []
    entries = parse_input_file(input_filepath)
    for _, title, _ in entries:
        if title: 
            ordered_titles.append(title)

    print(f"\n rebuilding {output_filepath} in the correct order...")
    with open(output_filepath, "w", encoding="utf-8") as f:
        for title in ordered_titles:
            if title in all_chapters_data:
                content = all_chapters_data[title]
                f.write(f"\n--- {title} ---\n\n{content}\n")
    print("✅ Final file built successfully.")


# --- Main Scraper Logic ---

def run_scraper(save_notes_flag, notes_file_path):
    """Main function to orchestrate the scraping process."""
    input_filepath = "chapter_list.txt"
    entries = parse_input_file(input_filepath)
    
    urls_to_scrape = [(index, url) for index, title, url in entries if not title]
    
    if not urls_to_scrape:
        print("\n✅ All chapters in 'chapter_list.txt' have already been scraped.")
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
            
            delay = 2
            for attempt in range(3):
                timeout = (attempt + 1) * 20000
                title, content, author_notes = scrape_chapter_content(page, url, timeout)

                if title and content is not None:
                    print(f"✅ Scraped and appended: {title}")
                    append_to_output_file(output_file, title, content)
                    
                    if save_notes_flag and author_notes:
                        print(f"🗒️  Saving author's note for: {title}")
                        append_to_notes_file(notes_file_path, title, author_notes)

                    update_input_file(input_filepath, index, title, url)
                    scraped_something_new = True
                    break
                else:
                    print(f"  -> Retry {attempt + 1} failed. Waiting {delay}s...")
                    time.sleep(delay)
                    delay *= 2
            else:
                print(f"⛔ All retries failed for: {url}")
                failed_urls.append(url)
        
        browser.close()

    if scraped_something_new:
        print("\n Re-ordering final text file...")
        all_chapters = parse_output_file(output_file)
        build_final_file(output_file, all_chapters, input_filepath)
    
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
        if scraped_something_new:
             print("\n🎉 All new chapters scraped successfully!")

if __name__ == "__main__":
    run_scraper(save_author_notes, notes_output_file)

