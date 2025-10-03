import os
import re
from .utils import check_and_install_dependencies

def create_epub_from_files():
    """
    Creates an EPUB ebook from one or more scraped story files.
    """
    print("\n" + "─"*10 + " Create EPUB Ebook " + "─"*10)

    if not check_and_install_dependencies(['ebooklib']):
        return

    from ebooklib import epub

    # --- Project Selection ---
    project_folders = [d for d in os.listdir('.') if os.path.isdir(d) and not d.startswith('.') and not d.startswith('_')]
    if not project_folders:
        print("No project folders found."); return

    print("Select the project folder containing the story files:")
    for i, folder in enumerate(project_folders):
        print(f"  {i+1}: {folder}")
    print("  0: Back")

    try:
        choice = int(input("\nEnter your choice: ").strip())
        if choice == 0: return
        project_folder = project_folders[choice - 1]
    except (ValueError, IndexError):
        print("⚠️ Invalid choice."); return

    # --- File Selection ---
    story_files = [f for f in os.listdir(project_folder) if f.endswith('.txt') and "chapter_list" not in f and "failed" not in f and "Author Notes" not in f]
    if not story_files:
        print(f"❌ No story text files found in '{project_folder}'."); return
    
    print("\nSelect the story file(s) to include in the EPUB:")
    for i, filename in enumerate(story_files):
        print(f"  {i+1}: {filename}")
    print("  all: Include all files")
    print("  0: Back")

    user_input = input("\nEnter numbers (e.g., 1, 3), 'all', or '0': ").strip().lower()

    selected_files = []
    if user_input == '0': return
    elif user_input == 'all':
        selected_files = story_files
    else:
        try:
            chosen_indices = [int(i.strip()) - 1 for i in user_input.split(',')]
            selected_files = [story_files[i] for i in chosen_indices if 0 <= i < len(story_files)]
        except (ValueError, IndexError):
            print("⚠️ Invalid input."); return

    if not selected_files:
        print("No valid files selected."); return

    # --- EPUB Metadata ---
    author_name = input("\nEnter the author's name: ").strip() or "Unknown Author"
    book_title = input(f"Enter the book title [default: {project_folder}]: ").strip() or project_folder
    
    book = epub.EpubBook()
    book.set_identifier(f'urn:uuid:{project_folder}')
    book.set_title(book_title)
    book.set_language('en')
    book.add_author(author_name)

    # --- Chapter Parsing and Creation ---
    print("\n⚙️ Reading and parsing story files...")
    full_content = ""
    for filename in sorted(selected_files):
        try:
            with open(os.path.join(project_folder, filename), 'r', encoding='utf-8') as f:
                full_content += f.read()
        except IOError as e:
            print(f"❌ Error reading {filename}: {e}")
            continue
    
    raw_chapters = re.split(r'\n---\s*(.*?)\s*---\n', full_content)
    
    chapter_data = []
    if len(raw_chapters) > 1:
        for i in range(1, len(raw_chapters), 2):
            title = raw_chapters[i].strip()
            content = raw_chapters[i+1].strip().replace('\n', '<br/>')
            if title and content:
                chapter_data.append({'title': title, 'content': content})

    if not chapter_data:
        print("❌ Could not find any chapters in the selected files. Make sure they are formatted with '--- Chapter Title ---'.")
        return

    print(f"✅ Found {len(chapter_data)} chapters to add.")
    
    toc = []
    book_chapters = []
    for i, chap_info in enumerate(chapter_data):
        chapter_title = chap_info['title']
        chapter_content = chap_info['content']
        
        epub_chap = epub.EpubHtml(title=chapter_title, file_name=f'chap_{i+1}.xhtml', lang='en')
        epub_chap.content = f'<h1>{chapter_title}</h1><p>{chapter_content}</p>'
        
        book.add_item(epub_chap)
        toc.append(epub.Link(f'chap_{i+1}.xhtml', chapter_title, f'chap_{i+1}'))
        book_chapters.append(epub_chap)

    book.toc = tuple(toc)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav'] + book_chapters

    output_filename = f"{book_title}.epub"
    output_path = os.path.join(project_folder, output_filename)
    
    try:
        epub.write_epub(output_path, book, {})
        print(f"\n🎉 Successfully created EPUB: '{output_filename}' in '{project_folder}'")
    except Exception as e:
        print(f"\n❌ An error occurred while writing the EPUB file: {e}")


