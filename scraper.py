import os
import requests
from typing import List, Optional, Dict
import time
from urllib.parse import urlparse, quote
import re # Added for slugify
import asyncio

# Try to import from youtube_transcriber
try:
    from youtube_transcriber import extract_video_id, get_youtube_transcript
    YOUTUBE_TRANSCRIBER_AVAILABLE = True
except ImportError:
    print("Warning: youtube_transcriber.py not found or YouTubeTranscriptApi not installed. YouTube transcript appending will be skipped.")
    YOUTUBE_TRANSCRIBER_AVAILABLE = False
    # Define dummy functions if not available to prevent NameError later, though logic will skip them
    def extract_video_id(url: str) -> Optional[str]: return None
    def get_youtube_transcript(video_id: str, languages: Optional[List[str]] = None) -> Optional[str]: return None

# --- Helper Function for Filename Generation ---
def slugify(text: str, max_length: int = 200) -> str:
    """
    Converts a string into a "slug" suitable for use as a filename.
    Lowercase, spaces to underscores, removes most special characters.
    """
    if not text:
        return "untitled_article"
    # Remove characters that are not alphanumeric, underscores, hyphens, or spaces
    s = re.sub(r'[^\w\s-]', '', text).strip().lower()
    # Replace spaces and hyphens with a single underscore
    s = re.sub(r'[-\s]+', '_', s)
    # Remove any leading/trailing underscores that might have resulted
    s = s.strip('_')
    # Truncate to max_length
    s = s[:max_length]
    # If the slugging resulted in an empty string (e.g., title was all special chars)
    if not s:
        return "untitled_article"
    return s

# --- Fallback HTML Scraper ---
def fallback_html_scrape(url: str, max_chars: int = 10000) -> Optional[str]:
    """
    Simple fallback HTML-to-text scraper using requests and BeautifulSoup.
    Only used if Jina AI fails and the page is not YouTube.
    """
    try:
        import bs4
    except ImportError:
        print("[Fallback Scraper] BeautifulSoup4 not installed. Skipping fallback scraping.")
        return None
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        soup = bs4.BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        return text[:max_chars]
    except Exception as e:
        print(f"[Fallback Scraper] Failed to scrape {url}: {e}")
        return None

# --- llm-reader Scraper (async API) ---
def llm_reader_scrape(url: str, max_chars: int = 10000) -> str:
    """
    Scrape content using llm-reader (open source, local, LLM-friendly Markdown).
    Uses the new async API from url_to_llm_text.
    """
    try:
        from url_to_llm_text.get_html_text import get_page_source
        from url_to_llm_text.get_llm_input_text import get_processed_text
    except ImportError:
        print("[llm-reader] llm-reader not installed or import failed. Please run 'pip install git+https://github.com/m92vyas/llm-reader.git'. Skipping llm-reader scraping.")
        return None
    async def scrape_async(url, max_chars):
        try:
            print(f"[llm-reader] Getting page source for: {url}")
            page_source = await get_page_source(url)
            print(f"[llm-reader] Got page source for: {url} (length: {len(page_source) if page_source else 0})")
            print(f"[llm-reader] Processing page source for: {url}")
            llm_text = await get_processed_text(page_source, url)
            print(f"[llm-reader] Got processed text for: {url} (length: {len(llm_text) if llm_text else 0})")
            if llm_text and llm_text.strip():
                return llm_text[:max_chars]
            else:
                print(f"[llm-reader] No content returned for {url}.")
        except Exception as e:
            print(f"[llm-reader] Failed to scrape {url}: {e}")
        return None
    try:
        print(f"[llm-reader] Starting async scrape for: {url}")
        result = asyncio.run(scrape_async(url, max_chars))
        print(f"[llm-reader] Finished async scrape for: {url}")
        return result
    except RuntimeError:
        import nest_asyncio
        nest_asyncio.apply()
        print(f"[llm-reader] Starting async scrape (nest_asyncio) for: {url}")
        result = asyncio.get_event_loop().run_until_complete(scrape_async(url, max_chars))
        print(f"[llm-reader] Finished async scrape (nest_asyncio) for: {url}")
        return result

