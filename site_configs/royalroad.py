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

    content_selector = '.chapter-inner'
    page.wait_for_selector(content_selector, timeout=30000)
    
    # Get raw content
    raw_content = page.inner_text(content_selector)
    
    # --- Anti-Piracy Warning Removal ---
    # Royal Road injects these to mess with scrapers. We filter them out based on common keywords.
    warning_triggers = [
        "taken from royal road",
        "stolen story",
        "purloined without the author",
        "taken without permission from the author",
        "unlawfully taken from royal road",
        "genuine version",
        "unauthorized usage",
        "official version",
        "unlawfully lifted",
        "creativity of authors",
        "creative writers",
        "literary theft",
        "taken without authorization",
        "illicitly lifted",
        "favorite authors get the support",
        "illicitly obtained",
        "stolen from royal road",
        "report any occurrences",
        "appearances on amazon",
        "report any sightings",
        "report the violation",
        "report the incident",
        "author's preferred platform",
        "support the creator",
        "ensure the author gets",
        "stolen content warning",
        "story on amazon",
        "narrative on amazon",
        "tale is not rightfully on amazon",
        "read the original version",
        "support their work!"
    ]
    
    cleaned_lines = []
    for line in raw_content.split('\n'):
        line_lower = line.strip().lower()
        # If the line contains any of the warning triggers, skip adding it
        if line_lower and any(trigger in line_lower for trigger in warning_triggers):
            continue
        cleaned_lines.append(line)
        
    # Clean up any excessive newlines caused by removing the warning paragraphs
    content = '\n'.join(cleaned_lines)
    content = re.sub(r'\n{3,}', '\n\n', content).strip()
    
    return title, content