def create_edge_html_from_file():
    """Creates a single HTML file from story text files, formatted for Edge's Read Aloud."""
    print("\n" + "─"*10 + " Create HTML for Read Aloud " + "─"*10)

    project_folders = [d for d in os.listdir('.') if os.path.isdir(d) and not d.startswith('.') and not d.startswith('_')]
    if not project_folders:
        print("No project folders found."); return

    print("Select the project folder containing the story files:")
    for i, folder in enumerate(project_folders):
        print(f"  {i+1}: {folder}")
    print("  0: Back")

    try:
        choice = int(input("\nEnter your choice: ").strip())
        if choice == 0: return
        project_folder = project_folders[choice - 1]
    except (ValueError, IndexError):
        print("⚠️ Invalid choice."); return

    story_files = [f for f in os.listdir(project_folder) if f.endswith('.txt') and "chapter_list" not in f and "failed" not in f and "Author Notes" not in f]
    if not story_files:
        print(f"❌ No story text files found in '{project_folder}'."); return
    
    print("\nSelect the story file(s) to convert to HTML:")
    for i, filename in enumerate(story_files):
        print(f"  {i+1}: {filename}")
    print("  all: Include all files")
    print("  0: Back")

    user_input = input("\nEnter numbers (e.g., 1, 3), 'all', or '0': ").strip().lower()

    selected_files = []
    if user_input == '0': return
    elif user_input == 'all':
        selected_files = story_files
    else:
        try:
            chosen_indices = [int(i.strip()) - 1 for i in user_input.split(',')]
            selected_files = [story_files[i] for i in chosen_indices if 0 <= i < len(story_files)]
        except (ValueError, IndexError):
            print("⚠️ Invalid input."); return

    if not selected_files:
        print("No valid files selected."); return

    book_title = input(f"Enter the HTML page title [default: {project_folder}]: ").strip() or project_folder
    
    print("\n⚙️ Reading and parsing story files...")
    full_content = ""
    for filename in sorted(selected_files):
        try:
            with open(os.path.join(project_folder, filename), 'r', encoding='utf-8') as f:
                full_content += f.read()
        except IOError as e:
            print(f"❌ Error reading {filename}: {e}")
            continue
            
    raw_chapters = re.split(r'\n---\s*(.*?)\s*---\n', full_content)
    
    html_body_content = ""
    chapter_count = 0
    if len(raw_chapters) > 1:
        for i in range(1, len(raw_chapters), 2):
            title = raw_chapters[i].strip()
            content = raw_chapters[i+1].strip().replace('\n', '<br />')
            if title and content:
                html_body_content += f"<h2>{title}</h2>\n<p>{content}</p>\n\n"
                chapter_count += 1
    
    if not html_body_content:
        print("❌ Could not find any chapters in the selected files."); return
        
    print(f"✅ Found {chapter_count} chapters to convert.")

    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{book_title}</title>
    <style>
        body {{ font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 20px auto; padding: 0 20px; background-color: #fdfdfd; color: #333; }}
        h1, h2 {{ text-align: center; border-bottom: 1px solid #ccc; padding-bottom: 10px; }}
        p {{ text-indent: 2em; }}
    </style>
</head>
<body>
    <h1>{book_title}</h1>
    {html_body_content}
</body>
</html>"""

    output_filename = f"{book_title}.html"
    output_path = os.path.join(project_folder, output_filename)
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_template)
        print(f"\n🎉 Successfully created HTML file: '{output_filename}' in '{project_folder}'")
    except Exception as e:
        print(f"\n❌ An error occurred while writing the HTML file: {e}")


def create_mp3s_from_file():
    """Creates MP3 audio files from a story file using gTTS, one file per chapter."""
    print("\n" + "─"*10 + " Create MP3 Audio Files " + "─"*10)

    if not check_and_install_dependencies(['gtts']):
        return
        
    from gtts import gTTS

    project_folders = [d for d in os.listdir('.') if os.path.isdir(d) and not d.startswith('.') and not d.startswith('_')]
    if not project_folders:
        print("No project folders found."); return

    print("Select the project folder containing the story file:")
    for i, folder in enumerate(project_folders):
        print(f"  {i+1}: {folder}")
    print("  0: Back")

    try:
        choice = int(input("\nEnter your choice: ").strip())
        if choice == 0: return
        project_folder = project_folders[choice - 1]
    except (ValueError, IndexError):
        print("⚠️ Invalid choice."); return

    story_files = [f for f in os.listdir(project_folder) if f.endswith('.txt') and "chapter_list" not in f and "failed" not in f]
    if not story_files:
        print(f"❌ No story text files found in '{project_folder}'."); return
    
    print("\nSelect the story file to convert to MP3s:")
    for i, filename in enumerate(story_files):
        print(f"  {i+1}: {filename}")
    print("  0: Back")
    
    try:
        choice = int(input("\nEnter your choice: ").strip())
        if choice == 0: return
        selected_file = story_files[choice - 1]
    except (ValueError, IndexError):
        print("⚠️ Invalid choice."); return

    print("\n⚙️ Reading and parsing story file...")
    try:
        with open(os.path.join(project_folder, selected_file), 'r', encoding='utf-8') as f:
            full_content = f.read()
    except IOError as e:
        print(f"❌ Error reading {selected_file}: {e}"); return
        
    raw_chapters = re.split(r'\n---\s*(.*?)\s*---\n', full_content)
    
    chapter_data = []
    if len(raw_chapters) > 1:
        for i in range(1, len(raw_chapters), 2):
            title = raw_chapters[i].strip()
            content = raw_chapters[i+1].strip()
            if title and content:
                chapter_data.append({'title': title, 'content': content})

    if not chapter_data:
        print("❌ Could not find any chapters in the selected file."); return

    output_dir = os.path.join(project_folder, "Audio Chapters")
    os.makedirs(output_dir, exist_ok=True)
    print(f"✅ Found {len(chapter_data)} chapters. MP3s will be saved in '{output_dir}'")
    print("\n🚀 Starting conversion (this may take a while)...")
    
    total_chapters = len(chapter_data)
    for i, chap_info in enumerate(chapter_data):
        title = chap_info['title']
        content = chap_info['content']
        
        # Sanitize title for filename
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
        filename = f"{i+1:04d} - {safe_title}.mp3"
        output_path = os.path.join(output_dir, filename)
        
        print(f"  [{i+1}/{total_chapters}] Converting: {title}...")

        try:
            tts = gTTS(text=f"{title}. {content}", lang='en')
            tts.save(output_path)
        except Exception as e:
            print(f"    ❌ FAILED to convert chapter: {title}")
            print(f"       Reason: {e}")
            continue
            
    print(f"\n🎉 Conversion complete. {total_chapters} chapters processed.")

