import json
import re
import math
import sys
import os
import datetime
import time
import importlib
import shutil
import subprocess
import hashlib
import urllib.request

# --- Dependency Check & Global Flags ---
# These flags are set by the startup check to enable/disable features.
PLAYWRIGHT_INSTALLED = False
EBOOKLIB_INSTALLED = False
GTTS_INSTALLED = False
REQUESTS_INSTALLED = False

# --- Constants ---
STORIES_DB_FILE = "stories.json"
CONFIG_FILE = "config.json"
SITE_CONFIGS_DIR = "site_configs"
SELF_UPDATE_URL = "https://raw.githubusercontent.com/crua9/Web-Novel-Scraper-Suite/main/Web-Novel-Scraper-Suite.py"
SITE_CONFIGS = {}

# --- Configuration & Database Functions ---
def load_config():
    """Loads user preferences from config.json, providing defaults if not found."""
    default_config = {
        "chunk_size": 100,
        "last_project_folder": "",
        "github_repo_url": "https://api.github.com/repos/crua9/Web-Novel-Scraper-Suite/contents/site_configs"
    }
    if not os.path.exists(CONFIG_FILE):
        return default_config
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            for key, value in default_config.items():
                config.setdefault(key, value)
            return config
    except (json.JSONDecodeError, FileNotFoundError):
        return default_config

