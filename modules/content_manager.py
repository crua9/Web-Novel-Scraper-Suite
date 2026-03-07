import os
import re
import time
import random
from playwright.sync_api import sync_playwright, TimeoutError
from .utils import load_stories_db

# --- CONFIGURATION ---
# Hardcoded path to your Brave Browser
BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

# --- HELPER FUNCTIONS ---

def _get_site_config(url):
    """Returns the correct CSS selectors for content and title based on the URL."""
    if "scribblehub.com" in url:
        return "#chp_raw", "div.chapter-title"
    elif "royalroad.com" in url:
        return ".chapter-content", "h1"
    return None, None

def _scrape_chapter_content_internal(page, url, timeout_ms):
    """Navigates to a URL and scrapes title, content, and author's notes."""
    try:
        content_selector, title_selector = _get_site_config(url)
        if not content_selector:
            print(f"⚠️ Unsupported site: {url}")
            return None, None, None

        # --- HANDLE POPUPS (18+ / Cookies) ---
        # We wrap these in try/except blocks so they don't crash the script if missing
        try:
            # Handle "Yes, I am 18" (ScribbleHub)
            # If we click this, the page usually reloads, so we must wait again.
            if page.get_by_role("button", name="Yes, I am 18 years or older").is_visible(timeout=1000):
                page.get_by_role("button", name="Yes, I am 18 years or older").click()
                time.sleep(1) # Brief pause for the reload trigger
                page.wait_for_load_state("domcontentloaded") # Wait for the new page to be ready
        except Exception:
            pass 

        try:
            # Handle "Got it!" (Cookie Consent)
            if page.get_by_role("button", name="Got it!").is_visible(timeout=1000):
                page.get_by_role("button", name="Got it!").click()
        except Exception:
            pass

        # --- WAIT FOR CONTENT ---
        # Now that popups are handled, wait for the actual story text
        page.wait_for_selector(title_selector, state="attached", timeout=timeout_ms)
        page.wait_for_selector(content_selector, state="attached", timeout=timeout_ms)

        author_notes = None
        # --- Extract and Remove Author's Notes ---
        if "scribblehub.com" in url:
            notes_element = page.query_selector('.wi_authornotes')
            if notes_element:
                author_notes = notes_element.inner_text().strip()
                page.evaluate("document.querySelector('.wi_authornotes')?.remove()")
        elif "royalroad.com" in url:
            notes_element = page.query_selector('.author-note-portlet')
            if notes_element:
                author_notes = notes_element.inner_text().strip()
                page.evaluate("document.querySelector('.author-note-portlet')?.remove()")

        title_element = page.query_selector(title_selector)
        title = title_element.inner_text().strip() if title_element else "Untitled Chapter"

        content_element = page.query_selector(content_selector)
        content = content_element.inner_text().strip() if content_element else ""

        return title, content, author_notes
    except Exception:
        # We return None so the main loop handles the retry logic
        return None, None, None

def _parse_input_file(filepath):
    """Reads chapter_list.txt and returns a list of tuples: (line_index, title_if_scraped, url)."""
    entries = []
    with open(filepath, "r", encoding="utf-8") as f:
        for i, line in enumerate(f.readlines()):
            line = line.strip()
            if not line: continue
            match = re.match(r"✔\s*(.*?)\s+(https?://\S+)", line)
            if match:
                entries.append((i, match.group(1).strip(), match.group(2).strip()))
            else:
                entries.append((i, None, line))
    return entries

def _update_input_file(filepath, index, title, url):
    """Marks a chapter as completed in chapter_list.txt."""
    with open(filepath, "r", encoding="utf-8") as f: lines = f.readlines()
    lines[index] = f"✔ {title} {url}\n"
    with open(filepath, "w", encoding="utf-8") as f: f.writelines(lines)

def _append_to_output_file(filepath, title, content):
    """Appends a single formatted chapter to the output file."""
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(f"\n--- {title} ---\n\n{content}\n")

