from playwright.sync_api import TimeoutError
import re

# --- Core Settings ---
DOMAIN = "www.scribblehub.com"
REVERSE_CHAPTERS = True # This method gets links from newest to oldest

# --- Main Functions ---
def get_links(page):
    """
    Scrapes all chapter links from a ScribbleHub series page by clicking
    the 'Show All Chapters' button and waiting for the full list to load.
    """
    print("📖 Clicking the 'Show All Chapters' icon...")
    
    # Handle the cookie consent banner first, if it appears
    try:
        page.get_by_role("button", name="Got it!").click(timeout=5000)
        print("✅ Cookie consent accepted.")
    except TimeoutError:
        print("👍 No cookie consent banner found or it was already handled.")

    # Click the icon to load all chapters
    page.locator('i[title="Show All Chapters"]').click()
    
    print("⏳ Waiting for all chapters to load... (this might take a minute)")
    # The '#pagination-mesh-toc' element disappears when the list is fully loaded
    page.wait_for_selector("#pagination-mesh-toc", state="hidden", timeout=120000)
    print("✅ Full chapter list loaded.")
    
    links = page.query_selector_all(".toc_ol .toc_a")
    base_url = "https://www.scribblehub.com"
    urls = []
    for link in links:
        href = link.get_attribute("href")
        if href:
            # Ensure the link is a full URL
            full_url = href.strip() if href.strip().startswith('http') else base_url + href.strip()
            urls.append(full_url)
    return urls

def get_content(page, url):
    """
    This function is responsible for scraping the title and content of a single
    ScribbleHub chapter page.
    """
    page.goto(url, wait_until='domcontentloaded', timeout=60000)

    # Handle cookie consent on chapter pages as well
    try:
        page.get_by_role("button", name="Got it!").click(timeout=3000)
    except TimeoutError:
        pass # No banner found, continue

    # Get the chapter title
    title_selector = 'h1.chapter-title'
    page.wait_for_selector(title_selector, timeout=30000)
    title = page.inner_text(title_selector).strip()

    # Get the chapter content from the specific div
    content_selector = '#chp_raw'
    page.wait_for_selector(content_selector, timeout=30000)
    
    content_html = page.inner_html(content_selector)
    
    # Convert HTML to plain text, preserving paragraph breaks
    content_text = content_html.replace('</p>', '\n').replace('<p>', '')
    content_text = re.sub('<[^>]*>', '', content_text).strip()
    
    # ScribbleHub does not have a separate, consistent container for author's notes
    # at the end of a chapter, so we return None for the author_note.
    return title, content_text, None

