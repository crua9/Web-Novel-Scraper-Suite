import os
import json
import requests
from .utils import load_stories_db, save_stories_db, save_config, check_and_install_dependencies

def manage_stories():
    """Allows the user to modify or delete tracked stories."""
    while True:
        print("\n" + "─"*10 + " Manage Tracked Stories " + "─"*10)
        db = load_stories_db()
        if not db:
            print("No stories are currently being tracked.")
            return
        
        stories = list(db.keys())
        print("\nYour tracked stories:")
        for i, name in enumerate(stories):
            status = "Complete" if db[name].get('is_complete') else "Active"
            print(f"  {i+1}: {name} ({status})")
        
        print("\nOptions:")
        print("  T: Toggle Active/Complete status")
        print("  E: Edit a story's URL")
        print("  D: Delete a story entirely")
        print("  0: Back to Main Menu")
        
        action = input("\nWhat would you like to do? (T/E/D/0): ").strip().upper()
        if action == '0':
            break
            
        if action not in ['T', 'E', 'D']:
            print("⚠️ Invalid choice.")
            continue
            
        try:
            choice = int(input(f"Enter the number of the story to modify: ").strip())
            if not (1 <= choice <= len(stories)):
                print("⚠️ Invalid number.")
                continue
                
            story_name = stories[choice - 1]
            
            if action == 'T':
                db[story_name]['is_complete'] = not db[story_name].get('is_complete', False)
                save_stories_db(db)
                print(f"✅ '{story_name}' marked as {'Complete' if db[story_name]['is_complete'] else 'Active'}.")
                
            elif action == 'E':
                current_url = db[story_name].get('story_url', '')
                print(f"\nCurrent URL: {current_url}")
                new_url = input("Enter new URL (or press Enter to cancel): ").strip()
                if new_url:
                    db[story_name]['story_url'] = new_url
                    save_stories_db(db)
                    print(f"✅ URL updated for '{story_name}'.")
                    
            elif action == 'D':
                confirm = input(f"⚠️ Are you sure you want to delete '{story_name}'? (y/n): ").strip().lower()
                if confirm in ['y', 'yes']:
                    del db[story_name]
                    save_stories_db(db)
                    print(f"🗑️ '{story_name}' has been removed from tracking.")
                    
        except ValueError:
            print("⚠️ Please enter a valid number.")

def show_help_qa():
    """Displays a quick Q&A guide for common issues."""
    print("\n" + "─"*10 + " Help & Troubleshooting Q&A " + "─"*10)
    
    print("\nQ: What if a main story link goes bad or needs to be changed?")
    print("A: Open the 'stories_db.json' file in the main folder and edit the URL there, or use option '10: Manage Tracked Stories' from the main menu, press 'E' to edit, and paste the new link.")
    
    print("\nQ: What does marking a story as Active or Complete do?")
    print("A: Marking a story as 'Complete' tells the scraper to ignore it when you use '2: Check Tracked Stories for Link Updates'. Leaving it as 'Active' means the script will continue looking for new chapters for that story.")

    print("\nQ: What does '9: Update Site Configurations from GitHub' do?")
    print("A: It downloads the newest scraping rules for specific sites (like Royal Road or ScribbleHub) directly from GitHub. Websites change their code frequently, so this allows you to fix a broken site scraper instantly without having to reinstall or manually update the entire main script.")
    
    print("\nQ: The scraper keeps timing out or failing to load pages.")
    print("A: This is usually Cloudflare or a slow connection. The script has built-in retries. If it fails completely, check 'failed_chapters.txt' in your project folder. You can re-run the scraper later and it will only try to grab the ones it missed.")
    
    print("\nQ: Cloudflare keeps blocking me.")
    print("A: When the browser pops up, solve the CAPTCHA manually. The script will wait up to 5 minutes for you to do this before it times out.")
    
    print("\nQ: I want to redownload a chapter that got messed up.")
    print("A: Open 'chapter_list.txt', find the chapter, and remove the '✔' and title from the start of the line. Also, open your scraped text file and delete that chapter's text. Run the scraper again.")
    print("\n" + "─"*40)

def update_site_configs(config):
    """Downloads the latest site configuration files from GitHub."""
    from __main__ import REQUESTS_INSTALLED
    if not REQUESTS_INSTALLED:
        if not check_and_install_dependencies(['requests']):
            return
            
    print("\n" + "─"*10 + " Update Site Configurations " + "─"*10)
    repo_url = config.get('github_repo_url', "https://api.github.com/repos/crua9/Web-Novel-Scraper-Suite/contents/site_configs")
    repo_url_prompt = f"🔗 Enter GitHub API URL [default: {repo_url}]: "
    
    user_input_url = input(repo_url_prompt).strip()
    if user_input_url:
        repo_url = user_input_url
        config["github_repo_url"] = repo_url
        save_config(config)
    
    try:
        response = requests.get(repo_url)
        response.raise_for_status()
        files = response.json()
        
        updated = 0
        for file_info in files:
            if file_info['type'] == 'file' and file_info['name'].endswith('.py'):
                print(f"  -> Downloading {file_info['name']}...")
                file_content = requests.get(file_info['download_url']).text
                with open(os.path.join("site_configs", file_info['name']), 'w', encoding='utf-8') as f:
                    f.write(file_content)
                updated += 1
                
        if updated > 0:
            print(f"\n✅ Updated {updated} file(s). Restart the script for changes to take effect.")
        else:
            print("\nNo new configuration files found.")
            
    except Exception as e:
        print(f"❌ Error fetching from GitHub: {e}")
