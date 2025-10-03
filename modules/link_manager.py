import os
import re
import datetime
from .utils import (
    load_config, save_config, get_all_chapter_links,
    save_chunks, read_all_links_from_folder, load_stories_db, save_stories_db
)

def scrape_new_story_links(config, site_configs):
    """Guides user through scraping links for a new story."""
    print("\n" + "─"*10 + " Scrape Chapter Links " + "─"*10)
    story_url = input("🔗 Enter a ScribbleHub or Royal Road story URL: ").strip()
    
    # Find the correct site config
    site_config = None
    domain_key = None
    for domain, conf in site_configs.items():
        if domain in story_url:
            site_config = conf
            domain_key = domain
            break
    
    if not site_config:
        print(f"Error: No site config found for domain '{story_url.split('/')[2]}'")
        return

    # Auto-generate a project name from the URL if possible
    try:
        default_folder = story_url.strip('/').split('/')[-1].replace('-', ' ').title()
    except:
        default_folder = config.get("last_project_folder", "")
    
    project_folder_prompt = f"📂 Enter a main project folder name (e.g., '{default_folder}')"
    if default_folder:
        project_folder_prompt += f" [press Enter to use '{default_folder}']: "
    else:
        project_folder_prompt += ": "
    
    project_folder = input(project_folder_prompt).strip() or default_folder
    
    if not project_folder:
        print("⚠️ Project folder name cannot be empty."); return
    
    config["last_project_folder"] = project_folder
    save_config(config)
    
    try:
        default_chunk_size = config.get("chunk_size", 100)
        chunk_size = int(input(f"🔢 How many links per file? [default: {default_chunk_size}]: ").strip() or default_chunk_size)
        config["chunk_size"] = chunk_size
        save_config(config)
    except ValueError:
        chunk_size = config.get("chunk_size", 100)
        print(f"⚠️ Invalid number. Using default: {chunk_size}")

    print("\n🚀 Starting link scrape...")
    urls = get_all_chapter_links(story_url, site_config, headless=config.get("headless_scraping", True))
    if not urls:
        print("❌ No chapter links found."); return

    save_chunks(urls, project_folder, chunk_size=chunk_size)
    
    db = load_stories_db()
    db[project_folder] = {
        "story_url": story_url, "chunk_size": chunk_size,
        "last_chapter_count": len(urls),
        "last_scraped_date": datetime.datetime.now().isoformat(), "is_complete": False,
        "domain": domain_key
    }
    save_stories_db(db)
    print(f"\n💾 Story '{project_folder}' saved to tracking database.")

