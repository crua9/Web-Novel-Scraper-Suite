from playwright.sync_api import TimeoutError
import re
import unicodedata

# --- Core Settings ---
DOMAIN = "www.scribblehub.com"
REVERSE_CHAPTERS = True 

def get_chapter_links(page):
    """Scrapes all chapter links from a ScribbleHub series page."""
    print("📖 Clicking the 'Show All Chapters' icon...")
    
    try:
        page.get_by_role("button", name="Got it!").click(timeout=5000)
    except TimeoutError:
        pass

    page.locator('i[title="Show All Chapters"]').click()
    print("⏳ Waiting for all chapters to load...")
    page.wait_for_selector("#pagination-mesh-toc", state="hidden", timeout=120000)
    
    links = page.query_selector_all(".toc_ol .toc_a")
    base_url = "https://www.scribblehub.com"
    urls = []
    for link in links:
        href = link.get_attribute("href")
        if href:
            full_url = href.strip() if href.strip().startswith('http') else base_url + href.strip()
            urls.append(full_url)
    return urls

def get_chapter_content(page, url):
    """Scrapes title and content of a single ScribbleHub chapter."""
    page.goto(url, wait_until='domcontentloaded', timeout=60000)

    try:
        page.get_by_role("button", name="Got it!").click(timeout=3000)
    except TimeoutError:
        pass

    title_selector = 'h1.chapter-title'
    page.wait_for_selector(title_selector, timeout=30000)
    title = page.inner_text(title_selector).strip()

    content_selector = '#chp_raw'
    page.wait_for_selector(content_selector, timeout=30000)
    content_html = page.inner_html(content_selector)
    
    content_text = content_html.replace('</p>', '\n').replace('<p>', '')
    content_text = re.sub('<[^>]*>', '', content_text).strip()
    
    # --- ElevenLabs TTS Sanitization ---
    # ElevenLabs' LLM gets confused by weird unicode, smart punctuation, and hidden HTML entities.
    # This causes it to "hallucinate" and insert random words/dates (like "1984").
    
    # 1. Normalize Unicode (fixes weirdly encoded foreign characters)
    content_text = unicodedata.normalize("NFKC", content_text)
    
    # 2. Flatten smart punctuation (removes tokenizer ambiguity for the TTS engine)
    replacements = {
        '“': '"', '”': '"',
        '‘': "'", '’': "'",
        '—': '-', '–': '-',
        '…': '...'
    }
    for old, new in replacements.items():
        content_text = content_text.replace(old, new)
        
    # 3. Strip zero-width and invisible control characters (removes hidden noise the TTS tries to read)
    content_text = re.sub(r'[\u200B-\u200F\uFEFF\x00-\x08\x0b\x0c\x0e-\x1f]', '', content_text)
    
    return title, content_text
