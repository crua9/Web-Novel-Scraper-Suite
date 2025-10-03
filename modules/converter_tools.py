import os
import re
from .utils import check_and_install_dependencies, print_progress_bar, parse_output_file

def create_epub_from_files():
    """Combines one or more text files into a single EPUB ebook."""
    from __main__ import EBOOKLIB_INSTALLED
    if not EBOOKLIB_INSTALLED:
        if not check_and_install_dependencies(['ebooklib']):
            return
            
    print("\n" + "─"*10 + " Create EPUB Ebook " + "─"*10)
    print("This feature is not yet implemented.")

def create_edge_html_from_file():
    """Converts a story text file into an HTML file for Edge's Read Aloud."""
    print("\n" + "─"*10 + " Create HTML for Edge " + "─"*10)
    print("This feature is not yet implemented.")

def create_mp3s_from_file():
    """Converts a story text file into chapter-by-chapter MP3 audio files."""
    from __main__ import GTTS_INSTALLED
    if not GTTS_INSTALLED:
        if not check_and_install_dependencies(['gtts']):
            return
    print("\n" + "─"*10 + " Create MP3 Audio Files " + "─"*10)
    print("This feature is not yet implemented.")
