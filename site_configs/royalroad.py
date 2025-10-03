from playwright.sync_api import TimeoutError
import re

# --- Core Settings ---
DOMAIN = "www.royalroad.com"
REVERSE_CHAPTERS = False # Royal Road chapter lists are usually in chronological order

# --- Main Functions ---
def get_links(page):
    """
    Scrapes all chapter links from a Royal Road fiction page by parsing
    the chapter data embedded in the page's script.
    """
    print("🔍 Extracting Royal Road links from page data...")
    
    # Wait for the chapters table to be visible to ensure scripts have loaded
    page.wait_for_selector("#chapters", timeout=30000)
    
    script_content = page.content()
    # Find the JavaScript block containing the chapter data
    match = re.search(r'window\.chapters\s*=\s*(\[.*?\]);', script_content)
    
    if not match:
        print("❌ Could not find chapter data script block.")
        return []
        
    try:
        # The matched group is a JSON string of a list of chapter objects
        import json
        chapters_data = json.loads(match.group(1))
        base_url = "https://www.royalroad.com"
        # Construct the full URL for each chapter
        return [base_url + chapter['url'] for chapter in chapters_data]
    except (json.JSONDecodeError, KeyError) as e:
        print(f"❌ Failed to parse chapter data: {e}")
        return []

def get_content(page, url):
    """
    This function is responsible for scraping the title, content, and author's note
    of a single Royal Road chapter page.
    """
    page.goto(url, wait_until='domcontentloaded', timeout=60000)
    
    # Get the chapter title from the main h1 element
    title_selector = 'h1'
    page.wait_for_selector(title_selector, timeout=30000)
    title = page.inner_text(title_selector).strip()

    # Get the main chapter content
    content_selector = '.chapter-content'
    page.wait_for_selector(content_selector, timeout=30000)
    content_html = page.inner_html(content_selector)
    
    # Convert HTML to plain text, preserving paragraph breaks
    content_text = content_html.replace('</p>', '\n').replace('<p>', '')
    content_text = re.sub('<[^>]*>', '', content_text).strip()

    # Scrape the author's note, if it exists
    author_note = None
    try:
        note_selector = '.author-note'
        # Use a short timeout because the note may not be present
        page.wait_for_selector(note_selector, timeout=3000) 
        note_html = page.inner_html(note_selector)
        note_text = note_html.replace('</p>', '\n').replace('<p>', '')
        author_note = re.sub('<[^>]*>', '', note_text).strip()
    except TimeoutError:
        # It's normal for a chapter to not have an author's note
        pass 
        
    return title, content_text, author_note
