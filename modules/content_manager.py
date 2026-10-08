import time
import random
import os
from .utils import (
    get_theme_colors, load_stories_db, clean_filename, 
    read_all_links_from_folder, scrape_chapter_content, open_browser, goto, print_progress_bar
)
from playwright.sync_api import sync_playwright

def assemble_chapter_list(story_name=None, story_path=None, auto_reset=False):
    """Option 4. Can also be called directly (e.g. after Hard Sync) with a story already chosen.
    auto_reset=True answers 'yes' to the clear-progress question automatically."""
    clr = get_theme_colors()
    P, S, G, Y, R, W = clr['P'], clr['S'], clr['G'], clr['Y'], clr['R'], clr['W']
    
    db = load_stories_db()
    stories = list(db.keys())
    
    if not stories:
        print(f"\n{Y}ℹ️ No stories found in database.{W}")
        return

    if story_name is None:
        print(f"\n{S}────────── 📂 Select Story to Assemble ──────────{W}")
        for i, name in enumerate(stories):
            print(f" {P}{i+1}{W}: {name}")
        
        choice = input(f"\n{S}Enter ID # (or 0 to cancel): {W}").strip()
        if not choice or choice == '0': return

        try:
            idx = int(choice) - 1
            story_name = stories[idx]
        except:
            print(f"{R}❌ Invalid Selection.{W}")
            return
    else:
        print(f"\n{S}────────── 📂 Assembling chapter_list for {story_name} ──────────{W}")

    data = db.get(story_name, {})
    if story_path is None:
        story_path = os.path.join("stories", story_name)
    links = read_all_links_from_folder(story_path)
    
    if not links:
        print(f"{R}❌ No link files found for {story_name}.{W}")
        return

    # Grab the chapter offset we assigned in Hard Sync
    offset = data.get('chapter_offset', 0)
    start_display = 1 + offset
    end_display = len(links) + offset

    print(f"\n{Y}Found {len(links)} total links for {story_name}.{W}")
    start_chap = input(f"{S}Start Chapter ({start_display}-{end_display}) [Press Enter for {start_display}]: {W}").strip()
    end_chap = input(f"{S}End Chapter ({start_display}-{end_display}) [Press Enter for {end_display}]: {W}").strip()

    try:
        start_idx = int(start_chap) - 1 - offset if start_chap else 0
        end_idx = int(end_chap) - offset if end_chap else len(links)
        
        # Ensure indices are within bounds
        start_idx = max(0, start_idx)
        end_idx = min(len(links), end_idx)
        
        if start_idx >= end_idx:
            print(f"{R}❌ Invalid range.{W}")
            return
            
        selected_links = links[start_idx:end_idx]
    except ValueError:
        print(f"{R}⚠️ Invalid input. Assembling all links.{W}")
        start_idx = 0
        end_idx = len(links)
        selected_links = links

    output_file = os.path.join(story_path, "chapter_list.txt")
    
    # Check for existing entries and their completion status
    existing_entries = []
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            existing_entries = [line.strip() for line in f if line.strip()]

    reset_progress = False
    if existing_entries and auto_reset:
        print(f"{Y}Clearing previous scrape progress (auto: yes).{W}")
        reset_progress = True
    elif existing_entries:
        ans = input(f"\n{Y}Clear previous scrape progress (checkmarks) for these chapters? (y/N): {W}").strip().lower()
        if ans == 'y':
            reset_progress = True

    total = len(selected_links)
    with open(output_file, "w", encoding="utf-8") as f:
        for n, link in enumerate(selected_links, 1):
            print_progress_bar(n, total, prefix='Assembling:', suffix='Complete', length=30)
            found = False
            if not reset_progress:
                for entry in existing_entries:
                    if link in entry:
                        f.write(f"{entry}\n")
                        found = True
                        break
            if not found:
                f.write(f"{link}\n")

    print(f"{G}✅ chapter_list.txt assembled for: {story_name} (Chapters {start_idx + 1 + offset} to {end_idx + offset}){W}")


