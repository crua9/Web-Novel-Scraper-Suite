from playwright.sync_api import TimeoutError
import re
import json

# --- Core Settings ---
DOMAIN = "www.royalroad.com"
REVERSE_CHAPTERS = False 

def get_chapter_links(page):
    """Scrapes all chapter links from a Royal Road fiction page."""
    print("🔍 Extracting Royal Road links from page data...")
    page.wait_for_selector("#chapters", timeout=30000)
    
    script_content = page.content()
    match = re.search(r'window\.chapters\s*=\s*(\[.*?\]);', script_content)
    
    if not match:
        print("❌ Could not find chapter data script block.")
        return []
        
    try:
        chapters_data = json.loads(match.group(1))
        base_url = "https://www.royalroad.com"
        return [base_url + chapter['url'] for chapter in chapters_data]
    except (json.JSONDecodeError, KeyError) as e:
        print(f"❌ Failed to parse chapter data: {e}")
        return []

def get_chapter_content(page, url):
    """Scrapes title and content of a single Royal Road chapter."""
    page.goto(url, wait_until='domcontentloaded', timeout=60000)
    
    title_selector = 'h1'
    page.wait_for_selector(title_selector, timeout=30000)
    title = page.inner_text(title_selector).strip()

    content_selector = '.chapter-content'
    page.wait_for_selector(content_selector, timeout=30000)
    content_html = page.inner_html(content_selector)
    
    content_text = content_html.replace('</p>', '\n').replace('<p>', '')
    content_text = re.sub('<[^>]*>', '', content_text).strip()

    return title, content_text