def save_config(config):
    """Saves user preferences to config.json."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

def load_stories_db():
    """Loads the stories database from stories.json."""
    if not os.path.exists(STORIES_DB_FILE):
        return {}
    try:
        with open(STORIES_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("Warning: stories.json is corrupted or empty. Starting fresh.")
        return {}

def save_stories_db(db):
    """Saves the stories database with an automatic backup."""
    if os.path.exists(STORIES_DB_FILE):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = "backups"
        os.makedirs(backup_dir, exist_ok=True)
        try:
            shutil.copy(STORIES_DB_FILE, os.path.join(backup_dir, f"stories_{timestamp}.json"))
            print(f"\n✅ Created backup of '{STORIES_DB_FILE}' in 'backups' folder.")
        except Exception as e:
            print(f"⚠️ Could not create backup: {e}")
    with open(STORIES_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4)

# --- Dynamic Site Config Loading ---
def load_site_configs():
    """Dynamically loads site-specific scraping logic from the site_configs directory."""
    configs = {}
    if not os.path.exists(SITE_CONFIGS_DIR):
        print(f"Directory '{SITE_CONFIGS_DIR}' not found. It will be created.")
        os.makedirs(SITE_CONFIGS_DIR)
        return configs
    for filename in os.listdir(SITE_CONFIGS_DIR):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = f"{SITE_CONFIGS_DIR}.{filename[:-3]}"
            try:
                if module_name in sys.modules:
                    module = importlib.reload(sys.modules[module_name])
                else:
                    module = importlib.import_module(module_name)
                if hasattr(module, "DOMAIN"):
                    configs[module.DOMAIN] = module
                    print(f"✅ Loaded config for: {module.DOMAIN}")
            except Exception as e:
                print(f"❌ Failed to load config from '{filename}': {e}")
    return configs

# --- General Helper & Scraping Functions ---
def print_progress_bar(iteration, total, prefix='', suffix='', length=50, fill='█'):
    """Displays a terminal progress bar."""
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    sys.stdout.write(f'\r{prefix} |{bar}| {percent}% {suffix}')
    sys.stdout.flush()
    if iteration == total:
        print()

def get_all_chapter_links(story_url):
    """Uses the appropriate site config to scrape all chapter links."""
    site_handler = next((config for domain, config in SITE_CONFIGS.items() if domain in story_url), None)
    if not site_handler:
        print(f"❌ No configuration found for the domain in URL: {story_url}"); return []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        try:
            urls = site_handler.get_links(page, story_url)
            if hasattr(site_handler, 'REVERSE_CHAPTERS') and site_handler.REVERSE_CHAPTERS:
                print("🔃 Reversing chapter order to chronological...")
                urls.reverse()
            return urls
        except Exception as e:
            print(f"❌ An error occurred during link scraping: {e}"); return []
        finally:
            browser.close()

def scrape_chapter_content(page, url):
    """Uses the appropriate site config to scrape content."""
    site_handler = next((config for domain, config in SITE_CONFIGS.items() if domain in url), None)
    if not site_handler:
        return f"Unsupported site: {url}", None, None
    return site_handler.get_content(page, url)

def save_chunks(urls, base_name, chunk_size, output_dir, start_offset=0):
    """Saves a list of URLs into multiple text files."""
    if not urls: return
    total_new = len(urls)
    chunks = math.ceil(total_new / chunk_size)
    print(f"\n📦 Saving {total_new} links into {chunks} file(s) in '{output_dir}'...")
    print_progress_bar(0, chunks, prefix='Progress:', suffix='Complete', length=50)
    for i in range(chunks):
        start_index = i * chunk_size
        end_index = min(start_index + chunk_size, total_new)
        chunk_data = urls[start_index:end_index]
        start_chap = start_offset + start_index + 1
        end_chap = start_offset + end_index
        filename = os.path.join(output_dir, f"{base_name} {start_chap}-{end_chap}.txt")
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(chunk_data) + "\n")
        time.sleep(0.05)
        print_progress_bar(i + 1, chunks, prefix='Progress:', suffix='Complete', length=50)
    print()

def parse_output_file(filepath):
    """Reads an existing story file and parses its chapters into a dictionary."""
    chapters = {}
    if not os.path.exists(filepath): return chapters
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    pattern = re.compile(r"---\s*(.*?)\s*---\n\n(.*?)(?=\n---|\Z)", re.DOTALL)
    matches = pattern.findall(content)
    for title, text in matches:
        chapters[title.strip()] = text.strip()
    return chapters

def build_final_file(output_filepath, all_chapters_data, ordered_titles):
    """Writes the final output file from scratch, ensuring correct order."""
    print(f"\nRebuilding {os.path.basename(output_filepath)} in the correct order...")
    with open(output_filepath, "w", encoding="utf-8") as f:
        for title in ordered_titles:
            if title and title in all_chapters_data:
                f.write(f"\n--- {title} ---\n\n{all_chapters_data[title]}\n")
    print("✅ Final file built successfully.")

def read_all_links_from_folder(folder_path):
    """Reads all URLs from all .txt files in a directory, sorted numerically."""
    all_urls = []
    if not os.path.exists(folder_path): return all_urls
    try:
        files = sorted(
            [f for f in os.listdir(folder_path) if f.endswith('.txt') and re.search(r'\d+-\d+\.txt$', f)],
            key=lambda x: int(re.search(r'(\d+)-\d+\.txt$', x).group(1))
        )
        for filename in files:
            with open(os.path.join(folder_path, filename), 'r', encoding='utf-8') as f:
                all_urls.extend([line.strip() for line in f if line.strip()])
    except (AttributeError, ValueError, TypeError):
        files = sorted([f for f in os.listdir(folder_path) if f.endswith('.txt')])
        for filename in files:
            with open(os.path.join(folder_path, filename), 'r', encoding='utf-8') as f:
                all_urls.extend([line.strip() for line in f if line.strip()])
    except Exception as e:
        print(f"Could not read link files: {e}")
    return all_urls

# --- [FULL MENU FUNCTIONS START] ---
def scrape_new_story_links(config):
    """Guides user through scraping links for a new story."""
    print("\n" + "─"*10 + " Scrape Chapter Links " + "─"*10)
    story_url = input("🔗 Enter a ScribbleHub or Royal Road story URL: ").strip()
    if not any(domain in story_url for domain in SITE_CONFIGS):
        print("⚠️ Invalid or unsupported URL."); return

    default_folder = config.get("last_project_folder", "")
    project_folder_prompt = f"📂 Enter a main project folder name (e.g., 'World Keeper')"
    if default_folder:
        project_folder_prompt += f" [press Enter to use '{default_folder}']: "
    else:
        project_folder_prompt += ": "
    
    project_folder = input(project_folder_prompt).strip() or default_folder
    
    if not project_folder:
        print("⚠️ Project folder name cannot be empty."); return
    
    config["last_project_folder"] = project_folder
    save_config(config)
    
    output_dir = os.path.join(project_folder, "links")
    os.makedirs(output_dir, exist_ok=True)
    print(f"\n✅ Link files will be saved in: '{output_dir}'")
    
    base_name = input("📝 What should the link files be named? (e.g. World Keeper Links): ").strip()
    if not base_name:
        print("⚠️ File name cannot be empty."); return
        
    try:
        default_chunk_size = config.get("chunk_size", 100)
        chunk_size = int(input(f"🔢 How many links per file? [default: {default_chunk_size}]: ").strip() or default_chunk_size)
        config["chunk_size"] = chunk_size
        save_config(config)
    except ValueError:
        chunk_size = config.get("chunk_size", 100)
        print(f"⚠️ Invalid number. Using default: {chunk_size}")

    print("\n🚀 Starting link scrape...")
    urls = get_all_chapter_links(story_url)
    if not urls:
        print("❌ No chapter links found."); return

    save_chunks(urls, base_name, chunk_size, output_dir)
    
    db = load_stories_db()
    db[project_folder] = {
        "story_url": story_url, "base_name": base_name, "chunk_size": chunk_size,
        "output_dir": output_dir, "last_chapter_count": len(urls),
        "last_scraped_date": datetime.datetime.now().isoformat(), "is_complete": False
    }
    save_stories_db(db)
    print(f"\n💾 Story '{project_folder}' saved to tracking database.")

def check_for_updates():
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
        except ValueError: print("⚠️ Invalid input."); return

    if not stories_to_check: print("No valid stories selected."); return

    print(f"\nPreparing to check {len(stories_to_check)} story/stories...")
    updates_found = False
    for i, (name, data) in enumerate(stories_to_check):
        print(f"\n--- [{i+1}/{len(stories_to_check)}] Checking '{name}' ---")
        current_urls = get_all_chapter_links(data['story_url'])
        if not current_urls: print("Could not retrieve current chapters. Skipping."); continue
            
        existing_urls = read_all_links_from_folder(data['output_dir'])
        current_set, existing_set = set(current_urls), set(existing_urls)
        new_urls = sorted([url for url in current_urls if url not in existing_set], key=current_urls.index)
        removed_urls = list(existing_set - current_set)

        if not new_urls and not removed_urls: print("✅ No changes found."); continue

        updates_found = True
        print(f"✨ Found Changes for '{name}':")
        if new_urls: print(f"  + {len(new_urls)} new chapters added.")
        if removed_urls: print(f"  - {len(removed_urls)} chapters removed.")
            
        if input("Update local files? (y/n): ").strip().lower() in ['y', 'yes']:
            if removed_urls:
                print("\nChapters have been removed from the website.")
                if input("Earmark them as [DEAD LINK] in 'chapter_list.txt'? (y/n): ").strip().lower() in ['y', 'yes']:
                    chapter_list_path = os.path.join(name, 'chapter_list.txt')
                    if os.path.exists(chapter_list_path):
                        with open(chapter_list_path, 'r+', encoding='utf-8') as f:
                            lines = f.readlines(); f.seek(0); f.truncate()
                            for line in lines:
                                if any(removed in line for removed in removed_urls) and not line.startswith('[DEAD LINK]'):
                                    f.write(f"[DEAD LINK] {line.strip()}\n")
                                else:
                                    f.write(line)
                        print(f"✅ Earmarked {len(removed_urls)} dead links in '{chapter_list_path}'.")
                    else: print(f"⚠️ Could not find '{chapter_list_path}'.")

            if new_urls:
                print("Appending new chapters...")
                last_chap_num = len(existing_urls)
                save_chunks(new_urls, data['base_name'], data['chunk_size'], data['output_dir'], start_offset=last_chap_num)

            db[name]['last_chapter_count'] = len(current_urls)
            db[name]['last_scraped_date'] = datetime.datetime.now().isoformat()
            save_stories_db(db)
            print(f"✅ Update complete. You can now re-assemble 'chapter_list.txt' for '{name}'.")
        else: print("Update cancelled.")
    
    if not updates_found: print("\n✅ All active stories are up to date.")

def check_for_revived_links():
    """Checks a project's dead links to see if they are live again."""
    print("\n" + "─"*10 + " Check for Revived Links " + "─"*10)
    db = load_stories_db(); stories = list(db.keys())
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
    live_urls = get_all_chapter_links(db[project_folder]['story_url'])
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