# --- Jina Reader Scraper ---
def jina_reader_scrape(url: str, headers: dict = None, max_chars: int = 10000) -> Optional[str]:
    """
    Scrape content using Jina Reader API. Returns None if 402/429 or empty/error content.
    """
    if not url.startswith(('http://', 'https://')):
        print(f"[Jina Reader] Invalid URL (missing scheme): {url}")
        return None
    jina_reader_url = f"https://r.jina.ai/{url}"
    try:
        response = requests.get(jina_reader_url, headers=headers or {}, timeout=45)
        if response.status_code in [402, 429]:
            print(f"[Jina Reader] Rate limit or payment required for {url} (status {response.status_code}).")
            return None
        response.raise_for_status()
        text = response.text.strip()
        # Heuristic: consider empty or error pages as failure
        if not text or 'error' in text.lower() or len(text) < 100:
            print(f"[Jina Reader] Empty or error content for {url}.")
            return None
        return text[:max_chars]
    except requests.exceptions.Timeout:
        print(f"[Jina Reader] Timeout for {url}")
    except requests.exceptions.RequestException as e:
        print(f"[Jina Reader] Request error for {url}: {e}")
    except Exception as e:
        print(f"[Jina Reader] Unexpected error for {url}: {e}")
    return None

# --- Main Scraping Function ---
def scrape_urls_to_markdown(
    items_to_scrape: List[Dict[str, str]],
    output_folder: str,
    jina_api_key: Optional[str] = None,
    delay: float = 1.0,
    youtube_transcript_languages: Optional[List[str]] = None,
    # method: str = "auto"  # 'jina', 'llm-reader', 'fallback', or 'auto'
    method: str = "llm-reader"
    
) -> None:
    """
    Scrape URLs using the selected method. 'auto' tries Jina, then llm-reader, then fallback.
    Only attempts YouTube transcript if the URL is a valid YouTube link.
    """
    if not items_to_scrape:
        print("No items provided to scrape.")
        return
    if youtube_transcript_languages is None:
        youtube_transcript_languages = ['en']
    os.makedirs(output_folder, exist_ok=True)
    print(f"Ensured output directory exists: {output_folder}")
    # --- Rate limit config ---
    if jina_api_key:
        max_rpm = 500  # Free API key
        jina_headers = {'Authorization': f'Bearer {jina_api_key}'}
    else:
        max_rpm = 20   # No API key
        jina_headers = {}
    min_delay = max(delay, 60.0 / max_rpm)
    seen_urls = set()
    num_items = len(items_to_scrape)
    for i, item in enumerate(items_to_scrape):
        url = item.get('url')
        original_title = item.get('title', '')
        content = None
        youtube_transcript_text = None
        if not url or not original_title:
            print(f"Skipping item due to missing URL or title: {item}")
            continue
        if url in seen_urls:
            print(f"Skipping duplicate URL in this run: {url}")
            continue
        seen_urls.add(url)
        print(f"\n[{i+1}/{num_items}] Processing: '{original_title}' ({url})")
        # --- Scraping logic by method ---
        tried = []
        methods_to_try = []
        if method == "auto":
            methods_to_try = ["jina", "llm-reader", "fallback"]
        else:
            methods_to_try = [method]
        for m in methods_to_try:
            print(f"[Scraper] Attempting method '{m}' for {url}")
            if m == "jina":
                content = jina_reader_scrape(url, headers=jina_headers)
                tried.append("jina")
            elif m == "llm-reader":
                content = llm_reader_scrape(url)
                tried.append("llm-reader")
            elif m == "fallback":
                content = fallback_html_scrape(url)
                tried.append("fallback")
            print(f"[Scraper] Finished attempt with method '{m}' for {url} (content length: {len(content) if content else 0})")
            if content:
                print(f"[Scraper] Successfully scraped content for {url} using {m}.")
                break
        if not content:
            print(f"[Scraper] No content could be scraped for {url} (tried: {', '.join(tried)}). Skipping file save.")
            if i < num_items - 1:
                print(f"Waiting for {min_delay:.2f} seconds before next request...")
                time.sleep(min_delay)
            continue
        # --- YouTube transcript only if valid YouTube link ---
        video_id = None
        if YOUTUBE_TRANSCRIBER_AVAILABLE:
            video_id = extract_video_id(url)
            if video_id:
                print(f"Detected YouTube URL. Attempting to fetch transcript for video ID: {video_id} (Languages: {youtube_transcript_languages})")
                transcript_text = get_youtube_transcript(video_id, languages=youtube_transcript_languages)
                if transcript_text:
                    youtube_transcript_text = transcript_text
                    print(f"Successfully fetched transcript for YouTube video {video_id}.")
                else:
                    print(f"Could not fetch transcript for YouTube video {video_id}. No transcript will be appended.")
        # --- Combine content and save ---
        final_content_to_save = content
        if youtube_transcript_text:
            transcript_header = "\n\n---\n\n## YouTube Transcript\n\n"
            if not final_content_to_save:
                final_content_to_save = f"# {original_title}\nURL: {url}\n{transcript_header}{youtube_transcript_text}"
            else:
                final_content_to_save += f"{transcript_header}{youtube_transcript_text}"
        base_filename_slug = slugify(original_title)
        filename_candidate = f"{base_filename_slug}.md"
        filepath = os.path.join(output_folder, filename_candidate)
        counter = 1
        while os.path.exists(filepath):
            filename_candidate = f"{base_filename_slug}_{counter}.md"
            filepath = os.path.join(output_folder, filename_candidate)
            counter += 1
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(final_content_to_save)
            source_info = ", ".join(tried)
            if youtube_transcript_text and content: source_info += " + YouTube Transcript"
            elif youtube_transcript_text: source_info = "YouTube Transcript (web scrape failed or no content)"
            print(f"Successfully saved content from '{source_info}' for '{original_title}' to {filepath}")
        except IOError as e_io:
            print(f"Error saving file {filepath}: {e_io}")
        if i < num_items - 1:
            print(f"Waiting for {min_delay:.2f} seconds before next request...")
            time.sleep(min_delay)
    print(f"\nScraping finished. Files saved in '{output_folder}' (if any content was successfully fetched).")

