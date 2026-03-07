import os
import json
import requests
from .utils import load_stories_db, save_stories_db, save_config, check_and_install_dependencies

def manage_stories():
    """Allows the user to mark stories as complete or active."""
    print("\n" + "─"*10 + " Manage Tracked Stories " + "─"*10)
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
            choice = int(input("\nEnter number to toggle status: ").strip())
            if choice == 0:
                break
            if 1 <= choice <= len(stories):
                story_name = stories[choice - 1]
                db[story_name]['is_complete'] = not db[story_name].get('is_complete', False)
                save_stories_db(db)
                print(f"✅ '{story_name}' marked as {'Complete' if db[story_name]['is_complete'] else 'Active'}.")
            else:
                print("⚠️ Invalid number.")
        except ValueError:
            print("⚠️ Please enter a valid number.")

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

def sync_db_with_text():
    """Exports DB to a text file, lets user edit it, then imports changes back."""
    print("\n" + "─"*10 + " Sync Database via Text File " + "─"*10)
    db = load_stories_db()
    txt_file = "tracked_stories_list.txt"
    
    # Export current DB to text
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write("# Delete lines to remove stories. Do not change the names of the ones you keep.\n")
        for story in db.keys():
            f.write(f"{story}\n")
            
    print(f"✅ Exported your stories to '{txt_file}'.")
    input("Open that file, delete the stories you don't want, save it, and press Enter here...")
    
    # Import back and delete removed ones
    try:
        with open(txt_file, "r", encoding="utf-8") as f:
            kept_stories = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            
        removed = 0
        for story in list(db.keys()):
            if story not in kept_stories:
                del db[story]
                removed += 1
                
        save_stories_db(db)
        print(f"✅ Synced! Removed {removed} stories from your tracking database.")
    except Exception as e:
        print(f"❌ Error reading text file: {e}")