def _append_to_notes_file(filepath, title, notes):
    """Appends a chapter's author notes to the specified file."""
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(f"\n--- {title} ---\n\n{notes}\n")

def _parse_output_file(filepath):
    """Reads an existing output file and parses its chapters into a dictionary."""
    chapters = {}
    if not os.path.exists(filepath): return chapters
    with open(filepath, "r", encoding="utf-8") as f: content = f.read()
    pattern = re.compile(r"---\s*(.*?)\s*---\n\n(.*?)(?=\n---|\Z)", re.DOTALL)
    for title, text in pattern.findall(content):
        chapters[title.strip()] = text.strip()
    return chapters

def _build_final_file(output_filepath, all_chapters_data, input_filepath):
    """Writes the final output file from scratch, ensuring correct chapter order."""
    ordered_titles = [title for _, title, _ in _parse_input_file(input_filepath) if title]
    print(f"\nRebuilding {os.path.basename(output_filepath)} in the correct order...")
    with open(output_filepath, "w", encoding="utf-8") as f:
        for title in ordered_titles:
            if title in all_chapters_data:
                f.write(f"\n--- {title} ---\n\n{all_chapters_data[title]}\n")
    print("✅ Final file built successfully.")

# --- MAIN FUNCTIONS ---

def assemble_chapter_list():
    """Assembles a master chapter_list.txt from individual link files."""
    print("\n" + "─"*10 + " Assemble `chapter_list.txt` " + "─"*10)
    
    db = load_stories_db()
    if not db:
        print("No stories are being tracked. Scrape a new story first."); return

    stories = list(db.keys())
    print("Select a project to assemble the chapter list for:")
    for i, name in enumerate(stories): print(f"  {i+1}: {name}")
    print("  0: Back to Main Menu")

    try:
        choice = int(input("\nEnter your choice: ").strip())
        if choice == 0: return
        project_folder = stories[choice - 1]
    except (ValueError, IndexError):
        print("⚠️ Invalid choice."); return

    links_dir = os.path.join(project_folder, 'links')
    if not os.path.exists(links_dir) or not os.listdir(links_dir):
        print(f"❌ No link files found for '{project_folder}'."); return

    try:
        link_files = sorted(
            [f for f in os.listdir(links_dir) if f.endswith('.txt')],
            key=lambda x: int(re.search(r'(\d+)-\d+\.txt$', x).group(1)) if re.search(r'(\d+)-\d+\.txt$', x) else 0
        )
    except Exception:
        link_files = sorted([f for f in os.listdir(links_dir) if f.endswith('.txt')])

    print("\nWhich link files do you want to assemble?")
    for i, filename in enumerate(link_files):
        print(f"  {i+1}: {filename}")
    print("  all: Assemble all files")
    print("  0: Back")

    user_input = input("\nEnter numbers (e.g., 1, 3), 'all', or '0': ").strip().lower()

    selected_files = []
    if user_input == '0': return
    elif user_input == 'all':
        selected_files = link_files
    else:
        try:
            chosen_indices = [int(i.strip()) - 1 for i in user_input.split(',')]
            selected_files = [link_files[i] for i in chosen_indices if 0 <= i < len(link_files)]
        except (ValueError, IndexError):
            print("⚠️ Invalid input."); return

    if not selected_files:
        print("No valid files selected."); return
        
    print(f"\nAssembling the following files:")
    for f in selected_files: print(f"  - {f}")

    links_from_selection = []
    for filename in selected_files:
        filepath = os.path.join(links_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                links_from_selection.extend([line.strip() for line in f if line.strip()])
        except IOError as e:
            print(f"❌ Error reading file {filepath}: {e}")

    chapter_list_path = os.path.join(project_folder, 'chapter_list.txt')
    file_exists = os.path.exists(chapter_list_path)
    
    write_mode = 'w'
    links_to_write = links_from_selection
    action_verb = "create"

    if file_exists:
        print(f"\n`chapter_list.txt` already exists. How should I proceed?")
        print("  1: Overwrite the list with your new selection")
        print("  2: Add new, unlisted links to the end of the list")
        action_choice = input("Enter your choice (1 or 2): ").strip()
        
        if action_choice == '2':
            write_mode = 'a'
            action_verb = "append"
            with open(chapter_list_path, 'r', encoding='utf-8') as f:
                existing_links = [line.strip() for line in f.readlines()]
            links_to_write = [link for link in links_from_selection if not link.startswith("✔") and link not in existing_links and "[DEAD LINK]" not in link]
        elif action_choice == '1':
             action_verb = "overwrite"
        else:
            print("⚠️ Invalid choice. Operation cancelled."); return
            
    if not links_to_write:
        print(f"\n✅ No new links to {action_verb}. `chapter_list.txt` is already up-to-date."); return

    print(f"\nPreparing to {action_verb} {len(links_to_write)} links...")
    
    try:
        final_mode = 'w' if write_mode == 'w' else 'a'
        with open(chapter_list_path, final_mode, encoding='utf-8') as f:
            if final_mode == 'w':
                 f.truncate(0)
            for link in links_to_write:
                f.write(link + '\n')
        
        if final_mode == 'w':
             print(f"✅ Successfully created `chapter_list.txt` with {len(links_to_write)} links.")
        else:
             print(f"✅ Successfully appended {len(links_to_write)} new links to `chapter_list.txt`.")

    except IOError as e:
        print(f"❌ Failed to write to file: {e}")

def scrape_story_content(config, site_configs):
    """Main function to orchestrate the scraping process."""
    print("\n" + "─" * 10 + " Scrape Story Content " + "─" * 10)
    
    db = load_stories_db()
    stories = list(db.keys())
    print("Select a project to scrape content for:")
    for i, name in enumerate(stories): print(f"  {i+1}: {name}")
    print("  0: Back")
    try:
        choice = int(input("\nEnter your choice: ").strip())
        if choice == 0: return
        project_folder = stories[choice - 1]
    except (ValueError, IndexError):
        print("⚠️ Invalid choice."); return

    input_filepath = os.path.join(project_folder, "chapter_list.txt")
    if not os.path.exists(input_filepath):
        print(f"❌ 'chapter_list.txt' not found in '{project_folder}'. Please assemble it first."); return

    entries = _parse_input_file(input_filepath)
    urls_to_scrape = [(index, url) for index, title, url in entries if not title]

   # --- Filename and Author Notes ---
    sanitized_name = "".join(c for c in project_folder if c.isalnum() or c in (' ', '_', '-')).strip()
    
    # Auto-calculate chapter range for default filename
    if urls_to_scrape:
        start_chap = urls_to_scrape[0][0] + 1
        end_chap = urls_to_scrape[-1][0] + 1
        default_file = f"{sanitized_name} {start_chap}-{end_chap}.txt"
    else:
        default_file = f"{sanitized_name} Scraped Chapters.txt"

    output_file = os.path.join(project_folder, default_file)
    filename_input = input(f"\nEnter output filename [Enter for '{default_file}']: ").strip()
    if filename_input:
        output_file = os.path.join(project_folder, filename_input if filename_input.lower().endswith(".txt") else f"{filename_input}.txt")

    save_notes_input = input("\n📝 Save author's notes to a separate file? (y/n): ").strip().lower()
    save_author_notes = save_notes_input in ["y", "yes"]
    notes_output_file = ""
    if save_author_notes:
        base_name, ext = os.path.splitext(output_file)
        notes_output_file = f"{base_name} Author Notes{ext}"
        print(f"🗒️  Author's notes will be saved to: {os.path.basename(notes_output_file)}")

    if not urls_to_scrape:
        print("\n✅ All chapters in 'chapter_list.txt' have already been scraped.")
        if os.path.exists(output_file):
            print("\nRunning a final check to ensure correct chapter order...")
            all_chapters = _parse_output_file(output_file)
            if all_chapters:
                _build_final_file(output_file, all_chapters, input_filepath)
        return

    print("\n🧠 Heads up:")
    print(f"* Brave Browser will launch from: {BRAVE_PATH}")
    print("* If Cloudflare appears, solve it in the browser window.")
    print("* Do NOT minimize or close the browser.")
    input("\nPress Enter to begin scraping...")

    if not os.path.exists(BRAVE_PATH):
        print(f"❌ Error: Could not find Brave at: {BRAVE_PATH}")
        return

    scraped_something_new = False
    failed_urls = []

    # --- BRAVE LAUNCHER ---
    with sync_playwright() as p:
        user_data_dir = os.path.join(os.getcwd(), "brave_data")
        try:
            print("🚀 Launching Brave...")
            context = p.chromium.launch_persistent_context(
                user_data_dir,
                executable_path=BRAVE_PATH,
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
        except Exception as e:
            print(f"❌ Failed to launch Brave: {e}")
            print("Make sure all Brave windows are CLOSED before running this.")
            return

        page = context.pages[0] if context.pages else context.new_page()

        total_to_scrape = len(urls_to_scrape)
        for i, (index, url) in enumerate(urls_to_scrape):
            print(f"\nScraping [{i+1}/{total_to_scrape}]: {url}")
            
            # Anti-bot randomization
            time.sleep(random.uniform(1.5, 3.5))

            for attempt in range(3):
                # Timeout increases on retries
                timeout = 60000 if attempt == 0 else (attempt + 1) * 45000
                
                try:
                    # FIXED: Added wait_until='domcontentloaded' to prevent early access
                    page.goto(url, timeout=timeout, wait_until="domcontentloaded")

                    # --- CLOUDFLARE CHECK ---
                    if page.locator("text=Verify you are human").count() > 0 or "Just a moment" in page.title():
                        print("⚠️  Cloudflare detected! Waiting for you to solve it...")
                        try:
                            # Wait up to 5 mins for the title to appear
                            page.wait_for_selector("h1, .chapter-title", state="attached", timeout=300000)
                            print("✅ CAPTCHA passed.")
                        except:
                            print("❌ Timed out waiting for CAPTCHA.")
                    # ------------------------

                    title, content, author_notes = _scrape_chapter_content_internal(page, url, timeout)
                    
                    if title and content is not None:
                        print(f"✅ Scraped and appended: {title}")
                        _append_to_output_file(output_file, title, content)
                        if save_author_notes and author_notes:
                            print(f"🗒️  Saving author's note for: {title}")
                            _append_to_notes_file(notes_output_file, title, author_notes)
                        _update_input_file(input_filepath, index, title, url)
                        scraped_something_new = True
                        break
                    else:
                        print(f"  -> Retry {attempt + 1} failed (content check). Waiting...")
                        time.sleep(3)

                except TimeoutError:
                    print("  -> Timeout (likely CAPTCHA or slow load)...")
                except Exception as e:
                    print(f"  -> Error: {e}")
                    time.sleep(2)

            else: # This block runs if the for loop completes without a 'break'
                print(f"⛔ All retries failed for: {url}")
                failed_urls.append(url)
        
        print("Closing browser...")
        context.close()

    if scraped_something_new:
        print("\nRe-ordering final text file...")
        all_chapters = _parse_output_file(output_file)
        _build_final_file(output_file, all_chapters, input_filepath)

    saved_count = len(urls_to_scrape) - len(failed_urls)
    skipped_count = len(entries) - len(urls_to_scrape)
    failed_count = len(failed_urls)

    print("\n📊 Summary:")
    print(f"✅ Saved {saved_count} new chapters.")
    print(f"⏭️ Skipped {skipped_count} already-saved chapters.")
    print(f"❌ Failed to scrape {failed_count} chapters.")

    if failed_urls:
        failed_filepath = os.path.join(project_folder, "failed_chapters.txt")
        with open(failed_filepath, "w", encoding="utf-8") as f:
            f.write("\nThe following URLs could not be scraped:\n")
            for url in failed_urls: f.write(f"{url}\n")
        print(f"\n- A list of failed URLs has been saved to '{os.path.basename(failed_filepath)}'.")
