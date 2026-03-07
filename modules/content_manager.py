import os
from .utils import (
    get_theme_colors, load_stories_db, clean_filename, 
    read_all_links_from_folder, scrape_chapter_content, print_progress_bar
)
from playwright.sync_api import sync_playwright

def assemble_chapter_list():
    clr = get_theme_colors()
    P, S, G, Y, R, W = clr['P'], clr['S'], clr['G'], clr['Y'], clr['R'], clr['W']
    
    db = load_stories_db()
    stories = list(db.keys())
    
    if not stories:
        print(f"\n{Y}ℹ️ No stories found in database.{W}")
        return

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

    story_path = os.path.join("stories", story_name)
    links = read_all_links_from_folder(story_path)
    
    if not links:
        print(f"{R}❌ No link files found for {story_name}.{W}")
        return

    output_file = os.path.join(story_path, "chapter_list.txt")
    
    # If file exists, we don't want to overwrite progress markers (✔)
    existing_entries = []
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            existing_entries = [line.strip() for line in f if line.strip()]

    with open(output_file, "w", encoding="utf-8") as f:
        for link in links:
            # Check if this link was already marked as done
            found = False
            for entry in existing_entries:
                if link in entry:
                    f.write(f"{entry}\n")
                    found = True
                    break
            if not found:
                f.write(f"{link}\n")

    print(f"{G}✅ chapter_list.txt assembled for: {story_name}{W}")

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

    to_scrape = [i for i, line in enumerate(lines) if not line.startswith("✔")]
    
    if not to_scrape:
        print(f"{G}✨ All chapters already scraped for {story_name}.{W}")
        return

    domain = data.get('domain', '').split('.')[0]
    site_config = site_configs.get(domain)

    print(f"{S}🚀 Starting scraper for {story_name}...{W}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        content_file = os.path.join(story_path, f"{story_name}.txt")
        
        for i, idx in enumerate(to_scrape):
            url = lines[idx]
            print_progress_bar(i, len(to_scrape), prefix='Progress:', suffix='Complete', length=30)
            
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                title, content = scrape_chapter_content(page, url, site_config)
                
                if title and content:
                    with open(content_file, "a", encoding="utf-8") as out:
                        out.write(f"\n\n{title}\n\n{content}\n")
                    lines[idx] = f"✔ {title} | {url}"
                else:
                    print(f"\n{R}⚠️ Failed to get content for: {url}{W}")
                    
            except Exception as e:
                print(f"\n{R}❌ Error at {url}: {e}{W}")

        browser.close()

    # Update the chapter list with checkmarks
    with open(list_file, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(f"{line}\n")

    print(f"\n{G}✅ Scraping complete for {story_name}.{W}")
