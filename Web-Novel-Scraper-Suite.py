import sys
import os
from modules.utils import load_config, save_config, get_theme_colors, check_and_install_dependencies, load_site_configs
from modules.admin_tools import manage_stories, update_site_configs, show_help_qa
from modules.link_manager import scrape_new_story_links, check_for_updates, check_for_revived_links
from modules.content_manager import assemble_chapter_list, scrape_story_content
from modules.converter_tools import create_epub_from_files, create_edge_html_from_file, create_mp3s_from_file

def change_theme():
    config = load_config()
    clr = get_theme_colors()
    S, W = clr['S'], clr['W']
    print(f"\n{S}🎨 Select Theme Number:{W}")
    print(f" {S}1{W}: Cyberpunk")
    print(f" {S}2{W}: Matrix")
    print(f" {S}3{W}: Classic")
    t_choice = input(f"\n{S}Selection: {W}").strip()
    
    themes = {"1": "cyberpunk", "2": "matrix", "3": "classic"}
    if t_choice in themes:
        config["theme"] = themes[t_choice]
        save_config(config)
        print(f"{clr['G']}✅ Theme updated! Restart to apply.{W}")
    else:
        print(f"{clr['R']}❌ Invalid choice.{W}")

def main_menu():
    config = load_config()
    while True:
        clr = get_theme_colors()
        P, S, G, Y, R, W = clr['P'], clr['S'], clr['G'], clr['Y'], clr['R'], clr['W']
        SITE_CONFIGS = load_site_configs()

        print(f"\n{S}────────── 📘 {W}Web Novel Scraper Suite{S} ──────────{W}")
        print(f"{G}--- Link Management ---{W}")
        print(f" {G}1{W}: Scrape New Story Links")
        print(f" {G}2{W}: Check for Link Updates")
        print(f" {G}3{W}: Check for Revived Links")
        print(f"\n{P}--- Content Management ---{W}")
        print(f" {P}4{W}: Assemble `chapter_list.txt`")
        print(f" {P}5{W}: Scrape Story Content")
        print(f"\n{Y}--- Conversion Tools ---{W}")
        print(f" {Y}6{W}: Create EPUB Ebook")
        print(f" {Y}7{W}: Create HTML (Edge)")
        print(f" {Y}8{W}: Create MP3 Audio Files")
        print(f"\n{S}--- Administration ---{W}")
        print(f" {S}9{W}: Update Site Configs")
        print(f" {S}10{W}: Manage Tracked Stories")
        print(f" {S}11{W}: Help & Troubleshooting")
        print(f" {S}12{W}: Change Theme")
        print(f" {S}13{W}: Exit")
        
        choice = input(f"\n{S}Selection: {W}").strip()

        if choice == '1': scrape_new_story_links(config, SITE_CONFIGS)
        elif choice == '2': check_for_updates(config, SITE_CONFIGS)
        elif choice == '3': check_for_revived_links(config, SITE_CONFIGS)
        elif choice == '4': assemble_chapter_list()
        elif choice == '5': scrape_story_content(config, SITE_CONFIGS)
        elif choice == '6': create_epub_from_files()
        elif choice == '7': create_edge_html_from_file()
        elif choice == '8': create_mp3s_from_file()
        elif choice == '9': update_site_configs(config)
        elif choice == '10': manage_stories()
        elif choice == '11': show_help_qa()
        elif choice == '12': change_theme()
        elif choice == '13': print(f"{Y}Goodbye!{W}"); break
        else: print(f"{R}⚠️ Invalid choice.{W}")
        input(f"\n{S}Press Enter to return...{W}")

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    check_and_install_dependencies(['playwright', 'requests'])
    main_menu()
