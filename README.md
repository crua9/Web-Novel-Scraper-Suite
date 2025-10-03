# Web Novel Scraper Suite
This project contains two Python scripts designed to download web novels from ScribbleHub and Royal Road and compile them into a single text file, perfect for use with Text-to-Speech (TTS) applications.

I made this so I can enjoy stories on Royal Road and Scribblehub. One script grabs links to given chapters and puts it in a txt file. And the other script takes those links and grabs the stories and puts them in a txt file. From there I just throw the txt file in a TTS and listen to it like an audio book while I do things. Doing it by hand it took an hour to do about 50 or so chapters. This takes seconds.

# The Scripts
This suite consists of two main scripts that work together:

1. grab_links.py (Chapter Link Grabber): This script visits the main page of a story and scrapes the URLs for every single chapter.
2. scraper.py (Chapter Content Scraper): This script reads a list of chapter URLs and scrapes the title and story content from each one, compiling them into a final text file.

# Features
* Multi-Site Support: Works seamlessly with both ScribbleHub and Royal Road.
* Resumable Scraping: The content scraper tracks its progress, allowing you to stop and resume without losing your place.
* Automatic Retries: If a chapter fails to load, the script will automatically try again a few times.
* Correctly Ordered Output: The final text file is always sorted in the correct chronological chapter order.
* Error Logging: Failed URLs are saved to failed_chapters.txt for easy troubleshooting.

# Requirements
Before you can run these scripts, you need to have Python installed on your system.

Python 3: This script is written for Python 3. You can download it from the official Python website. During installation, it's highly recommended to check the box that says "Add Python to PATH".

pip: The Python package installer. This is usually included with modern Python installations.

# Installation
These scripts use the Playwright library to control a web browser. To set it up, you need to run two commands in your terminal or command prompt.

Install the Playwright Python library:

pip install playwright

Install the browsers for Playwright:
This command downloads the browser files that Playwright needs to operate. This may take a few minutes.

playwright install

Once both commands have finished, your system is ready.

How to Use: The Two-Step Process
Step 1: Grab the Chapter Links
Run the link grabber script in your terminal:

python grab_links.py

# Follow the prompts:

Story URL: Paste the main series/fiction page URL from ScribbleHub or Royal Road.

Output file name: The base name for the link files (e.g., "World Keeper Links").

Links per file: How many links to put in each text file.

This will create a links folder containing one or more .txt files filled with chapter URLs.

Step 2: Scrape the Chapter Content
Create chapter_list.txt: In the same main folder, create a new file named chapter_list.txt.

Consolidate Links: Open the .txt files inside the links folder, copy all the URLs, and paste them into chapter_list.txt. Each URL should be on its own line.

Run the content scraper script:

python scraper.py

Follow the prompts:

Confirm you've added URLs to chapter_list.txt.

Enter the desired name for your final, compiled story file (e.g., World Keeper Story).

The script will now open a browser and begin scraping the content for each chapter, saving your complete story to a single text file.

What the Scripts Do
Chapter Link Grabber (grab_links.py)
It opens a visible browser window (do not close or minimize it).

It navigates to the story URL you provide.

It detects the website (ScribbleHub or Royal Road) and uses the appropriate method to find all chapter links.

For ScribbleHub, it clicks the "Show All Chapters" button and waits for the full list to load.

For Royal Road, it reads the chapter data directly from the page's code.

It organizes the links in chronological order.

It creates a new folder named links.

Finally, it saves the chapter URLs into one or more .txt files inside the links folder.

Chapter Content Scraper (scraper.py)
It reads chapter_list.txt to find URLs that haven't been scraped yet (the ones without a ✔ checkmark).

It opens a visible browser window that should not be closed or minimized.

It navigates to each URL on its to-do list, one by one.

It detects the website and uses the correct method to find the chapter title and story content.

As each chapter is successfully scraped, it appends the formatted content to your final output file (e.g., My Awesome Story.txt).

It then updates chapter_list.txt, marking the line with a ✔ and the chapter title so it won't be scraped again.

If a chapter fails to load, it will automatically retry a few times before moving on.

After all scraping is finished, it re-reads the final output file and sorts all the chapters into the correct chronological order.

Any URLs that could not be scraped are saved in a separate failed_chapters.txt file for you to review.
