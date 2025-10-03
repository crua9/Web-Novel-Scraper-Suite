import os
import json
import subprocess
import sys
import importlib
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from urllib.parse import urljoin, urlparse

# --- Configuration Management ---

def get_config_path():
    """Returns the absolute path to the config.json file."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')

def load_config():
    """Loads the configuration from config.json, creating it if it doesn't exist."""
    config_path = get_config_path()
    if not os.path.exists(config_path):
        print("Config file not found. Creating a default 'config.json'.")
        default_config = {
            "headless_scraping": True,
            "tracked_stories": {},
            "github_pat": "",
            "chunk_size": 50
        }
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=4)
        return default_config
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("⚠️ Error: config.json is corrupted. Please fix or delete it.")
        sys.exit(1)

def save_config(config):
    """Saves the given configuration object to config.json."""
    try:
        with open(get_config_path(), 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"❌ Error saving configuration: {e}")

# --- Dependency Management ---

def install_package(package):
    """Installs a package using pip and handles Playwright-specific setup."""
    try:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
        if 'playwright' in package:
            print("Playwright library installed. Now installing necessary browser drivers...")
            subprocess.check_call([sys.executable, '-m', 'playwright', 'install'])
            print("✅ Playwright browser drivers installed successfully.")
        print(f"✅ Successfully installed {package}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing {package}: {e}")
        return False
    except Exception as e:
        print(f"❌ An unexpected error occurred during installation: {e}")
        return False

def check_and_install_dependencies(packages):
    missing_packages = [pkg for pkg in packages if importlib.util.find_spec(pkg.replace('-', '_')) is None]
    if not missing_packages:
        return True
    print("\n--- ⚠️ Missing Libraries for this Feature ---")
    for pkg in missing_packages:
        print(f"  - {pkg}")
    if input("\nInstall them now? (y/n): ").strip().lower() in ['y', 'yes']:
        if all(install_package(pkg) for pkg in missing_packages):
            print("\n✅ All required libraries are now installed.")
            return True
        else:
            print("\n❌ Installation failed for one or more libraries.")
            return False
    else:
        print("Installation skipped.")
        return False

# --- Site Configuration Loading ---

SITE_CONFIGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'site_configs')

def load_site_configs():
    configs = {}
    if not os.path.exists(SITE_CONFIGS_DIR):
        os.makedirs(SITE_CONFIGS_DIR)
        return configs
    for filename in os.listdir(SITE_CONFIGS_DIR):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = filename[:-3]
            try:
                module = importlib.import_module(f'site_configs.{module_name}')
                if hasattr(module, 'DOMAIN'):
                    configs[module.DOMAIN] = {
                        'get_links': module.get_links,
                        'get_content': module.get_content,
                        'reverse_chapters': getattr(module, 'REVERSE_CHAPTERS', False)
                    }
            except Exception as e:
                print(f"❌ Error loading site configuration from {filename}: {e}")
    return configs

# --- File System Helpers ---
def ensure_directory_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)

def save_chunks(links, story_folder, chunk_size=50, start_offset=0):
    links_dir = os.path.join(story_folder, 'links')
    ensure_directory_exists(links_dir)
    print(f"\nSaving links to folder: '{links_dir}'")
    num_links = len(links)
    for i in range(0, num_links, chunk_size):
        chunk = links[i:i + chunk_size]
        start_num = start_offset + i + 1
        end_num = start_offset + i + len(chunk)
        sanitized_folder_name = "".join(c for c in os.path.basename(story_folder) if c.isalnum() or c in (' ', '_', '-')).strip()
        filename = f"{sanitized_folder_name} Links {start_num}-{end_num}.txt"
        filepath = os.path.join(links_dir, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(chunk) + '\n')
            print(f"  - Saved chunk {start_num}-{end_num} to '{filename}'")
        except IOError as e:
            print(f"❌ Error writing to file {filepath}: {e}")
    print("✅ All link files saved.")

def read_all_links_from_folder(story_folder):
    links_dir = os.path.join(story_folder, 'links')
    all_links = []
    if not os.path.exists(links_dir):
        return []
    link_files = sorted(
        [f for f in os.listdir(links_dir) if f.endswith('.txt')],
        key=lambda x: int(re.search(r'(\d+)-\d+\.txt$', x).group(1)) if re.search(r'(\d+)-\d+\.txt$', x) else 0
    )
    for filename in link_files:
        filepath = os.path.join(links_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                all_links.extend([line.strip() for line in f if line.strip()])
        except IOError as e:
            print(f"❌ Error reading file {filepath}: {e}")
    return all_links

def parse_output_file(story_folder, file_format):
    """Generates a standard output file path within a project folder."""
    base_name = os.path.basename(story_folder)
    sanitized_name = "".join(c for c in base_name if c.isalnum() or c in (' ', '_', '-')).strip()
    return os.path.join(story_folder, f"{sanitized_name}.{file_format}")

# --- Story Database Management ---
def get_stories_db_path():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'stories_db.json')

def load_stories_db():
    db_path = get_stories_db_path()
    if not os.path.exists(db_path):
        return {}
    try:
        with open(db_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("⚠️ Error: stories_db.json is corrupted. Returning empty database.")
        return {}

def save_stories_db(db):
    try:
        with open(get_stories_db_path(), 'w') as f:
            json.dump(db, f, indent=4)
    except Exception as e:
        print(f"❌ Error saving story database: {e}")

# --- Web Scraping Helpers ---
def get_all_chapter_links(story_url, site_config, headless=True):
    """
    Launches a browser and scrapes chapter links from a story URL using
    the provided site configuration.
    """
    if not site_config:
        domain = urlparse(story_url).netloc.replace('www.', '')
        print(f"Error: No site configuration was provided for the domain '{domain}'")
        return []

    print(f"Scraping chapter links from: {story_url}")
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()
            page.goto(story_url, wait_until='domcontentloaded', timeout=60000)
            
            all_links = site_config['get_links'](page)
            
            if site_config.get('reverse_chapters'):
                all_links.reverse()
            browser.close()
            print(f"\n✅ Finished scraping. Found {len(all_links)} unique chapter links.")
            return list(dict.fromkeys(all_links))
        except Exception as e:
            print(f"❌ An unexpected error occurred during link scraping: {e}")
            return []

def scrape_chapter_content(page, url, site_configs, timeout=60000):
    """
    Finds the correct site configuration and calls its get_content function.
    This acts as a router to the site-specific scraping logic.
    """
    raw_domain = urlparse(url).netloc
    domain = raw_domain.replace('www.', '')
    
    site_config = site_configs.get(domain) or site_configs.get(raw_domain)
    
    if site_config:
        # Pass the timeout value to the specific get_content function
        return site_config['get_content'](page, url, timeout)
        
    return "Error: No config for {domain}", None, None


# --- UI Helpers ---
def print_progress_bar(iteration, total, prefix='', suffix='', length=50, fill='█'):
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    sys.stdout.write(f'\r{prefix} |{bar}| {percent}% {suffix}')
    sys.stdout.flush()
    if iteration == total:
        print()

