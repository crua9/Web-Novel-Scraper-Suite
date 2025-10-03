# Web Novel Scraper Suite
My Motivation

I made this so I can enjoy stories on Royal Road and Scribblehub. I wanted a simple way to download web novels and listen to them with Text-to-Speech (TTS) like an audiobook while I do other things. Doing this by hand used to take me an hour for just 50 chapters; this suite does it in seconds.

The Scraper Suite
This project has been combined into a single, powerful, menu-driven script: Web-Novel-Scraper-Suite.py. It handles the entire process from finding chapter links to creating final files for reading or listening, supporting both ScribbleHub and Royal Road.

The old standalone scripts (grab_links.py and scraper.py) are still included as a backup in case you run into any issues, but the main suite is the recommended and easiest way to use this tool. I made it to make it an all in 1 thing. 

If you run into problems, give the script, error, and site to an AI. Note I made it where other sites can be added or the ones I use can be edited if needed in it's own system config files. 

# What the Suite Does (The Workflow)
The suite guides you through a simple, step-by-step process using a main menu:

* Scrape Chapter Links (Option 1):
    * You provide a story's main URL.
    * The script automatically creates a dedicated project folder for your story.
    * It scrapes all chapter links and saves them into numbered .txt files inside your project's links subfolder.
* Assemble chapter_list.txt (Option 4):
    * You select your project.
    * The script shows you all the link files it found (e.g., "Links 1-100.txt", "Links 101-200.txt", etc.).
    * You choose which files you want to process. This gives you the flexibility to work with a whole book or just a small batch of chapters.
    * It then creates a master chapter_list.txt inside your project folder containing only the URLs you selected.

* Scrape Story Content (Option 5):
    * This is the core function. It reads the chapter_list.txt you just created.
    * It intelligently scrapes only the chapters that haven't been downloaded yet (it marks completed ones with a ✔).
    * As it successfully scrapes each chapter, it adds it to a main story file and updates the chapter_list.txt so you can safely stop and resume at any time.
    * If a chapter fails, it retries a few times automatically.
    * After scraping, it rebuilds the final .txt file to ensure every chapter is in the correct chronological order.
    * Any links that fail repeatedly are saved to a failed_chapters.txt file for you to review.

* Conversion Tools (Options 6, 7, 8):
   * Once you have a scraped .txt file, you can easily convert it into other formats:
   * EPUB: For e-readers.
   * HTML: A clean, single-page file perfect for Microsoft Edge's "Read Aloud" feature.
   * MP3: Creates individual audio files for each chapter using Google's Text-to-Speech.

# Requirements

Python 3: You can download it from the official Python website. Important: During installation, check the box that says "Add Python to PATH".

pip: The Python package installer, which is included with modern Python installations.

Installation
The script will handle installing its own dependencies, but if you want to do it manually, open your terminal or command prompt and run this single command:

pip install playwright requests ebooklib gtts

After that, you need to install the browser files that Playwright uses. This only needs to be done once.

playwright install

Once both commands have finished, you're ready to go.

# How to Use It (The Simple Way)
I tried to make this as idiot-proof as possible.

* Run the Main Script:
   * Open your terminal or command prompt in the project folder and run:
   * python Web-Novel-Scraper-Suite.py
   * Scrape Links (Option 1):
* Choose option 1 from the menu.
   * Paste the main URL for a story on ScribbleHub or Royal Road (e.g., https://www.scribblehub.com/series/10442/world-keeper/).
   * Give your project a name when prompted (e.g., "World Keeper"). The script handles all the folder creation automatically.
* Assemble a Batch (Option 4):
   * Choose option 4 from the menu and select the project you just created.
   * The script will show you the link files it made. Choose the ones you want to process for this batch (e.g., just the file for chapters 1-100).
   * This creates the chapter_list.txt that the scraper will use.

* Scrape the Content (Option 5):
   * Choose option 5 and select your project.
   * The script will ask what you want to name the final text file. I recommend naming it by chapter batch (e.g., "World Keeper 1-100.txt"). This makes it easy to manage for TTS, which can sometimes struggle with very large files.
   * Let the script run. A browser window will open and do the work. It will close automatically when finished.

* Convert (Optional):
   * If you want an EPUB, HTML, or MP3 files, just choose the corresponding option from the menu and select the .txt file you just created.

 Note the MP3 might take a good while. It is better to use other things if you want to do that. If you use eleven labs or like services, you can convert an entire book txt file to EPUB and it will note the chapters.
 The HTML I added that in because Edge browser has a TTS many like to use.
