import os
import json
import importlib
import sys
import subprocess
import re

# --- Theme Definitions ---
THEMES = {
    "cyberpunk": {"P": "\033[95m", "S": "\033[96m", "G": "\033[92m", "Y": "\033[93m", "R": "\033[91m", "W": "\033[0m"},
    "matrix": {"P": "\033[32m", "S": "\033[92m", "G": "\033[92m", "Y": "\033[33m", "R": "\033[31m", "W": "\033[0m"},
    "classic": {"P": "\033[94m", "S": "\033[97m", "G": "\033[92m", "Y": "\033[93m", "R": "\033[91m", "W": "\033[0m"}
}

def get_theme_colors():
    config = load_config()
    return THEMES.get(config.get("theme", "cyberpunk"), THEMES["cyberpunk"])

CONFIG_FILE = "config.json"
STORIES_DB = "stories_db.json"
SITE_CONFIGS_DIR = "site_configs"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f: return json.load(f)
    return {"theme": "cyberpunk", "github_repo_url": "https://api.github.com/repos/crua9/Web-Novel-Scraper-Suite/contents/site_configs"}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f: json.dump(config, f, indent=4)

def load_stories_db():
    if os.path.exists(STORIES_DB):
        with open(STORIES_DB, 'r') as f: return json.load(f)
    return {}

def save_stories_db(db):
    with open(STORIES_DB, 'w') as f: json.dump(db, f, indent=4)

def load_site_configs():
    configs = {}
    if not os.path.exists(SITE_CONFIGS_DIR): os.makedirs(SITE_CONFIGS_DIR)
    for filename in os.listdir(SITE_CONFIGS_DIR):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = f"{SITE_CONFIGS_DIR}.{filename[:-3]}"
            configs[filename[:-3]] = importlib.import_module(module_name)
    return configs

# --- BOUNDARY-AWARE Link Management ---
def save_chunks(links, story_path, story_name, chunk_size=100):
    """Saves links into /links/ subfolder, respecting 100-chapter block boundaries."""
    links_dir = os.path.join(story_path, "links")
    os.makedirs(links_dir, exist_ok=True)
    existing_files = os.listdir(links_dir)
    
    # 1. Find the absolute highest chapter number currently saved
    highest_chapter = 0
    for f_name in existing_files:
        match = re.search(r'-(\d+)', f_name)
        if match:
            highest_chapter = max(highest_chapter, int(match.group(1)))

    if highest_chapter >= len(links):
        return

    # 2. Start from where we left off
    start_index = highest_chapter 
    remaining_links = links[start_index:]
    
    # 3. Calculate how many chapters are needed to reach the next boundary (e.g., 500)
    # If highest is 479, remainder is 21 (479 % 100 = 79; 100 - 79 = 21)
    # If highest is 500, remainder is 0 (500 % 100 = 0)
    to_next_boundary = chunk_size - (highest_chapter % chunk_size)
    if to_next_boundary == chunk_size: # We are exactly at a boundary (e.g., 500)
        to_next_boundary = 0

    current_ptr = 0

    # 4. Fill the gap to the boundary first (e.g., chapters 480-500)
    if to_next_boundary > 0 and current_ptr < len(remaining_links):
        gap_chunk = remaining_links[current_ptr : current_ptr + to_next_boundary]
        gap_start = highest_chapter + 1
        gap_end = highest_chapter + len(gap_chunk)
        
        file_name = f"{story_name} {gap_start}-{gap_end}.txt"
        with open(os.path.join(links_dir, file_name), "w", encoding="utf-8") as f:
            for link in gap_chunk: f.write(f"{link}\n")
            
        current_ptr += len(gap_chunk)

    # 5. Save everything else in standard blocks of 100 (e.g., 501-600)
    while current_ptr < len(remaining_links):
        standard_chunk = remaining_links[current_ptr : current_ptr + chunk_size]
        std_start = highest_chapter + current_ptr + 1
        std_end = highest_chapter + current_ptr + len(standard_chunk)
        
        file_name = f"{story_name} {std_start}-{std_end}.txt"
        with open(os.path.join(links_dir, file_name), "w", encoding="utf-8") as f:
            for link in standard_chunk: f.write(f"{link}\n")
            
        current_ptr += len(standard_chunk)

def read_all_links_from_folder(story_path):
    links = []
    links_dir = os.path.join(story_path, "links")
    if not os.path.exists(links_dir): return links
    
    files = sorted(os.listdir(links_dir), key=lambda x: int(re.search(r'(\d+)-', x).group(1)) if re.search(r'(\d+)-', x) else 0)
    for filename in files:
        if filename.endswith(".txt"):
            with open(os.path.join(links_dir, filename), "r", encoding="utf-8") as f:
                links.extend([line.strip() for line in f if line.strip()])
    return list(dict.fromkeys(links))

