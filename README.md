# Web Novel Scraper Suite
This project contains two Python scripts designed to download web novels from ScribbleHub and Royal Road and compile them into a single text file, perfect for use with Text-to-Speech (TTS) applications.

I made this so I can enjoy stories on Royal Road and Scribblehub. One script grabs links to given chapters and puts it in a txt file. And the other script takes those links and grabs the stories and puts them in a txt file. From there I just throw the txt file in a TTS and listen to it like an audio book while I do things. Doing it by hand it took an hour to do about 50 or so chapters. This takes seconds.

# The Scripts
This suite consists of two main scripts that work together:

1. grab_links.py (Chapter Link Grabber): This script visits the main page of a story and scrapes the URLs for every single chapter.
2. scraper.py (Chapter Content Scraper): This script reads a list of chapter URLs and scrapes the title and story content from each one, compiling them into a final text file.

# What the Scripts Does
Chapter Link Grabber (grab_links.py)
* It opens a visible browser window (do not close or minimize it).
* It navigates to the story URL you provide.
* It detects the website (ScribbleHub or Royal Road) and uses the appropriate method to find all chapter links.
* For ScribbleHub, it clicks the "Show All Chapters" button and waits for the full list to load.
* For Royal Road, it reads the chapter data directly from the page's code.
* It organizes the links in chronological order.
* It creates a new folder named links.
* Finally, it saves the chapter URLs into one or more .txt files inside the links folder.

Chapter Content Scraper (scraper.py)
* It reads chapter_list.txt to find URLs that haven't been scraped yet (the ones without a ✔ checkmark).
* It opens a visible browser window that should not be closed or minimized.
* It navigates to each URL on its to-do list, one by one.
* It detects the website and uses the correct method to find the chapter title and story content.
* As each chapter is successfully scraped, it appends the formatted content to your final output file (e.g., My Awesome Story.txt).
* It then updates chapter_list.txt, marking the line with a ✔ and the chapter title so it won't be scraped again.
* If a chapter fails to load, it will automatically retry a few times before moving on.
* After all scraping is finished, it re-reads the final output file and sorts all the chapters into the correct chronological order.
* Any URLs that could not be scraped are saved in a separate failed_chapters.txt file for you to review.


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

# How to use it?

I tried to make this as idiot proof as possible. I suggest running your scripts in 1 folder location. Basically run the grabber script. You need to use a link to a story, use the main area where you can get a table of context like
https://www.royalroad.com/fiction/108300/arcanist-in-another-world-a-healer-archmage-isekai
https://www.scribblehub.com/series/10442/world-keeper/

Run that, and it will quickly generate txt files in a sub folder. I did it this way so it doesn't flood the main one because it will grab all the chapters. 

From here you can make a file in the main with the scripts named "chapter_list" make sure it is a txt file. Or change one of the files you made into that, and move it to where the scripts are.

Then go to the other script and do a paint by numbers with that one. It will basically ask you to confirm you did the above. It will ask you what to call the txt file it will generate. Personally I do [story title] chapters. So like timelord 50-100 so I know in that it has chapters 50-100 in that file. (why not the entire book. Most TTS freak out, and it is easier to deal with it like this if you accidently skipped around)


Anyways, from there just let it do it's thing and you should have it in short order.

If something goes wrong, I added an ability where you should be able to tell it to try again. Using the chapter list, it edits it as it goes through so it knows what it already found and where to place the new content. Again I tried to make this as paint by numbers as possible. 
