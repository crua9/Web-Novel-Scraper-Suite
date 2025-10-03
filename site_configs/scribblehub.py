import re
from playwright.sync_api import TimeoutError

# This variable is used by the main script to identify which URLs this config handles.
DOMAIN = "scribblehub.com"
# This tells the main script that the chapter list from the site needs to be reversed.
REVERSE_CHAPTERS = True 

def get_links(page):
    """
    Scrapes all chapter links from a ScribbleHub series page.
    This function is called by the main scraper script.
    """
    try:
        print("📖 Clicking the 'Show All Chapters' icon...")
        # Use Playwright's get_by_title locator, which is robust
        page.get_by_title("Show All Chapters").click()
        
        print("⏳ Waiting for all chapters to load... (this might take a minute or two)")
        # Wait for the pagination element to disappear, which signals the full list has loaded.
        page.wait_for_selector("#pagination-mesh-toc", state="hidden", timeout=120000)
        print("✅ TOC fully loaded.")
        
        links = page.query_selector_all(".toc_ol .toc_a")
        base_url = "https://www.scribblehub.com"
        urls = []
        for link in links:
            href = link.get_attribute("href")
            if href:
                # Ensure the URL is absolute
                if href.startswith('/'):
                    urls.append(base_url + href.strip())
                else:
                    urls.append(href.strip())
        return urls
    except TimeoutError:
        print("❌ Timed out waiting for the full chapter list to load on ScribbleHub.")
        return []
    except Exception as e:
        print(f"❌ An error occurred during ScribbleHub link scraping: {e}")
        return []

def get_content(page, url):
    """
    Scrapes the title, content, and author's notes from a ScribbleHub chapter page.
    This function is called by the main scraper script.
    """
    try:
        # Navigate to the chapter page with a generous timeout
        page.goto(url, timeout=60000)
        # Wait until the initial HTML is parsed
        page.wait_for_load_state("domcontentloaded", timeout=60000)
        
        # Define the specific CSS selectors for ScribbleHub
        title_selector = "div.chapter-title"
        content_selector = "#chp_raw"
        notes_selector = ".wi_authornotes"

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
            page.evaluate("document.querySelector('.wi_authornotes')?.remove()")

        # Scrape the title and the now-cleaned content
        title = page.query_selector(title_selector).inner_text().strip()
        content = page.query_selector(content_selector).inner_text().strip()
        
        return title, content, author_notes
    except Exception as e:
        print(f"❌ Error scraping ScribbleHub content from {url}: {e}")
        # Return an error message in the title to signify failure
        return f"Error scraping: {url}", None, None