def assemble_chapter_list():
    """Assembles or updates a master chapter_list.txt from individual link files."""
    print("\n" + "─"*10 + " Assemble `chapter_list.txt` " + "─"*10)
    db = load_stories_db(); stories = list(db.keys())
    if not db: print("No stories tracked."); return
    print("Select a project:"); [print(f"  {i+1}: {name}") for i, name in enumerate(stories)]; print("  0: Back")
    try:
        choice = int(input("\nEnter choice: ").strip())
        if choice == 0: return
        project_folder = stories[choice - 1]
    except (ValueError, IndexError): print("⚠️ Invalid choice."); return

    links_dir = os.path.join(project_folder, "links")
    chapter_list_path = os.path.join(project_folder, "chapter_list.txt")
    progress_path = os.path.join(links_dir, "_added_links_tracker.json")

    if not os.path.exists(links_dir): print(f"❌ Links directory not found."); return

    try:
        with open(progress_path, 'r', encoding='utf-8') as f: processed_files = set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError): processed_files = set()

    all_link_files = set(f for f in os.listdir(links_dir) if f.endswith('.txt') and re.search(r'\d+-\d+\.txt$', f))
    new_files = sorted(list(all_link_files - processed_files), key=lambda x: int(re.search(r'(\d+)-\d+\.txt$', x).group(1)))

    if not new_files: print(f"\n✅ `chapter_list.txt` is already up-to-date."); return
    print("\nNew link files found:"); [print(f"  - {f}") for f in new_files]
    
    if input(f"\nAppend these to '{os.path.basename(chapter_list_path)}'? (y/n): ").strip().lower() in ['y', 'yes']:
        with open(chapter_list_path, "a", encoding="utf-8") as master_file:
            for filename in new_files:
                with open(os.path.join(links_dir, filename), "r", encoding="utf-8") as chunk_file:
                    master_file.write(chunk_file.read())
                processed_files.add(filename)
        with open(progress_path, "w", encoding="utf-8") as f: json.dump(list(processed_files), f, indent=4)
        print("✅ Successfully updated `chapter_list.txt`.")
    else: print("Operation cancelled.")