# --- Step status: plain messages, no background threads ---
class Spinner:
    """Usage:  with Spinner("Closing browser"): slow_thing()
    Prints  ⏳ Closing browser...  then  ✅ Closing browser (3s)"""
    active = None

    def __init__(self, message):
        self.message = message
        self.paused = False

    def __enter__(self):
        import time
        self._start = time.time()
        clr = get_theme_colors()
        print(f"{clr['S']}⏳ {self.message}...{clr['W']}", flush=True)
        return self

    def __exit__(self, exc_type, exc, tb):
        import time
        clr = get_theme_colors()
        secs = int(time.time() - self._start)
        if exc_type is None:
            print(f"{clr['G']}✅ {self.message} done ({secs}s){clr['W']}", flush=True)
        elif exc_type is not KeyboardInterrupt:
            print(f"{clr['R']}❌ {self.message} failed ({secs}s){clr['W']}", flush=True)
        return False

# --- Browser launching (Cloudflare-friendly) ---
BROWSER_PROFILE_DIR = "browser_profile"
CHALLENGE_MARKERS = [
    "performing security verification",
    "verify you are human",
    "just a moment",
    "checking your browser",
    "attention required",
]

def open_browser(p):
    """
    Opens a real, persistent browser window and returns (context, page).
    - Uses installed Chrome, then Edge, then Playwright's Chromium as a last resort.
    - Keeps a saved profile in ./browser_profile so the Cloudflare pass cookie survives between runs.
    - Turns off the flags that tell sites the browser is automated.
    Close it with context.close().
    """
    profile = os.path.abspath(BROWSER_PROFILE_DIR)
    os.makedirs(profile, exist_ok=True)
    opts = dict(
        user_data_dir=profile,
        headless=False,
        no_viewport=True,
        args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
        ignore_default_args=["--enable-automation"],
    )
    last_err = None
    for channel in ("chrome", "msedge", None):
        try:
            if channel:
                context = p.chromium.launch_persistent_context(channel=channel, **opts)
            else:
                context = p.chromium.launch_persistent_context(**opts)
            break
        except Exception as e:
            last_err = e
            context = None
    if context is None:
        raise RuntimeError(f"Could not open a browser. Close any open window using the scraper profile and retry. ({last_err})")

    context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
    page = context.pages[0] if context.pages else context.new_page()
    return context, page

def is_challenge_page(page):
    try:
        text = (page.title() + " " + page.inner_text("body", timeout=3000)[:2000]).lower()
    except Exception:
        return False
    return any(m in text for m in CHALLENGE_MARKERS)

def wait_for_cloudflare(page, max_wait=180):
    """If a Cloudflare check is showing, wait for it to clear (you can click it in the window)."""
    import time
    if not is_challenge_page(page):
        return True
    clr = get_theme_colors()
    if Spinner.active:
        Spinner.active.paused = True
        time.sleep(0.3)
    print(f"\n{clr['Y']}🛡️ Cloudflare check detected. Click the checkbox in the browser window if one shows. Waiting up to {max_wait}s...{clr['W']}")
    waited = 0
    while waited < max_wait:
        time.sleep(2)
        waited += 2
        if not is_challenge_page(page):
            print(f"{clr['G']}✅ Cloudflare passed.{clr['W']}")
            time.sleep(2)
            if Spinner.active:
                Spinner.active.paused = False
            return True
    print(f"{clr['R']}❌ Cloudflare check did not clear.{clr['W']}")
    return False

def goto(page, url, timeout=60000, spin=None):
    """Load a page and get past Cloudflare if it shows up. spin='message' shows a spinner while loading."""
    if spin:
        with Spinner(spin):
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    else:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    if not wait_for_cloudflare(page):
        raise RuntimeError("Blocked by Cloudflare")

def extract_author(html):
    """Pull the author's name out of a story page's HTML (Royal Road or ScribbleHub). Returns None if not found."""
    import html as htmlmod
    patterns = [
        r'property="books:author"\s+content="([^"]+)"',
        r'<meta[^>]+name="author"[^>]+content="([^"]+)"',
        r'<h4[^>]*>\s*<span[^>]*>\s*by\s*</span>\s*<span[^>]*>\s*<a[^>]*>([^<]+)</a>',
        r'class="auth_name_fic"[^>]*>([^<]+)<',
        r'<span property="name">([^<]+)</span>',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            name = htmlmod.unescape(m.group(1)).strip()
            if name and not name.lower().startswith("http"):
                return name
    return None

def save_author(page, db, story_name):
    """Read the author from the currently loaded story page and store it in the stories db."""
    try:
        name = extract_author(page.content())
    except Exception:
        name = None
    if name and story_name in db:
        db[story_name]['author'] = name
    return name

def get_all_chapter_links(page, site_config):
    return site_config.get_chapter_links(page)

def scrape_chapter_content(page, url, site_config):
    return site_config.get_chapter_content(page, url)

def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=40, fill='█'):
    clr = get_theme_colors()
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{clr["S"]}{prefix} |{bar}| {percent}% {suffix}{clr["W"]}', end='\r')
    if iteration == total: print()

def check_and_install_dependencies(packages):
    for package in packages:
        try: importlib.import_module(package)
        except ImportError: subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    return True

def clean_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)
