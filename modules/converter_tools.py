import os
import re
import requests
from .utils import get_theme_colors, load_stories_db, check_and_install_dependencies

def get_all_project_folders():
    """Maps tracked stories to their folders in root or /stories/."""
    db = load_stories_db()
    project_paths = []
    for story_name in db.keys():
        sub_path = os.path.join("stories", story_name)
        if os.path.isdir(sub_path): project_paths.append(sub_path)
        elif os.path.isdir(story_name): project_paths.append(story_name)
    return sorted(list(set(project_paths)))

def create_epub_from_files():
    clr = get_theme_colors()
    P, S, G, Y, R, W = clr['P'], clr['S'], clr['G'], clr['Y'], clr['R'], clr['W']
    print(f"\n{S}────────── 📚 Create EPUB Ebook ──────────{W}")
    if not check_and_install_dependencies(['ebooklib']): return
    from ebooklib import epub

    project_folders = get_all_project_folders()
    if not project_folders:
        print(f"{R}❌ No story folders found.{W}"); return

    for i, folder in enumerate(project_folders):
        print(f"  {P}{i+1}{W}: {os.path.basename(folder)}")
    
    try:
        choice_input = input(f"\n{S}Select Folder ID (or 0 to go back): {W}").strip()
        if choice_input == '0' or not choice_input: return
        project_folder = project_folders[int(choice_input) - 1]
    except: return

    story_files = [f for f in os.listdir(project_folder) if f.endswith('.txt') and "chapter_list" not in f and "failed" not in f]
    if not story_files:
        print(f"{R}❌ No text files found in '{os.path.basename(project_folder)}'.{W}"); return
        
    for i, f in enumerate(story_files): print(f"  {P}{i+1}{W}: {f}")
    
    print(f"\n{G}Options: {W}'all', '0' (back), or specific IDs (e.g., 1, 2, 4)")
    user_input = input(f"{S}Selection: {W}").strip().lower()
    
    if user_input == '0' or not user_input: return
    
    if user_input == 'all':
        selected_files = story_files
    else:
        try:
            selected_files = [story_files[int(i.strip())-1] for i in user_input.split(',') if i.strip()]
        except:
            print(f"{R}⚠️ Invalid selection format.{W}"); return

    # Metadata & Scraping
    db = load_stories_db()
    project_key = os.path.basename(project_folder)
    story_url = db.get(project_key, {}).get("story_url", "")
    author_name = "Unknown Author"
    
    if story_url:
        try:
            html = requests.get(story_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5).text
            m = re.search(r'property="books:author" content="([^"]+)"', html) or re.search(r'<span property="name">([^<]+)</span>', html)
            if m: author_name = m.group(1)
        except: pass

    default_title = selected_files[0].replace(".txt", "") if len(selected_files) == 1 else project_key
    author_name = input(f"\n{S}Author [{author_name}]: {W}").strip() or author_name
    book_title = input(f"{S}Book Title [{default_title}]: {W}").strip() or default_title

    book = epub.EpubBook()
    book.set_title(book_title)
    book.add_author(author_name)

    full_content = ""
    for filename in sorted(selected_files):
        with open(os.path.join(project_folder, filename), 'r', encoding='utf-8') as f:
            full_content += f.read()
    
    raw_chapters = re.split(r'\n---\s*(.*?)\s*---\n', full_content)
    toc, book_chapters = [], []
    if len(raw_chapters) > 1:
        for i in range(1, len(raw_chapters), 2):
            t = raw_chapters[i].strip()
            c = raw_chapters[i+1].strip().replace('\n', '<br/>')
            chap = epub.EpubHtml(title=t, file_name=f'chap_{i}.xhtml', lang='en')
            chap.content = f"<h1>{t}</h1><p>{c}</p>"
            book.add_item(chap)
            toc.append(epub.Link(f'chap_{i}.xhtml', t, f'chap_{i}'))
            book_chapters.append(chap)

    book.toc, book.spine = tuple(toc), ['nav'] + book_chapters
    book.add_item(epub.EpubNcx()); book.add_item(epub.EpubNav())
    epub.write_epub(os.path.join(project_folder, f"{book_title}.epub"), book, {})
    print(f"\n{G}🎉 Created: {book_title}.epub{W}")

