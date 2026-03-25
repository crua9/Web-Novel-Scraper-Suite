from playwright.sync_api import TimeoutError
import re
import json
import unicodedata

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

    content_selector = '.chapter-inner'
    page.wait_for_selector(content_selector, timeout=30000)
    
    raw_content = page.inner_text(content_selector)
    
    # --- Anti-Piracy Warning Removal ---
    # Royal Road injects hidden "zero-width" characters into their warning paragraphs 
    # to prevent scrapers from using simple Find/Replace.
    # The triggers below have all spaces removed so they can match against the heavily stripped text.
    warning_triggers = [
        "takenfromroyalroad", "stolenstory", "purloinedwithout", "takenwithoutpermission",
        "unlawfullytaken", "genuineversion", "unauthorizedusage", "unauthorizeduse",
        "officialversion", "unlawfullylifted", "creativityofauthors", "creativewriters",
        "literarytheft", "takenwithoutauthorization", "illicitlylifted", "illicitlyobtained",
        "stolenfromroyalroad", "reportanyoccurrences", "appearancesonamazon", "reportanysightings",
        "reporttheviolation", "reporttheincident", "authorspreferredplatform", "supportthecreator",
        "ensuretheauthorgets", "stolencontentwarning", "storyonamazon", "narrativeonamazon",
        "taleisnotrightfullyonamazon", "readtheoriginalversion", "supporttheirwork",
        "royalroadisthehome", "enjoyingthestoryshowyoursupport", "helpsupportcreativewriters",
        "ensuretheauthorgetscredit", "anothersitesupporttheauthor", "withouttheauthorsconsent",
        "reportanyinstances"
    ]
    
    cleaned_lines = []
    for line in raw_content.split('\n'):
        # By removing EVERYTHING except letters (including the invisible zero-width characters), 
        # we can reliably detect the warning phrases and delete the line.
        alpha_only_line = re.sub(r'[^a-z]', '', line.lower())
        if alpha_only_line and any(trigger in alpha_only_line for trigger in warning_triggers):
            continue
        cleaned_lines.append(line)
        
    content = '\n'.join(cleaned_lines)
    content = re.sub(r'\n{3,}', '\n\n', content).strip()
    
    # --- ElevenLabs TTS Sanitization ---
    # ElevenLabs' LLM gets confused by weird unicode, smart punctuation, and hidden HTML entities.
    # This causes it to "hallucinate" and insert random words/dates (like "1984").
    
    # 1. Normalize Unicode (fixes weirdly encoded foreign characters)
    content = unicodedata.normalize("NFKC", content)
    
    # 2. Flatten smart punctuation (removes tokenizer ambiguity for the TTS engine)
    replacements = {
        '“': '"', '”': '"',
        '‘': "'", '’': "'",
        '—': '-', '–': '-',
        '…': '...'
    }
    for old, new in replacements.items():
        content = content.replace(old, new)
        
    # 3. Strip zero-width and invisible control characters (removes hidden noise the TTS tries to read)
    content = re.sub(r'[\u200B-\u200F\uFEFF\x00-\x08\x0b\x0c\x0e-\x1f]', '', content)
    
    return title, content
