import os
from playwright.sync_api import sync_playwright
from .utils import (
    get_theme_colors, clean_filename, save_chunks, 
    load_stories_db, save_stories_db, get_all_chapter_links,
    load_site_configs, read_all_links_from_folder
)

def get_clean_domain(url):
    try:
        clean_url = url.lower().replace("https://", "").replace("http://", "").replace("www.", "")
        return clean_url.split("/")[0].split('.')[0]
    except: return None

def pick_story_folder():
    clr = get_theme_colors()
    P, S, G, Y, R, W = clr['P'], clr['S'], clr['G'], clr['Y'], clr['R'], clr['W']
    ignore = ['modules', 'site_configs', '__pycache__', '.git', 'stories']
    root_f = [f for f in os.listdir(".") if os.path.isdir(f) and f not in ignore]
    sub_f = [os.path.join("stories", f) for f in os.listdir("stories") if os.path.isdir(os.path.join("stories", f))] if os.path.exists("stories") else []
    all_p = sorted(root_f + sub_f)
    if not all_p: return None
    start = 0
    while True:
        end = min(start + 20, len(all_p))
        batch = all_p[start:end]
        print(f"\n{S}────────── 📁 Browse Story Locations ──────────{W}")
        for i, path in enumerate(batch): print(f" {P}{i+1}{W}: {path.replace('stories'+os.sep, '[New] ')}")
        print(f"{S}─" * 45 + f"\n {G}21{W}: Next | {G}22{W}: Prev | {Y}0{W}: Cancel")
        choice = input(f"\n{S}ID: {W}").strip()
        if choice == '0': return None
        if choice == '21' and end < len(all_p): start += 20; continue
        if choice == '22' and start > 0: start -= 20; continue
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(batch): return batch[idx]
        except: pass

def scrape_new_story_links(config, site_configs):
    clr = get_theme_colors()
    S, G, R, W = clr['S'], clr['G'], clr['R'], clr['W']
    url = input(f"\n{S}Enter Story URL: {W}").strip()
    if not url: return
    domain = get_clean_domain(url)
    site_config = site_configs.get(domain)
    if not site_config: return
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        title = clean_filename(page.title().split(" | ")[0])
        links = get_all_chapter_links(page, site_config)
        browser.close()
    if not links: return
    db = load_stories_db()
    db[title] = {"story_url": url, "last_chapter_count": len(links), "is_complete": False, "domain": domain}
    save_stories_db(db)
    story_path = os.path.join("stories", title)
    os.makedirs(story_path, exist_ok=True)
    save_chunks(links, story_path, title)
    print(f"{G}✅ Links saved to {story_path}/links/{W}")

def check_for_updates(config, site_configs):
    clr = get_theme_colors()
    P, S, G, Y, R, W = clr['P'], clr['S'], clr['G'], clr['Y'], clr['R'], clr['W']
    db = load_stories_db()
    active = [name for name, data in db.items() if not data.get('is_complete')]
    if not active: return
    print(f"\n{S}────────── 🔄 Update Story ──────────{W}")
    for i, name in enumerate(active): print(f" {P}{i+1}{W}: {name}")
    choice = input(f"\n{S}ID: {W}").strip()
    if not choice or choice == '0': return
    db_name = active[int(choice)-1]
    data = db[db_name]
    print(f"\n{S}📂 Location for '{db_name}':{W}\n {P}1{W}: Auto-detect | {P}2{W}: Browse")
    f_choice = input(f"{S}Choice: {W}").strip()
    story_path = pick_story_folder() if f_choice == '2' else (os.path.join("stories", db_name) if os.path.exists(os.path.join("stories", db_name)) else db_name)
    os.makedirs(story_path, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(data['story_url'], wait_until="networkidle")
        new_links = get_all_chapter_links(page, site_configs.get(get_clean_domain(data['story_url'])))
        existing = read_all_links_from_folder(story_path)
        added = [l for l in new_links if l not in existing]
        if added:
            save_chunks(new_links, story_path, db_name)
            db[db_name]['last_chapter_count'] = len(new_links)
            save_stories_db(db)
            print(f"{G}✨ Added {len(added)} new links!{W}")
        else: print(f"{Y}☕ No new chapters.{W}")
        browser.close()

def check_for_revived_links(config, site_configs):
    print("Scan complete.")