def check_for_updates(config, site_configs):
    """Checks selected active stories for new or removed chapters."""
    print("\n" + "─"*10 + " Check for Updates " + "─"*10)
    db = load_stories_db()
    if not db: print("No stories are currently being tracked."); return
        
    active_stories_dict = {name: data for name, data in db.items() if not data.get('is_complete')}
    if not active_stories_dict: print("All tracked stories are marked as complete."); return

    active_stories_list = list(active_stories_dict.items())
    
    print("\nWhich stories would you like to check for updates?")
    for i, (name, _) in enumerate(active_stories_list): print(f"  {i+1}: {name}")
    print("  all: Check all active stories"); print("  0: Back to Main Menu")

    user_input = input("\nEnter numbers (e.g., 1, 3), 'all', or '0': ").strip().lower()

    stories_to_check = []
    if user_input == '0': return
    elif user_input == 'all': stories_to_check = active_stories_list
    else:
        try:
            chosen_indices = [int(i.strip()) - 1 for i in user_input.split(',')]
            stories_to_check = [active_stories_list[i] for i in chosen_indices if 0 <= i < len(active_stories_list)]
        except (ValueError, IndexError): print("⚠️ Invalid input."); return

    if not stories_to_check: print("No valid stories selected."); return

    print(f"\nPreparing to check {len(stories_to_check)} story/stories...")
    updates_found = False
    for i, (name, data) in enumerate(stories_to_check):
        print(f"\n--- [{i+1}/{len(stories_to_check)}] Checking '{name}' ---")
        
        site_config = None
        for domain, conf in site_configs.items():
            if domain in data['story_url']:
                site_config = conf
                break
        if not site_config:
            print(f"Could not find site config for {data['story_url']}. Skipping."); continue
        
        # Pass the headless setting from the config object
        current_urls = get_all_chapter_links(data['story_url'], site_config, headless=config.get("headless_scraping", True))
        if not current_urls: print("Could not retrieve current chapters. Skipping."); continue
            
        existing_urls = read_all_links_from_folder(name)
        current_set, existing_set = set(current_urls), set(existing_urls)
        new_urls = sorted([url for url in current_urls if url not in existing_set], key=current_urls.index)
        
        if not new_urls: print("✅ No changes found."); continue

        updates_found = True
        print(f"✨ Found {len(new_urls)} new chapters.")
            
        if input("Update local files? (y/n): ").strip().lower() in ['y', 'yes']:
            save_chunks(new_urls, name, chunk_size=data['chunk_size'], start_offset=len(existing_urls))
            db[name]['last_chapter_count'] = len(current_urls)
            db[name]['last_scraped_date'] = datetime.datetime.now().isoformat()
            save_stories_db(db)
            print(f"✅ Update complete. You can now re-assemble 'chapter_list.txt' for '{name}'.")
        else: print("Update cancelled.")
    
    if not updates_found: print("\n✅ All active stories are up to date.")

def check_for_revived_links(config, site_configs):
    """Checks a project's dead links to see if they are live again."""
    print("\n" + "─"*10 + " Check for Revived Links " + "─"*10)
    db = load_stories_db()
    stories = list(db.keys())
    if not db: print("No stories tracked."); return
    print("Select a project to check:"); [print(f"  {i+1}: {name}") for i, name in enumerate(stories)]; print("  0: Back")
    try:
        choice = int(input("\nEnter choice: ").strip())
        if choice == 0: return
        project_folder = stories[choice - 1]
    except (ValueError, IndexError): print("⚠️ Invalid choice."); return

    chapter_list_path = os.path.join(project_folder, 'chapter_list.txt')
    if not os.path.exists(chapter_list_path): print(f"❌ No chapter list for '{project_folder}'."); return
    
    with open(chapter_list_path, 'r', encoding='utf-8') as f: lines = f.readlines()
    dead_links = [line.strip().replace("[DEAD LINK] ", "") for line in lines if line.startswith("[DEAD LINK]")]
    if not dead_links: print("✅ No dead links found to check."); return
    
    print(f"Checking {len(dead_links)} dead links for '{project_folder}'...")
    
    site_config = None
    for domain, conf in site_configs.items():
        if domain in db[project_folder]['story_url']:
            site_config = conf
            break
    if not site_config:
        print(f"Could not find site config for this story. Aborting."); return

    # Pass the headless setting from the config object
    live_urls = get_all_chapter_links(db[project_folder]['story_url'], site_config, headless=config.get("headless_scraping", True))
    if not live_urls: print("❌ Could not fetch live chapter list."); return
    
    revived_links = [url for url in dead_links if url in live_urls]
    if not revived_links: print("✅ None of the dead links have been revived."); return
    
    print("\nThe following links are live again:"); [print(f"  - {url}") for url in revived_links]
    if input("Restore these links? (y/n): ").strip().lower() in ['y', 'yes']:
        updated_lines = []
        for line in lines:
            stripped_line = line.strip().replace("[DEAD LINK] ", "")
            if stripped_line in revived_links:
                updated_lines.append(stripped_line + '\n')
            else:
                updated_lines.append(line)
        with open(chapter_list_path, 'w', encoding='utf-8') as f: f.writelines(updated_lines)
        print(f"✅ Restored {len(revived_links)} links.")
    else: print("Operation cancelled.")

