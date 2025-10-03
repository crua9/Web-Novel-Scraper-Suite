import json
import re
from playwright.sync_api import sync_playwright, TimeoutError
import math
import sys
import os
import datetime
import time

# --- Constants ---
STORIES_DB_FILE = "stories.json"

# --- Database Functions ---
def load_stories_db():
    """Loads the stories database from the JSON file."""
    if not os.path.exists(STORIES_DB_FILE):
        return {}
    with open(STORIES_DB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_stories_db(db):
    """Saves the stories database to the JSON file."""
    with open(STORIES_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4)

# --- Scraping Functions ---
def get_scribblehub_links(page):
    """Scrapes all chapter links from a ScribbleHub series page."""
    print("📖 Clicking the 'Show All Chapters' icon...")
    page.get_by_title("Show All Chapters").click()
    print("⏳ Waiting for all chapters to load... (this might take a minute or two)")
    page.wait_for_selector("#pagination-mesh-toc", state="hidden", timeout=120000)
    print("✅ TOC fully loaded.")
    links = page.query_selector_all(".toc_ol .toc_a")
    base_url = "https://www.scribblehub.com"
    urls = []
    for link in links:
        href = link.get_attribute("href")
        if href:
            urls.append(base_url + href.strip() if href.startswith('/') else href.strip())
    return urls

def get_royalroad_links(page):
    """Scrapes all chapter links from a Royal Road fiction page."""
    print("🔍 Extracting Royal Road links from page data...")
    script_content = page.content()
    match = re.search(r'window\.chapters\s*=\s*(\[.*?\]);', script_content)
    if not match:
        print("❌ Could not find chapter data script block.")
        return []
    try:
        chapters_data = json.loads(match.group(1))
        base_url = "https://www.royalroad.com"
        return [base_url + chapter['url'] for chapter in chapters_data]
    except (json.JSONDecodeError, KeyError) as e:
        print(f"❌ Failed to parse chapter data: {e}")
        return []

def get_all_chapter_links(story_url):
    """Launches a browser and scrapes chapter links from either site."""
    print("🌐 Launching browser...")
    urls = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        try:
            print(f"📄 Loading story page: {story_url}")
            page.goto(story_url, timeout=60000)
            try:
                page.get_by_role("button", name="Got it!").click(timeout=5000)
                print("✅ Cookie consent accepted.")
            except TimeoutError:
                print("👍 No cookie consent banner found.")

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
            browser.close()
            print(f"✅ Found {len(urls)} chapter links.")
            return urls

# --- File Handling & UI ---
def print_progress_bar(iteration, total, prefix='', suffix='', length=50, fill='█'):
    """
    Call in a loop to create a terminal progress bar.
    """
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    sys.stdout.write(f'\r{prefix} |{bar}| {percent}% {suffix}')
    sys.stdout.flush()
    if iteration == total:
        print()

def save_chunks(urls, base_name, chunk_size, output_dir):
    """Saves a list of URLs into multiple text files with a progress bar."""
    if not urls:
        return
    total = len(urls)
    chunks = math.ceil(total / chunk_size)
    print(f"\n📦 Saving {total} links into {chunks} file(s) in '{output_dir}'...")
    
    print_progress_bar(0, chunks, prefix='Progress:', suffix='Complete', length=50)
    for i in range(chunks):
        start_index = i * chunk_size
        end_index = min(start_index + chunk_size, total)
        chunk_data = urls[start_index:end_index]
        start_chap = start_index + 1
        end_chap = end_index
        filename = os.path.join(output_dir, f"{base_name} {start_chap}-{end_chap}.txt")
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n".join(chunk_data) + "\n")
        except Exception as e:
            print(f"\n❌ Failed to save {filename}: {e}")
        
        time.sleep(0.05)
        print_progress_bar(i + 1, chunks, prefix='Progress:', suffix='Complete', length=50)
    print() # Final newline after bar is done

def read_all_links_from_folder(folder_path):
    """Reads all URLs from all .txt files in a directory."""
    all_urls = []
    if not os.path.exists(folder_path):
        return all_urls
    try:
        files = sorted([f for f in os.listdir(folder_path) if f.endswith('.txt')])
        for filename in files:
            with open(os.path.join(folder_path, filename), 'r', encoding='utf-8') as f:
                all_urls.extend([line.strip() for line in f if line.strip()])
    except Exception as e:
        print(f"Could not read link files: {e}")
    return all_urls

# --- Menu Functions ---
def scrape_new_story():
    """Guides user through scraping a new story and saves it to the DB."""
    print("\n--- Scrape a New Story ---")
    story_url = input("🔗 Enter a ScribbleHub or Royal Road story URL: ").strip()
    if not ("scribblehub.com/series/" in story_url or "royalroad.com/fiction/" in story_url):
        print("⚠️ Invalid URL. Must be a ScribbleHub or Royal Road fiction URL.")
        return

    print("\nNext, let's set up the folder where your link files will be saved.")
    project_folder = input("📂 Enter a main project folder name (e.g., 'World Keeper'): ").strip()
    if not project_folder:
        print("⚠️ Project folder name cannot be empty.")
        return
    
    output_dir = os.path.join(project_folder, "links")
    os.makedirs(output_dir, exist_ok=True)
    print(f"\n✅ Link files will be saved in: '{output_dir}'")
    
    base_name = input("📝 What should the link files be named? (e.g. World Keeper Links): ").strip()
    if not base_name:
        print("⚠️ File name cannot be empty.")
        return
        
    try:
        chunk_size_input = input("🔢 How many links per file? (e.g. 100): ").strip()
        chunk_size = int(chunk_size_input) if chunk_size_input else 100
    except ValueError:
        chunk_size = 100
        print("⚠️ Invalid number. Using default: 100")

    print("\n🚀 Starting scrape...")
    urls = get_all_chapter_links(story_url)
    if not urls:
        print("❌ No chapter links found. Exiting.")
        return

    save_chunks(urls, base_name, chunk_size, output_dir)
    
    db = load_stories_db()
    db[project_folder] = {
        "story_url": story_url,
        "base_name": base_name,
        "chunk_size": chunk_size,
        "output_dir": output_dir,
        "last_chapter_count": len(urls),
        "last_scraped_date": datetime.datetime.now().isoformat(),
        "is_complete": False
    }
    save_stories_db(db)
    print(f"\n💾 Story '{project_folder}' saved to tracking database.")

def check_for_updates():
    """Checks all active stories for new or removed chapters."""
    print("\n--- Check All Stories for Updates ---")
    db = load_stories_db()
    if not db:
        print("No stories are currently being tracked. Scrape a new story first.")
        return
        
    active_stories = {name: data for name, data in db.items() if not data.get('is_complete')}
    if not active_stories:
        print("All tracked stories are marked as complete. No checks will be performed.")
        return

    total_stories = len(active_stories)
    print(f"Found {total_stories} active stories to check...")
    
    updates_found_overall = False
    for i, (name, data) in enumerate(active_stories.items()):
        print(f"\n--- [{i+1}/{total_stories}] Checking '{name}' ---")
        
        current_urls = get_all_chapter_links(data['story_url'])
        if not current_urls:
            print("Could not retrieve current chapters. Skipping.")
            continue
            
        existing_urls = read_all_links_from_folder(data['output_dir'])
        
        current_set = set(current_urls)
        existing_set = set(existing_urls)

        new_urls = sorted(list(current_set - existing_set), key=current_urls.index)
        removed_urls = list(existing_set - current_set)

        if not new_urls and not removed_urls:
            print("✅ No changes found.")
            continue

        updates_found_overall = True
        print(f"✨ Found Changes for '{name}':")
        if new_urls:
            print(f"  + {len(new_urls)} new chapters added.")
        if removed_urls:
            print(f"  - {len(removed_urls)} chapters removed.")
            
        proceed = input("Do you want to update your local files? (y/n): ").strip().lower()
        if proceed in ['y', 'yes']:
            print("Updating files...")
            for filename in os.listdir(data['output_dir']):
                os.remove(os.path.join(data['output_dir'], filename))
            
            save_chunks(current_urls, data['base_name'], data['chunk_size'], data['output_dir'])

            db[name]['last_chapter_count'] = len(current_urls)
            db[name]['last_scraped_date'] = datetime.datetime.now().isoformat()
            save_stories_db(db)
            print("✅ Update complete.")
        else:
            print("Update cancelled.")
    
    if not updates_found_overall:
        print("\n✅ All active stories are up to date.")

def manage_stories():
    """Allows the user to mark stories as complete or active."""
    print("\n--- Manage Tracked Stories ---")
    db = load_stories_db()
    if not db:
        print("No stories are currently being tracked.")
        return
        
    stories = list(db.keys())
    while True:
        print("\nYour tracked stories:")
        for i, name in enumerate(stories):
            status = "Complete" if db[name].get('is_complete') else "Active"
            print(f"  {i+1}: {name} ({status})")
        print("  0: Back to Main Menu")

        try:
            choice = int(input("\nEnter the number of a story to toggle its status: ").strip())
            if choice == 0:
                break
            if 1 <= choice <= len(stories):
                story_name = stories[choice - 1]
                current_status = db[story_name].get('is_complete', False)
                db[story_name]['is_complete'] = not current_status
                save_stories_db(db)
                new_status = "Complete" if not current_status else "Active"
                print(f"✅ '{story_name}' has been marked as {new_status}.")
            else:
                print("⚠️ Invalid number.")
        except ValueError:
            print("⚠️ Please enter a valid number.")

def main_menu():
    """Displays the main menu and handles user choices."""
    while True:
        print("\n📘 Universal Chapter Link Grabber Menu 📘")
        print("1: Scrape a New Story")
        print("2: Check All Stories for Updates")
        print("3: Manage Tracked Stories")
        print("4: Exit")
        choice = input("Enter your choice (1-4): ").strip()

        if choice == '1':
            scrape_new_story()
        elif choice == '2':
            check_for_updates()
        elif choice == '3':
            manage_stories()
        elif choice == '4':
            print("Goodbye!")
            break
        else:
            print("⚠️ Invalid choice. Please enter a number between 1 and 4.")
        input("\nPress Enter to return to the menu...")

if __name__ == "__main__":
    try:
        main_menu()
    except ImportError:
        print("\n--- ERROR ---")
        print("Playwright library not found. It's needed for this script to work.")
        print("Please run the following commands in your terminal:")
        print("1. pip install playwright")
        print("2. playwright install")
        input("\nPress Enter to exit.")
    except Exception as e:
        print(f"\n--- An Unexpected Error Occurred ---")
        print(f"Error: {e}")
        input("\nPress Enter to exit.")