def create_edge_html_from_file():
    clr = get_theme_colors()
    P, S, G, Y, R, W = clr['P'], clr['S'], clr['G'], clr['Y'], clr['R'], clr['W']
    print(f"\n{S}────────── 🌐 Create HTML for Read Aloud ──────────{W}")

    project_folders = get_all_project_folders()
    for i, folder in enumerate(project_folders): print(f"  {P}{i+1}{W}: {os.path.basename(folder)}")
    
    try:
        choice_input = input(f"\n{S}Select Folder ID (or 0 to go back): {W}").strip()
        if choice_input == '0' or not choice_input: return
        project_folder = project_folders[int(choice_input) - 1]
    except: return

    story_files = [f for f in os.listdir(project_folder) if f.endswith('.txt') and "chapter_list" not in f]
    for i, f in enumerate(story_files): print(f"  {P}{i+1}{W}: {f}")
    
    print(f"\n{G}Options: {W}'all', '0' (back), or specific IDs (e.g., 1, 2)")
    user_input = input(f"{S}Selection: {W}").strip().lower()
    if user_input == '0' or not user_input: return
    selected_files = story_files if user_input == 'all' else [story_files[int(x.strip())-1] for x in user_input.split(',') if x.strip()]

    book_title = input(f"{S}Page Title [{os.path.basename(project_folder)}]: {W}").strip() or os.path.basename(project_folder)

    full_content = ""
    for filename in sorted(selected_files):
        with open(os.path.join(project_folder, filename), 'r', encoding='utf-8') as f:
            full_content += f.read()

    raw_chapters = re.split(r'\n---\s*(.*?)\s*---\n', full_content)
    body = ""
    if len(raw_chapters) > 1:
        for i in range(1, len(raw_chapters), 2):
            chapter_title = raw_chapters[i].strip()
            chapter_content = raw_chapters[i+1].strip().replace('\n', '<br />')
            body += f"<h2>{chapter_title}</h2>\n<p>{chapter_content}</p>\n\n"

    html_template = f"<!DOCTYPE html><html><head><title>{book_title}</title><style>body{{font-family:sans-serif;line-height:1.6;max-width:800px;margin:20px auto;padding:0 20px;}}h2{{text-align:center;border-bottom:1px solid #ccc;}}p{{text-indent:2em;}}</style></head><body><h1>{book_title}</h1>{body}</body></html>"
    
    with open(os.path.join(project_folder, f"{book_title}.html"), 'w', encoding='utf-8') as f:
        f.write(html_template)
    print(f"\n{G}🎉 Created: {book_title}.html{W}")

def create_mp3s_from_file():
    clr = get_theme_colors()
    P, S, G, Y, R, W = clr['P'], clr['S'], clr['G'], clr['Y'], clr['R'], clr['W']
    print(f"\n{S}────────── 🎧 Create MP3 Audio Files ──────────{W}")
    if not check_and_install_dependencies(['gtts']): return
    from gtts import gTTS

    project_folders = get_all_project_folders()
    for i, folder in enumerate(project_folders): print(f"  {P}{i+1}{W}: {os.path.basename(folder)}")
    
    try:
        choice_input = input(f"\n{S}Select Folder ID (or 0 to go back): {W}").strip()
        if choice_input == '0' or not choice_input: return
        project_folder = project_folders[int(choice_input) - 1]
    except: return

    story_files = [f for f in os.listdir(project_folder) if f.endswith('.txt') and "chapter_list" not in f]
    for i, f in enumerate(story_files): print(f"  {P}{i+1}{W}: {f}")
    
    try:
        idx_input = input(f"\n{S}Select file ID (or 0 to go back): {W}").strip()
        if idx_input == '0' or not idx_input: return
        selected_file = story_files[int(idx_input) - 1]
    except: return

    with open(os.path.join(project_folder, selected_file), 'r', encoding='utf-8') as f:
        raw_chapters = re.split(r'\n---\s*(.*?)\s*---\n', f.read())

    output_dir = os.path.join(project_folder, "Audio Chapters")
    os.makedirs(output_dir, exist_ok=True)
    
    chapter_data = []
    for i in range(1, len(raw_chapters), 2):
        chapter_data.append({'t': raw_chapters[i].strip(), 'c': raw_chapters[i+1].strip()})

    print(f"{Y}🚀 Converting {len(chapter_data)} chapters to MP3...{W}")
    for i, chap in enumerate(chapter_data):
        safe_t = re.sub(r'[\\/*?:"<>|]', "", chap['t'])
        print(f"  [{i+1}/{len(chapter_data)}] {chap['t']}...")
        text_to_speak = f"{chap['t']}. {chap['c']}"
        tts = gTTS(text=text_to_speak, lang='en')
        tts.save(os.path.join(output_dir, f"{i+1:04d} - {safe_t}.mp3"))
    print(f"\n{G}🎉 MP3 Conversion Complete.{W}")
