import os
import json
import requests
from datetime import datetime
from .utils import load_stories_db, save_stories_db, save_config, check_and_install_dependencies, get_theme_colors

def manage_stories():
    """Allows the user to modify or delete tracked stories with a colored table."""
    while True:
        clr = get_theme_colors()
        P, S, G, Y, R, W = clr['P'], clr['S'], clr['G'], clr['Y'], clr['R'], clr['W']
        
        print(f"\n{P}────────── 📚 Manage Tracked Stories ──────────{W}")
        db = load_stories_db()
        if not db:
            print("No stories tracked.")
            return
        
        stories = list(db.keys())
        
        # Table Header
        print(f"{Y}{'ID':<4} {'Status':<12} {'Chaps':<7} {'Story Name'}{W}")
        print(f"{P}─" * 60 + f"{W}")

        for i, name in enumerate(stories):
            story_data = db[name]
            is_comp = story_data.get('is_complete', False)
            
            # Formatting
            status_text = f"{S}Complete{W}" if is_comp else f"{G}Active{W}"
            chapters = story_data.get('last_chapter_count', 0)
            
            # Print row
            print(f"{Y}{i+1:<4}{W} {status_text:<20} {chapters:<7} {name}")
        
        print(f"{P}─" * 60 + f"{W}")
        print(f" {G}T{W}: Toggle | {G}E{W}: Edit URL | {R}D{W}: Delete | {Y}0{W}: Back")
        
        action = input(f"\n{S}Action (T/E/D/0):{W} ").strip().upper()
        if action == '0':
            break
            
        if action not in ['T', 'E', 'D']:
            print("⚠️ Invalid choice.")
            continue
            
        try:
            choice = int(input(f"{S}Enter Story ID #: {W}").strip())
            if not (1 <= choice <= len(stories)):
                print("⚠️ Invalid ID.")
                continue
                
            story_name = stories[choice - 1]
            
            if action == 'T':
                db[story_name]['is_complete'] = not db[story_name].get('is_complete', False)
                save_stories_db(db)
                print(f"✨ Status updated for {story_name}!")
                
            elif action == 'E':
                print(f"\n🔗 Current: {db[story_name].get('story_url', '')}")
                new_url = input(f"{S}New URL (Enter to cancel): {W}").strip()
                if new_url:
                    db[story_name]['story_url'] = new_url
                    save_stories_db(db)
                    print(f"✅ URL updated!")
                    
            elif action == 'D':
                confirm = input(f"{R}🔥 Delete '{story_name}'? (y/n): {W}").strip().lower()
                if confirm == 'y':
                    del db[story_name]
                    save_stories_db(db)
                    print(f"🗑️ Story removed.")
                    
        except ValueError:
            print("⚠️ Please enter a number.")

def show_help_qa():
    """Displays a quick Q&A guide with icons."""
    clr = get_theme_colors()
    P, S, G, Y, R, W = clr['P'], clr['S'], clr['G'], clr['Y'], clr['R'], clr['W']
    
    print(f"\n{P}────────── 💡 Help & Troubleshooting ──────────{W}")
    
    qa = [
        ("🔗 Bad Story Link?", f"Use {Y}Option 10 -> E{W} to update the URL, or edit 'stories_db.json'."),
        ("📖 Active vs Complete?", f"{G}Active{W} checks for updates. {S}Complete{W} ignores story."),
        ("☁️ What is Option 9?", f"Updates scraper rules from GitHub to fix broken sites."),
        ("🔄 Redownload Chapter?", f"Edit 'chapter_list.txt', remove '✔', delete text, re-run.")
    ]
    
    for q, a in qa:
        print(f"\n{G}Q: {q}{W}\n{W}A: {a}{W}")
    
    print(f"\n{P}──────────────────────────────────────────────{W}")

def update_site_configs(config):
    """Downloads site configs with status emojis."""
    clr = get_theme_colors()
    P, S, G, Y, R, W = clr['P'], clr['S'], clr['G'], clr['Y'], clr['R'], clr['W']

    from __main__ import REQUESTS_INSTALLED
    if not REQUESTS_INSTALLED:
        if not check_and_install_dependencies(['requests']): return
            
    print(f"\n{S}☁️ Fetching rules from GitHub...{W}")
    repo_url = config.get('github_repo_url', "https://api.github.com/repos/crua9/Web-Novel-Scraper-Suite/contents/site_configs")
    
    try:
        response = requests.get(repo_url)
        response.raise_for_status()
        files = response.json()
        
        updated = 0
        for file_info in files:
            if file_info['type'] == 'file' and file_info['name'].endswith('.py'):
                print(f"  📥 {file_info['name']}...")
                content = requests.get(file_info['download_url']).text
                with open(os.path.join("site_configs", file_info['name']), 'w', encoding='utf-8') as f:
                    f.write(content)
                updated += 1
                
        print(f"\n✅ {G}Updated {updated} files.{W}")
    except Exception as e:
        print(f"❌ {R}Update failed: {e}{W}")