def scrape_story_content(config):
    """Guides user through scraping content for a tracked story."""
    print("\n" + "─"*10 + " Scrape Story Content " + "─"*10)
    db = load_stories_db(); stories = list(db.keys())
    if not db: print("No stories tracked."); return
    print("Select a project:"); [print(f"  {i+1}: {name}") for i, name in enumerate(stories)]; print("  0: Back")
    try:
        choice = int(input("\nEnter choice: ").strip())
        if choice == 0: return
        project_folder = stories[choice - 1]
    except (ValueError, IndexError): print("⚠️ Invalid choice."); return

    chapter_list_path = os.path.join(project_folder, "chapter_list.txt")
    if not os.path.exists(chapter_list_path):
        print(f"❌ '{os.path.basename(chapter_list_path)}' not found. Please assemble it first."); return
        
    master_url_list = [line.strip() for line in open(chapter_list_path, 'r', encoding='utf-8') if line.strip() and not line.startswith("[DEAD LINK]")]

    output_filename = input(f"\nEnter output filename (e.g., {project_folder} Story.txt): ").strip() or f"{project_folder} Story.txt"
    output_filepath = os.path.join(project_folder, output_filename)

    save_notes = input("\nSave author's notes? (y/n): ").strip().lower() in ['y', 'yes']
    notes_filepath = ""
    if save_notes:
        base, ext = os.path.splitext(output_filename)
        notes_filepath = os.path.join(project_folder, f"{base} Author Notes{ext}")
        print(f"🗒️ Notes will be saved to: {os.path.basename(notes_filepath)}")

    progress_file = os.path.join(project_folder, "_scrape_progress.json")
    try:
        with open(progress_file, 'r', encoding='utf-8') as f: progress_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): progress_data = {}

    urls_to_scrape = [url for url in master_url_list if url not in progress_data]

    if not urls_to_scrape:
        print("\n✅ All chapters appear to be scraped already.")
        all_chapters_data = parse_output_file(output_filepath)
        if all_chapters_data:
            ordered_titles = [progress_data.get(url) for url in master_url_list if progress_data.get(url)]
            build_final_file(output_filepath, all_chapters_data, ordered_titles)
        return

    print("\n🧠 Heads up:"); print("* A browser window will open — do NOT minimize or close it.")
    input("\nPress Enter to begin scraping...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False); page = browser.new_page()
        total_to_scrape = len(urls_to_scrape)
        print_progress_bar(0, total_to_scrape, prefix='Content Scraping:', suffix='Complete', length=50)

        for i, url in enumerate(urls_to_scrape):
            title, content, notes = scrape_chapter_content(page, url)
            if title and content is not None and not title.startswith("Error:"):
                progress_data[url] = title
                with open(output_filepath, "a", encoding="utf-8") as f: f.write(f"\n--- {title} ---\n\n{content}\n")
                if save_notes and notes:
                    with open(notes_filepath, "a", encoding="utf-8") as f: f.write(f"\n--- {title} ---\n\n{notes}\n")
            else: print(f"\nSkipping failed URL: {url} ({title})")
            with open(progress_file, 'w', encoding='utf-8') as f: json.dump(progress_data, f, indent=4)
            print_progress_bar(i + 1, total_to_scrape, prefix='Content Scraping:', suffix='Complete', length=50)
        browser.close()

    all_chapters_data = parse_output_file(output_filepath)
    ordered_titles = [progress_data.get(url) for url in master_url_list if progress_data.get(url)]
    build_final_file(output_filepath, all_chapters_data, ordered_titles)
    print("\n🎉 Content scraping complete.")

def manage_stories():
    """Allows the user to mark stories as complete or active."""
    print("\n" + "─"*10 + " Manage Tracked Stories " + "─"*10)
    db = load_stories_db()
    if not db: print("No stories are currently being tracked."); return
    stories = list(db.keys())
    while True:
        print("\nYour tracked stories:")
        for i, name in enumerate(stories):
            status = "Complete" if db[name].get('is_complete') else "Active"
            print(f"  {i+1}: {name} ({status})")
        print("  0: Back to Main Menu")
        try:
            choice = int(input("\nEnter number to toggle status: ").strip())
            if choice == 0: break
            if 1 <= choice <= len(stories):
                story_name = stories[choice - 1]
                db[story_name]['is_complete'] = not db[story_name].get('is_complete', False)
                save_stories_db(db)
                print(f"✅ '{story_name}' marked as {'Complete' if db[story_name]['is_complete'] else 'Active'}.")
            else: print("⚠️ Invalid number.")
        except ValueError: print("⚠️ Please enter a valid number.")

def update_site_configs(config):
    """Downloads the latest site configuration files from GitHub."""
    if not REQUESTS_INSTALLED:
        if not check_and_install_dependencies(['requests']): return
    print("\n" + "─"*10 + " Update Site Configurations " + "─"*10)
    repo_url = input(f"🔗 Enter GitHub API URL [default: {config.get('github_repo_url')}]: ").strip() or config.get('github_repo_url')
    config["github_repo_url"] = repo_url; save_config(config)
    try:
        response = requests.get(repo_url); response.raise_for_status(); files = response.json()
        updated = 0
        for file_info in files:
            if file_info['type'] == 'file' and file_info['name'].endswith('.py'):
                print(f"  -> Downloading {file_info['name']}...")
                file_content = requests.get(file_info['download_url']).text
                with open(os.path.join(SITE_CONFIGS_DIR, file_info['name']), 'w', encoding='utf-8') as f: f.write(file_content)
                updated += 1
        if updated > 0: print(f"\n✅ Updated {updated} file(s). Restart for changes to take effect.")
        else: print("\nNo new configuration files found.")
    except Exception as e: print(f"❌ Error fetching from GitHub: {e}")

def create_epub_from_files():
    """Combines one or more text files into a single EPUB ebook."""
    if not EBOOKLIB_INSTALLED:
        if not check_and_install_dependencies(['ebooklib']): return
    print("\n" + "─"*10 + " Create EPUB Ebook " + "─"*10)
    print("This feature is not yet implemented.")

def create_edge_html_from_file():
    """Converts a story text file into an HTML file for Edge's Read Aloud."""
    print("\n" + "─"*10 + " Create HTML for Edge " + "─"*10)
    print("This feature is not yet implemented.")

def create_mp3s_from_file():
    """Converts a story text file into chapter-by-chapter MP3 audio files."""
    if not GTTS_INSTALLED:
        if not check_and_install_dependencies(['gtts']): return
    print("\n" + "─"*10 + " Create MP3 Audio Files " + "─"*10)
    print("This feature is not yet implemented.")

# --- [FULL MENU FUNCTIONS END] ---

def main_menu():
    """Displays the main menu and handles user choices."""
    config = load_config()
    while True:
        print("\n" + "─"*10 + " 📘 Web Novel Scraper Suite 📘 " + "─"*10)
        print("--- Link Management ---")
        print("1: Scrape Chapter Links for a New Story")
        print("2: Check Tracked Stories for Link Updates")
        print("3: Check for Revived Links in a Project")
        print("--- Content Management ---")
        print("4: Assemble `chapter_list.txt` from Link Files")
        print("5: Scrape Story Content from `chapter_list.txt`")
        print("--- Conversion Tools ---")
        print("6: Create EPUB Ebook from Story File(s)")
        print("7: Create HTML file for Edge Read Aloud")
        print("8: Create MP3 Audio Files from Story File")
        print("--- Administration ---")
        print("9: Update Site Configurations from GitHub")
        print("10: Manage Tracked Stories (Mark as Complete/Active)")
        print("11: Exit")
        choice = input("Enter your choice (1-11): ").strip()

        # Route to the correct function, with on-demand dependency checks
        if choice == '1': 
            if check_and_install_dependencies(['playwright']): scrape_new_story_links(config)
        elif choice == '2': 
            if check_and_install_dependencies(['playwright']): check_for_updates()
        elif choice == '3':
             if check_and_install_dependencies(['playwright']): check_for_revived_links()
        elif choice == '4': assemble_chapter_list()
        elif choice == '5': 
            if check_and_install_dependencies(['playwright']): scrape_story_content(config)
        elif choice == '6': 
            if check_and_install_dependencies(['ebooklib']): create_epub_from_files()
        elif choice == '7': create_edge_html_from_file()
        elif choice == '8': 
            if check_and_install_dependencies(['gtts']): create_mp3s_from_file()
        elif choice == '9': 
            if check_and_install_dependencies(['requests']): update_site_configs(config)
        elif choice == '10': manage_stories()
        elif choice == '11': print("Goodbye!"); break
        else: print("⚠️ Invalid choice.")
        input("\nPress Enter to return to the menu...")

# --- Startup, Self-Update, and Installation ---
def install_package(package_name, install_command):
    """Attempts to install a missing Python package."""
    print(f"\nAttempting to install '{package_name}'...")
    try:
        process = subprocess.run(install_command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ Successfully installed '{package_name}'.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"--- ❌ ERROR installing '{package_name}' ---"); print(e.stderr); return False

def check_for_self_update():
    """Checks GitHub for a new version of the main script and offers to update."""
    if not REQUESTS_INSTALLED: return
    try:
        print("\nChecking for application updates...")
        with urllib.request.urlopen(SELF_UPDATE_URL) as response: latest_code = response.read()
        with open(sys.argv[0], 'rb') as f: current_code = f.read()
        if hashlib.sha256(latest_code).hexdigest() != hashlib.sha256(current_code).hexdigest():
            print("✨ A new version of the script is available!")
            if input("Update and restart now? (y/n): ").strip().lower() in ['y', 'yes']:
                with open("_update.py", "wb") as f: f.write(latest_code)
                updater_script = f"""@echo off\necho Updating script...\ntimeout /t 2 /nobreak > nul\nmove /Y "_update.py" "{os.path.basename(sys.argv[0])}"\necho Update complete. Restarting...\nstart "" python "{os.path.basename(sys.argv[0])}"\ndel "%~f0" """
                with open("updater.bat", "w") as f: f.write(updater_script)
                subprocess.Popen("updater.bat", shell=True); sys.exit()
        else: print("✅ Your script is up-to-date.")
    except Exception as e: print(f"⚠️ Could not check for updates: {e}")

def run_startup_checks():
    """Performs initial checks for all dependencies and offers to install them."""
    print("🚀 Running startup checks...")
    
    # Check for core playwright dependency first. If missing, prompt install.
    try: import playwright; global PLAYWRIGHT_INSTALLED; PLAYWRIGHT_INSTALLED = True
    except ImportError: pass

    if not PLAYWRIGHT_INSTALLED:
        if not check_and_install_dependencies(['playwright']):
            return False

    # Check for optional dependencies but don't install yet
    try: from ebooklib import epub; global EBOOKLIB_INSTALLED; EBOOKLIB_INSTALLED = True
    except ImportError: pass
    try: from gtts import gTTS; global GTTS_INSTALLED; GTTS_INSTALLED = True
    except ImportError: pass
    try: import requests; global REQUESTS_INSTALLED; REQUESTS_INSTALLED = True
    except ImportError: pass
    
    check_for_self_update()

    global SITE_CONFIGS
    SITE_CONFIGS = load_site_configs()
    if not SITE_CONFIGS and REQUESTS_INSTALLED:
        print("\n⚠️ No site configurations found.")
        if input("Download the default configurations from GitHub now? (y/n): ").strip().lower() in ['y', 'yes']:
            update_site_configs(load_config())
            SITE_CONFIGS = load_site_configs()
            
    print("\n✅ Startup checks passed.")
    return True

if __name__ == "__main__":
    if run_startup_checks():
        try:
            main_menu()
        except Exception as e:
            print(f"\n--- An Unexpected Error Occurred: {e} ---")
            import traceback
            traceback.print_exc()
    input("\nPress Enter to exit.")

