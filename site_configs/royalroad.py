import re
import json
from playwright.sync_api import TimeoutError

# This variable is used by the main script to identify which URLs this config handles.
DOMAIN = "royalroad.com"
# This tells the main script that the chapter list from the site does NOT need to be reversed,
# as Royal Road provides it in chronological order.
REVERSE_CHAPTERS = False 

def get_links(page):
    """
    Scrapes all chapter links from a Royal Road fiction page.
    This method is faster and more reliable as it reads data directly from a script tag
    embedded in the page's HTML, rather than interacting with visible elements.
    """
    try:
        print("🔍 Extracting Royal Road links from page data...")
        # First, wait for the chapter table element to be present. This is a good sign
        # that the JavaScript containing the chapter data has loaded.
        page.wait_for_selector("#chapters", timeout=30000)
        
        # Get the entire HTML content of the page
        script_content = page.content()
        # Use a regular expression to find the specific JavaScript variable `window.chapters`
        # and capture the JSON array assigned to it.
        match = re.search(r'window\.chapters\s*=\s*(\[.*?\]);', script_content)
        
        if not match:
            print("❌ Could not find the chapter data script block on Royal Road.")
            return []
            
        # Parse the captured string as JSON to get a list of chapter objects
        chapters_data = json.loads(match.group(1))
        base_url = "https://www.royalroad.com"
        # Create a full URL for each chapter from the parsed data
        urls = [base_url + chapter['url'] for chapter in chapters_data]
        return urls
    except (json.JSONDecodeError, KeyError) as e:
        print(f"❌ Failed to parse Royal Road chapter data: {e}")
        return []
    except Exception as e:
        print(f"❌ An error occurred during Royal Road link scraping: {e}")
        return []

def get_content(page, url):
    """
    Scrapes the title, content, and author's notes from a Royal Road chapter page.
    This function is called by the main scraper script.
    """
    try:
        # Navigate to the chapter page with a generous timeout
        page.goto(url, timeout=60000)
        # Wait until the initial HTML is parsed
        page.wait_for_load_state("domcontentloaded", timeout=60000)
        
        # Define the specific CSS selectors for Royal Road
        title_selector = "h1"
        content_selector = ".chapter-content"
        notes_selector = ".author-note-portlet"
        
        # Wait for the essential elements to be ready on the page
        page.wait_for_selector(title_selector, state="attached", timeout=30000)
        page.wait_for_selector(content_selector, state="attached", timeout=30000)

        author_notes = None
        # Find the author's notes element
        notes_element = page.query_selector(notes_selector)
        if notes_element:
            # If notes exist, get their text content
            author_notes = notes_element.inner_text().strip()
            # Run a piece of JavaScript to remove the notes element from the page.
            # This ensures it won't be included when we scrape the main content.
            page.evaluate("document.querySelector('.author-note-portlet')?.remove()")
            
        # Scrape the title and the now-cleaned content
        title = page.query_selector(title_selector).inner_text().strip()
        content = page.query_selector(content_selector).inner_text().strip()
        
        return title, content, author_notes
    except Exception as e:
        print(f"❌ Error scraping Royal Road content from {url}: {e}")
        # Return an error message in the title to signify failure
        return f"Error scraping: {url}", None, None

