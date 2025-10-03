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
from playwright.sync_api import sync_playwright, TimeoutError

# --- Constants ---
STORIES_DB_FILE = "stories.json"
CONFIG_FILE = "config.json"
SITE_CONFIGS_DIR = "site_configs"

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

def get_all_chapter_links(story_url, site_configs):
    """Uses the appropriate site config to scrape all chapter links."""
    site_handler = next((config for domain, config in site_configs.items() if domain in story_url), None)
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

def scrape_chapter_content(page, url, site_configs):
    """Uses the appropriate site config to scrape content."""
    site_handler = next((config for domain, config in site_configs.items() if domain in url), None)
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

def install_package(package_name, install_command):
    """Attempts to install a missing Python package."""
    print(f"\nAttempting to install '{package_name}'...")
    try:
        process = subprocess.run(install_command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ Successfully installed '{package_name}'.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"--- ❌ ERROR installing '{package_name}' ---"); print(e.stderr); return False

def check_and_install_dependencies(dependencies):
    """Checks for a list of dependencies and offers to install them."""
    # This function is now also a utility, called from the main script.
    # It relies on the global flags set at startup.
    required = {
        'playwright': ('playwright', 'pip install playwright'),
        'ebooklib': ('EbookLib', 'pip install EbookLib'),
        'gtts': ('gTTS', 'pip install gTTS'),
        'requests': ('requests', 'pip install requests')
    }
    
    # We need to access the global flags to check status
    from __main__ import PLAYWRIGHT_INSTALLED, EBOOKLIB_INSTALLED, GTTS_INSTALLED, REQUESTS_INSTALLED
    
    missing = [dep for dep in dependencies if not locals().get(f"{dep.upper()}_INSTALLED")]
    
    if missing:
        print("\n--- ⚠️ Missing Libraries for this Feature ---")
        for pkg_key in missing:
            print(f"  - {required[pkg_key][0]}")
        
        if input("\nInstall them now? (y/n): ").strip().lower() in ['y', 'yes']:
            ok = all(install_package(name, cmd) for pkg_key in missing for name, cmd in [required[pkg_key]])
            if 'playwright' in missing and ok:
                ok = install_package("Playwright Browsers", "playwright install")
            
            if ok:
                print("\n✅ Dependencies installed. Script will now restart to apply changes.")
                os.execv(sys.executable, ['python'] + sys.argv)
                sys.exit()
            else:
                print("\n❌ Some dependencies failed to install.")
                return False
        else:
            print("Installation skipped.")
            return False
    return True
