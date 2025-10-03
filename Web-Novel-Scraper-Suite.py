import sys
import os
import importlib
import subprocess

# --- Import from our new modules ---
# This corrected structure ensures all functions are imported from their correct files.
from modules.utils import (
    load_config, save_config, install_package, check_and_install_dependencies,
    load_site_configs, SITE_CONFIGS_DIR
)
from modules.admin_tools import manage_stories, update_site_configs
from modules.link_manager import scrape_new_story_links, check_for_updates, check_for_revived_links
from modules.content_manager import assemble_chapter_list, scrape_story_content
from modules.converter_tools import create_epub_from_files, create_edge_html_from_file, create_mp3s_from_file

# --- Dependency Flags ---
PLAYWRIGHT_INSTALLED = False
EBOOKLIB_INSTALLED = False
GTTS_INSTALLED = False
REQUESTS_INSTALLED = False

# --- Constants ---
SITE_CONFIGS = {}

# --- Startup Checks ---
def run_startup_checks():
    """Performs initial checks for all dependencies and offers to install them."""
    print("🚀 Running startup checks...")
    
    # Set initial global flags for dependencies
    global PLAYWRIGHT_INSTALLED, EBOOKLIB_INSTALLED, GTTS_INSTALLED, REQUESTS_INSTALLED
    try: import playwright; PLAYWRIGHT_INSTALLED = True
    except ImportError: pass
    try: from ebooklib import epub; EBOOKLIB_INSTALLED = True
    except ImportError: pass
    try: from gtts import gTTS; GTTS_INSTALLED = True
    except ImportError: pass
    try: import requests; REQUESTS_INSTALLED = True
    except ImportError: pass

    # Core dependency check
    if not PLAYWRIGHT_INSTALLED:
        print("\n--- ⚠️ Core Library Missing ---")
        if not check_and_install_dependencies(['playwright']):
            return False
    
    # The check_for_self_update function was removed by the developer.

    global SITE_CONFIGS
    SITE_CONFIGS = load_site_configs()
    if not SITE_CONFIGS and REQUESTS_INSTALLED:
        print("\n⚠️ No site configurations found.")
        if input("Download the default configurations from GitHub now? (y/n): ").strip().lower() in ['y', 'yes']:
            update_site_configs(load_config())
            SITE_CONFIGS = load_site_configs()
            
    print("\n✅ Startup checks passed.")
    return True

# --- Main Menu ---
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
            if check_and_install_dependencies(['playwright']):
                scrape_new_story_links(config, SITE_CONFIGS)
        elif choice == '2': 
            if check_and_install_dependencies(['playwright', 'requests']):
                check_for_updates(SITE_CONFIGS)
        elif choice == '3':
             if check_and_install_dependencies(['playwright']):
                check_for_revived_links(SITE_CONFIGS)
        elif choice == '4':
            assemble_chapter_list()
        elif choice == '5': 
            if check_and_install_dependencies(['playwright']):
                scrape_story_content(config, SITE_CONFIGS)
        elif choice == '6': 
            if check_and_install_dependencies(['ebooklib']):
                create_epub_from_files()
        elif choice == '7':
            create_edge_html_from_file()
        elif choice == '8': 
            if check_and_install_dependencies(['gtts']):
                create_mp3s_from_file()
        elif choice == '9': 
            if check_and_install_dependencies(['requests']):
                update_site_configs(config)
        elif choice == '10':
            manage_stories()
        elif choice == '11':
            print("Goodbye!"); break
        else:
            print("⚠️ Invalid choice.")
        input("\nPress Enter to return to the menu...")

# --- Main Execution ---
if __name__ == "__main__":
    # Add the script's directory to the Python path to allow for module imports
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    if run_startup_checks():
        try:
            main_menu()
        except Exception as e:
            print(f"\n--- An Unexpected Error Occurred in Main Application ---")
            print(f"Error: {type(e).__name__} - {e}")
            import traceback
            traceback.print_exc()
            
    input("\nPress Enter to exit.")