def scrape_story_content(config, site_configs):
    clr = get_theme_colors()
    P, S, G, Y, R, W = clr['P'], clr['S'], clr['G'], clr['Y'], clr['R'], clr['W']
    
    db = load_stories_db()
    stories = list(db.keys())
    
    print(f"\n{S}────────── 📝 Select Story to Scrape ──────────{W}")
    for i, name in enumerate(stories):
        print(f" {P}{i+1}{W}: {name}")
    
    choice = input(f"\n{S}Enter ID # (or 0 to cancel): {W}").strip()
    if not choice or choice == '0': return

    try:
        idx = int(choice) - 1
        story_name = stories[idx]
        data = db[story_name]
    except:
        print(f"{R}❌ Invalid Selection.{W}")
        return

    story_path = os.path.join("stories", story_name)
    list_file = os.path.join(story_path, "chapter_list.txt")
    
    if not os.path.exists(list_file):
        print(f"{R}❌ Error: chapter_list.txt not found. Run Option 4 first.{W}")
        return

    with open(list_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        print(f"{R}❌ chapter_list.txt is empty.{W}")
        return

    to_scrape = [i for i, line in enumerate(lines) if not line.startswith("✔")]
    
    if not to_scrape:
        print(f"{G}✨ All chapters in the list are already scraped for {story_name}.{W}")
        return

    print(f"\n{Y}Found {len(to_scrape)} unscraped chapters in the ledger.{W}")
    
    all_links = read_all_links_from_folder(story_path)
    offset = data.get('chapter_offset', 0)
    
    def extract_url(line):
        return line.split(" | ")[-1].strip() if " | " in line else line.strip()

    first_url = extract_url(lines[to_scrape[0]]) if to_scrape else extract_url(lines[0])
    last_url = extract_url(lines[to_scrape[-1]]) if to_scrape else extract_url(lines[-1])
    
    start_chap_num = all_links.index(first_url) + 1 + offset if first_url in all_links else 1 + offset
    end_chap_num = all_links.index(last_url) + 1 + offset if last_url in all_links else len(lines) + offset

    if start_chap_num == end_chap_num:
        default_file = f"{story_name} {start_chap_num}.txt"
    else:
        default_file = f"{story_name} {start_chap_num}-{end_chap_num}.txt"
        
    file_name_input = input(f"{S}Name for the output text file? (Press Enter for '{default_file}'): {W}").strip()
    if not file_name_input:
        file_name_input = default_file
    elif not file_name_input.endswith('.txt'):
        file_name_input += '.txt'

    print(f"{S}🚀 Starting scraper for {story_name}...{W}")
    
    with sync_playwright() as p:
        browser, page = open_browser(p)
        
        content_file = os.path.join(story_path, file_name_input)
        
        for i, idx in enumerate(to_scrape):
            raw_line = lines[idx]
            url = extract_url(raw_line)
            
            # --- Dynamically pick scraper based on the link ---
            site_config = None
            if "royalroad.com" in url:
                site_config = site_configs.get("royalroad")
            elif "scribblehub.com" in url:
                site_config = site_configs.get("scribblehub")
            else:
                domain_guess = url.replace("https://", "").replace("http://", "").replace("www.", "").split(".")[0]
                site_config = site_configs.get(domain_guess)

            if not site_config:
                print(f"\n{R}⚠️ No scraper configuration found for: {url}{W}")
                continue
            
            print_progress_bar(i, len(to_scrape), prefix='Progress:', suffix='Complete', length=30)
            
            try:
                title, content = scrape_chapter_content(page, url, site_config)
                time.sleep(random.uniform(1.5, 3.0))  # gentle pacing so Cloudflare doesn't flag rapid-fire loads
                
                if title and content:
                    with open(content_file, "a", encoding="utf-8") as out:
                        out.write(f"\n--- {title} ---\n{content}\n")
                    lines[idx] = f"✔ {title} | {url}"
                else:
                    print(f"\n{R}⚠️ Failed to get content for: {url}{W}")
                    
            except Exception as e:
                print(f"\n{R}❌ Error at {url}: {e}{W}")

        browser.close()

    with open(list_file, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(f"{line}\n")

    print(f"\n{G}✅ Scraping complete. Saved {len(to_scrape)} chapters to {file_name_input}.{W}")