# --- Example Usage ---
if __name__ == "__main__":
    from dotenv import load_dotenv
    try:
        from search import get_brave_search_results
    except ImportError:
        print("Error: Could not import 'get_brave_search_results' from search.py.")
        print("Make sure search.py is in the same directory.")
        exit(1)

    load_dotenv()
    brave_key = os.environ.get("BRAVE_API_KEY")
    jina_key = os.environ.get("JINA_API_KEY")

    if not brave_key or brave_key == "YOUR_BRAVE_API_KEY":
         print("Warning: BRAVE_API_KEY not found. Search functionality will be skipped or may fail.")

    # --- Configuration ---
    search_query = "portugal youtube abelhas apicultura mel enxame youtube"
    num_results_to_scrape = 10 # Keep it lower for testing this logic
    results_folder = "scraped_content_with_transcripts" 
    request_delay = 1.5
    youtube_transcript_preferred_languages = ['pt', 'en'] 
    # --- End Configuration ---

    items_for_scraping: List[Dict[str, str]] = []

    if brave_key and brave_key != "YOUR_BRAVE_API_KEY":
        print(f"Performing Brave search for: '{search_query}'...")
        search_results_list = get_brave_search_results(search_query, brave_key, count=num_results_to_scrape)

        if search_results_list:
            items_for_scraping = [
                item for item in search_results_list 
                if item.get('url') and item.get('title')
            ]
            print(f"\nFound {len(items_for_scraping)} valid items (with URL and title) to scrape:")
            for item_idx, item_val in enumerate(items_for_scraping):
                print(f"- {item_idx+1}. Title: '{item_val.get('title')}', URL: <{item_val.get('url')}>")
        else:
            print("Failed to get search results from Brave or no results found.")
    else:
         print("Brave search skipped or API key missing. Using predefined example items.")
         # Ensure example items include a YouTube link for testing this new logic
         items_for_scraping = [
             {"title": "Beekeeping in Portugal - A YouTube Example", "url": "https://www.youtube.com/watch?v=DrBjK1zU7PM"}, 
             {"title": "Jina AI Reader Official Page", "url": "https://jina.ai/reader/"},
             {"title": "What Is Web Scraping - Wikipedia", "url": "https://en.wikipedia.org/wiki/Web_scraping"},
         ]
         print(f"Using {len(items_for_scraping)} example items.")
         for item_idx, item_val in enumerate(items_for_scraping):
             print(f"- {item_idx+1}. Title: '{item_val.get('title')}', URL: <{item_val.get('url')}>")

    if items_for_scraping:
         print(f"\nStarting scraping process, saving to '{results_folder}'...")
         scrape_urls_to_markdown(
             items_for_scraping, 
             results_folder, 
             jina_api_key=jina_key, 
             delay=request_delay,
             youtube_transcript_languages=youtube_transcript_preferred_languages
        )
    else:
         print("No items to scrape. Either search failed or no example items were defined.") 