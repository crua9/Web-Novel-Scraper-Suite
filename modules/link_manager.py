import os
from playwright.sync_api import sync_playwright
from .utils import (
    get_theme_colors, clean_filename, save_chunks, 
    load_stories_db, save_stories_db, get_all_chapter_links,
    load_site_configs, read_all_links_from_folder,
    scrape_chapter_content
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
        end = min(start + 10, len(all_p))
        print(f"\n{S}📂 Select Folder:{W}")
        for i in range(start, end): print(f" {P}{i+1}{W}: {all_p[i]}")
        if end < len(all_p): print(f" {Y}N{W}: Next Page")
        if start > 0: print(f" {Y}B{W}: Prev Page")
        
        choice = input(f"{S}Selection (or 0 to cancel): {W}").strip().lower()
        if choice == '0': return None
        elif choice == 'n' and end < len(all_p): start += 10
        elif choice == 'b' and start > 0: start -= 10
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(all_p): return all_p[idx]

def scrape_new_story_links(config, site_configs):
    clr = get_theme_colors()
    P, S, G, Y, R, W = clr['P'], clr['S'], clr['G'], clr['Y'], clr['R'], clr['W']
    
    print(f"\n{S}────────── 🔗 Scrape New Story Links ──────────{W}")
    url = input(f"{S}Enter the Table of Contents URL: {W}").strip()
    if not url: return

    domain = get_clean_domain(url)
    site_config = site_configs.get(domain)
    if not site_config:
        print(f"{R}❌ Unsupported site: {domain}{W}")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            links = get_all_chapter_links(page, site_config)
            
            if not links:
                print(f"{R}❌ No links found.{W}")
                return

            print(f"\n{G}✅ Found {len(links)} links.{W}")
            
            try:
                title = page.inner_text('h1').strip()
                title = clean_filename(title)
            except:
                title = ""

            story_name = input(f"{S}Enter Story Name [{title}]: {W}").strip()
            if not story_name: story_name = title
            if not story_name: story_name = "Unknown_Story"

            story_path = os.path.join("stories", story_name)
            os.makedirs(story_path, exist_ok=True)
            
            save_chunks(links, story_path, story_name)
            
            db = load_stories_db()
            db[story_name] = {
                "story_url": url,
                "domain": domain,
                "last_chapter_count": len(links),
                "is_complete": False,
                "chapter_offset": 0
            }
            save_stories_db(db)
            print(f"{G}✅ Story '{story_name}' added and links saved!{W}")
            
        except Exception as e:
            print(f"{R}❌ Error: {e}{W}")
        finally:
            browser.close()

def check_for_updates(config, site_configs):
    clr = get_theme_colors()
    P, S, G, Y, R, W = clr['P'], clr['S'], clr['G'], clr['Y'], clr['R'], clr['W']
    
    db = load_stories_db()
    active = [name for name, data in db.items() if not data.get('is_complete')]
    if not active:
        print(f"\n{Y}ℹ️ No active stories to check.{W}")
        return

    print(f"\n{S}────────── 🔄 Check For Updates ──────────{W}")
    for i, name in enumerate(active):
        print(f" {P}{i+1}{W}: {name}")
        
    choice = input(f"\n{S}Select Story ID, 'A' for All, or 0 to cancel: {W}").strip().lower()
    if not choice or choice == '0': 
        return
        
    to_check = []
    if choice == 'a':
        to_check = active
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(active):
                to_check = [active[idx]]
            else:
                print(f"{R}❌ Invalid Selection.{W}")
                return
        except ValueError:
            print(f"{R}❌ Invalid input.{W}")
            return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        for db_name in to_check:
            data = db[db_name]
            domain = get_clean_domain(data['story_url'])
            site_config = site_configs.get(domain)
            if not site_config: continue
            
            print(f"[{P}{db_name}{W}] Checking...", end=" ")
            story_path = os.path.join("stories", db_name) if os.path.exists(os.path.join("stories", db_name)) else db_name
            os.makedirs(story_path, exist_ok=True)
            
            try:
                page.goto(data['story_url'], wait_until="domcontentloaded", timeout=60000)
                new_links = get_all_chapter_links(page, site_config)
                existing = read_all_links_from_folder(story_path)
                
                added = [l for l in new_links if l not in existing]
                if added:
                    save_chunks(new_links, story_path, db_name)
                    db[db_name]['last_chapter_count'] = len(new_links)
                    save_stories_db(db)
                    print(f"{G}Found {len(added)} new!{W}")
                else:
                    print(f"{Y}Up to date.{W}")
            except Exception as e:
                print(f"{R}Error: {e}{W}")
        browser.close()
        print(f"\n{G}✅ Update check complete!{W}")

def check_for_revived_links(config, site_configs):
    clr = get_theme_colors()
    P, S, G, Y, R, W = clr['P'], clr['S'], clr['G'], clr['Y'], clr['R'], clr['W']
    
    db = load_stories_db()
    active = [name for name, data in db.items() if not data.get('is_complete')]
    if not active: return
    
    print(f"\n{S}────────── 🔄 Hard Sync / Fix Stubbed Story ──────────{W}")
    print(f"{Y}Use this if a story was 'stubbed' or chapters were deleted by the author.")
    print(f"This will OVERWRITE your local links to match exactly what is on the site right now.{W}")
    
    for i, name in enumerate(active): print(f" {P}{i+1}{W}: {name}")
    choice = input(f"\n{S}Select Story ID (or 0 to cancel): {W}").strip()
    if not choice or choice == '0': return
    
    try:
        db_name = active[int(choice)-1]
        data = db[db_name]
    except (ValueError, IndexError):
        print(f"{R}❌ Invalid choice.{W}")
        return
        
    print(f"\n{S}📂 Location for '{db_name}':{W}\n {P}1{W}: Auto-detect | {P}2{W}: Browse")
    f_choice = input(f"{S}Choice: {W}").strip()
    story_path = pick_story_folder() if f_choice == '2' else (os.path.join("stories", db_name) if os.path.exists(os.path.join("stories", db_name)) else db_name)
    
    if not story_path:
        print(f"{R}❌ Invalid path selected.{W}")
        return
        
    os.makedirs(story_path, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        try:
            page.goto(data['story_url'], wait_until="domcontentloaded", timeout=60000)
            domain = get_clean_domain(data['story_url'])
            site_config = site_configs.get(domain)
            
            if not site_config:
                print(f"{R}❌ No scraper config found for domain: {domain}.{W}")
                return
                
            new_links = get_all_chapter_links(page, site_config)
            
            if not new_links:
                print(f"{R}❌ No links found on the page. Sync aborted to prevent data loss.{W}")
                return

            print(f"\n{S}🔍 To avoid gaps from deleted chapters, you can set a 'Resume Link'.{W}")
            print(f"{Y}The scraper will ignore all chapters before this link and start fresh from it.{W}")
            resume_url = input(f"\n{S}Enter the URL of the chapter to start from (Press Enter to keep all): {W}").strip()

            if resume_url:
                slice_idx = -1
                for i, link in enumerate(new_links):
                    if resume_url in link or link in resume_url:
                        slice_idx = i
                        break
                
                if slice_idx != -1:
                    new_links = new_links[slice_idx:]
                    print(f"{G}✅ Found link! Slicing list to start from this chapter. ({len(new_links)} links remaining){W}")
                else:
                    print(f"{R}⚠️ Could not find that exact URL in the list. Proceeding with all links.{W}")
                
            print(f"\n{S}🔍 Fetching title of the starting chapter to help you set the numbering...{W}")
            try:
                title, _ = scrape_chapter_content(page, new_links[0], site_config)
            except:
                title = "Unknown Title"
                
            print(f"\n{P}Starting Chapter on Site:{W} {G}{title}{W}")
            print(f"{P}URL:{W} {new_links[0]}")
            
            offset_input = input(f"\n{S}What chapter number is this? (e.g. 233) [Press Enter for 1]: {W}").strip()
            try:
                start_num = int(offset_input) if offset_input else 1
                offset = max(0, start_num - 1)
            except ValueError:
                print(f"{Y}⚠️ Invalid input. Defaulting to Chapter 1.{W}")
                offset = 0

            links_dir = os.path.join(story_path, "links")
            if os.path.exists(links_dir):
                for file in os.listdir(links_dir):
                    if file.endswith(".txt"):
                        os.remove(os.path.join(links_dir, file))
            else:
                os.makedirs(links_dir, exist_ok=True)
                
            save_chunks(new_links, story_path, db_name)
            
            db[db_name]['last_chapter_count'] = len(new_links)
            db[db_name]['chapter_offset'] = offset
            save_stories_db(db)
            
            print(f"\n{G}✅ Hard Sync complete! Old dead links deleted.{W}")
            print(f"{G}✅ Saved {len(new_links)} current links. Offset set to +{offset}.{W}")
            print(f"{Y}⚠️ Don't forget to run Option 4 (Assemble chapter_list)! Type 'y' when it asks to clear progress so your read chapters stay checked off!{W}")
            
        except Exception as e:
            print(f"{R}❌ Error during sync: {e}{W}")
        finally:
            browser.close()
