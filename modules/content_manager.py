import os
import json
from playwright.sync_api import sync_playwright
from .utils import (
    load_stories_db, parse_output_file, build_final_file,
    print_progress_bar, scrape_chapter_content
)

def assemble_chapter_list():
    """Assembles or updates a master chapter_list.txt from individual link files."""
    print("\n" + "─"*10 + " Assemble `chapter_list.txt` " + "─"*10)
    db = load_stories_db()
    if not db:
        print("No stories are currently being tracked.")
        return
        
    stories = list(db.keys())
    print("Select a project to assemble the chapter list for:")
    for i, name in enumerate(stories):
        print(f"  {i+1}: {name}")
    print("  0: Back to Main Menu")
    
    try:
        choice = int(input("\nEnter your choice: ").strip())
        if choice == 0:
            return
        if not (1 <= choice <= len(stories)):
            print("⚠️ Invalid choice.")
            return
        project_folder = stories[choice - 1]
    except ValueError:
        print("⚠️ Invalid input.")
        return

    links_dir = os.path.join(project_folder, "links")
    chapter_list_path = os.path.join(project_folder, "chapter_list.txt")
    progress_path = os.path.join(links_dir, "_added_links_tracker.json")

    if not os.path.exists(links_dir):
        print(f"❌ Links directory not found at '{links_dir}'.")
        return

    try:
        with open(progress_path, 'r', encoding='utf-8') as f:
            processed_files = set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        processed_files = set()

    all_link_files = set(f for f in os.listdir(links_dir) if f.endswith('.txt') and re.search(r'\d+-\d+\.txt$', f))
    new_files = sorted(list(all_link_files - processed_files), key=lambda x: int(re.search(r'(\d+)-\d+\.txt$', x).group(1)))

    if not new_files:
        print(f"\n✅ `chapter_list.txt` in '{project_folder}' is already up-to-date.")
        return

    print("\nThe following new link files were found:")
    for f in new_files:
        print(f"  - {f}")
    
    if input(f"\nDo you want to append these to '{os.path.basename(chapter_list_path)}'? (y/n): ").strip().lower() in ['y', 'yes']:
        print("Appending links...")
        with open(chapter_list_path, "a", encoding="utf-8") as master_file:
            for filename in new_files:
                with open(os.path.join(links_dir, filename), "r", encoding="utf-8") as chunk_file:
                    master_file.write(chunk_file.read())
                processed_files.add(filename)
        
        with open(progress_path, "w", encoding="utf-8") as f:
            json.dump(list(processed_files), f, indent=4)
        
        print("✅ Successfully updated `chapter_list.txt`.")
    else:
        print("Operation cancelled.")

def scrape_story_content(config, site_configs):
    """Guides user through scraping content for a tracked story."""
    print("\n" + "─"*10 + " Scrape Story Content " + "─"*10)
    db = load_stories_db()
    if not db:
        print("No stories are currently being tracked.")
        return

    stories = list(db.keys())
    print("Select a project to scrape content for:")
    for i, name in enumerate(stories):
        print(f"  {i+1}: {name}")
    print("  0: Back to Main Menu")
    
    try:
        choice = int(input("\nEnter your choice: ").strip())
        if choice == 0:
            return
        if not (1 <= choice <= len(stories)):
            print("⚠️ Invalid choice.")
            return
        project_folder = stories[choice - 1]
    except ValueError:
        print("⚠️ Invalid input.")
        return

    chapter_list_path = os.path.join(project_folder, "chapter_list.txt")
    if not os.path.exists(chapter_list_path):
        print(f"❌ '{os.path.basename(chapter_list_path)}' not found in '{project_folder}'.")
        print("Please run option 'Assemble `chapter_list.txt`' from the main menu first.")
        return
        
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
        with open(progress_file, 'r', encoding='utf-8') as f:
            progress_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        progress_data = {}

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
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        total_to_scrape = len(urls_to_scrape)
        print_progress_bar(0, total_to_scrape, prefix='Content Scraping:', suffix='Complete', length=50)

        for i, url in enumerate(urls_to_scrape):
            title, content, notes = scrape_chapter_content(page, url, site_configs)
            if title and content is not None and not title.startswith("Error:"):
                progress_data[url] = title
                with open(output_filepath, "a", encoding="utf-8") as f:
                    f.write(f"\n--- {title} ---\n\n{content}\n")
                if save_notes and notes:
                    with open(notes_filepath, "a", encoding="utf-8") as f:
                        f.write(f"\n--- {title} ---\n\n{notes}\n")
            else:
                print(f"\nSkipping failed URL: {url} ({title})")
            
            # Save progress after each chapter
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=4)
            
            print_progress_bar(i + 1, total_to_scrape, prefix='Content Scraping:', suffix='Complete', length=50)
            
        browser.close()

    all_chapters_data = parse_output_file(output_filepath)
    ordered_titles = [progress_data.get(url) for url in master_url_list if progress_data.get(url)]
    build_final_file(output_filepath, all_chapters_data, ordered_titles)
    print("\n🎉 Content scraping complete.")
