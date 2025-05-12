import os
import requests
from typing import List, Optional, Dict
import time
from urllib.parse import urlparse, quote
import re # Added for slugify and cookie banner removal
import asyncio
import bs4 # Added for cookie banner removal
import trafilatura # Added for main content extraction
from datetime import datetime # Added for timestamp in header

# Attempt to import get_page_source from llm-reader for async HTML fetching
try:
    from url_to_llm_text.get_html_text import get_page_source
    LLM_READER_GET_PAGE_SOURCE_AVAILABLE = True
except ImportError:
    print("[Scraper] llm-reader's get_page_source not found. Install with 'pip install git+https://github.com/m92vyas/llm-reader.git'. HTML fetching for llm_reader_scrape will fail.")
    LLM_READER_GET_PAGE_SOURCE_AVAILABLE = False
    async def get_page_source(url: str, **kwargs) -> Optional[str]: # Dummy definition
        print(f"[Scraper-Dummy] get_page_source called for {url} but llm-reader is not available.")
        return None

# Try to import readability (Re-enabled for fallback)
try:
    from readability import Document
    READABILITY_AVAILABLE = True
except ImportError:
    print("[Scraper] readability-lxml not installed. Run 'pip install readability-lxml'. Fallback to readability will be skipped.")
    READABILITY_AVAILABLE = False

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

# --- Helper function to remove cookie banners ---
def remove_cookie_banners(html_content: str) -> str:
    if not html_content:
        return ""
    try:
        soup = bs4.BeautifulSoup(html_content, "html.parser")
        
        # Keywords and selectors to identify cookie banners
        # This list can be expanded based on common patterns
        keywords = [
            "cookie", "consent", "privacy", "gdpr", "lgpd", 
            "aceitar", "accept", "manage preferences", "politica de cookies",
            "cookie policy", "uses cookies", "utilizamos cookies"
        ]
        selectors = [
            "div[id*='cookie']", "div[class*='cookie']",
            "div[id*='consent']", "div[class*='consent']",
            "div[id*='banner']", "div[class*='banner']", # More generic, might need care
            "div[role='dialog']", # Often used for modals
            "div[aria-modal='true']" 
        ]

        elements_to_remove = []

        # Find by selectors
        for selector in selectors:
            try:
                elements_to_remove.extend(soup.select(selector))
            except Exception: # Catch potential errors from invalid selectors
                pass
        
        # Find by keywords in text content (more expensive, do after specific selectors)
        # We'll be somewhat conservative to avoid removing main content
        for element in soup.find_all(['div', 'section', 'aside']): # Common tags for banners
            text_content = element.get_text(separator=" ", strip=True).lower()
            if any(keyword in text_content for keyword in keywords):
                # Check if it's a large element, could be the main content itself if keywords are too broad
                # This is a simple heuristic; more sophisticated checks could be added
                if len(text_content) < 1000: # Arbitrary threshold
                    is_likely_banner = False
                    # Check for common banner class/id patterns even if not caught by initial selectors
                    for attr in ['id', 'class']:
                        if element.has_attr(attr):
                            attr_value = " ".join(element[attr]).lower()
                            if any(k in attr_value for k in ["cookie", "consent", "banner", "cmp", "overlay"]):
                                is_likely_banner = True
                                break
                    if is_likely_banner:
                         elements_to_remove.append(element)
                    # Further check: if it contains typical action buttons
                    elif element.find(['button', 'a'], string=re.compile(r'(accept|aceitar|agree|concordo|manage|gerir|options|opções|customize|personalizar|decline|recusar)', re.I)):
                        elements_to_remove.append(element)


        # Remove identified elements
        for el in set(elements_to_remove): # Use set to avoid trying to remove an element twice
            if hasattr(el, 'decompose'):
                el.decompose()
        
        return str(soup)
    except Exception as e:
        print(f"[CookieBannerRemover] Error: {e}")
        return html_content # Return original if error

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

# --- llm-reader Scraper (async API) --- Adjusted to use trafilatura + readability fallback ---
async def llm_reader_scrape(url: str, max_chars: Optional[int] = None, youtube_transcript_languages: Optional[List[str]] = None) -> Optional[Dict]:
    # Check if it's a YouTube URL first using the imported function
    video_id = extract_video_id(url) if YOUTUBE_TRANSCRIBER_AVAILABLE else None
    is_youtube = video_id is not None
    youtube_transcript_text = None

    # Always try to get HTML content unless it's ONLY a youtube transcript request (future enhancement?)
    original_title = "Unknown Page"
    processed_html = None
    extracted_text = None
    source_method = "N/A" # Track which method succeeded

    try:
        # Use llm-reader's function to get potentially JS-rendered source
        print(f"[Scraper: Trafilatura/Readability] Getting page source for: {url}")
        # Note: get_page_source internally handles potential playwright errors
        page_source = await get_page_source(url)

        if page_source:
            # 1. Try removing cookie banners (best effort)
            print(f"[Scraper: Trafilatura/Readability] Attempting to remove cookie banners...")
            cleaned_page_source = remove_cookie_banners(page_source)

            # 2. Try extracting with Trafilatura
            print(f"[Scraper: Trafilatura/Readability] Attempting extraction with Trafilatura...")
            extracted_text = trafilatura.extract(
                cleaned_page_source,
                include_comments=False,
                include_tables=True,
                # no_fallback=True # Allow internal fallback? Let's try without it first.
                include_formatting=False, # Start with clean text
                include_links=False
            )
            source_method = "Trafilatura"

            # 3. Fallback to Readability if Trafilatura failed or got minimal content
            MIN_CONTENT_LENGTH = 200
            if READABILITY_AVAILABLE and (not extracted_text or len(extracted_text) < MIN_CONTENT_LENGTH):
                print(f"[Scraper: Trafilatura/Readability] Trafilatura extraction seems insufficient (length {len(extracted_text or '')}). Falling back to Readability...")
                try:
                    doc = Document(cleaned_page_source)
                    original_title = doc.short_title() or doc.title() or original_title
                    # Use summary() which gives text content; content() gives HTML
                    readability_text = doc.summary(html_partial=False) # Get plain text
                    if readability_text and len(readability_text) >= MIN_CONTENT_LENGTH:
                        extracted_text = readability_text
                        source_method = "Readability"
                        print("[Scraper: Trafilatura/Readability] Readability fallback successful.")
                    else:
                         print("[Scraper: Trafilatura/Readability] Readability fallback also insufficient.")
                         # Optional: Could add a third fallback here, e.g., basic BS4 text extraction
                except Exception as read_e:
                    print(f"[Scraper: Trafilatura/Readability] Error during Readability fallback: {read_e}")

            # Basic title extraction if Readability wasn't used or failed to get title
            if source_method != "Readability":
                 try:
                      soup_title = bs4.BeautifulSoup(cleaned_page_source, 'html.parser')
                      title_tag = soup_title.find('title')
                      if title_tag and title_tag.string:
                           original_title = title_tag.string.strip()
                 except Exception:
                      pass # Ignore errors getting title

            # Limit characters if needed (apply AFTER extraction)
            if extracted_text and max_chars is not None and len(extracted_text) > max_chars:
                print(f"[Scraper: Trafilatura/Readability] Truncating content from {len(extracted_text)} to {max_chars} characters.")
                extracted_text = extracted_text[:max_chars]

        else:
            print(f"[Scraper: Trafilatura/Readability] Failed to get page source for {url}.")

    except Exception as e:
        print(f"[Scraper: Trafilatura/Readability] Error scraping HTML content for {url}: {e}")
        # Continue to potentially fetch YouTube transcript even if HTML fails

    # --- YouTube Transcript Handling ---
    # Only proceed if the transcriber is available and it's a YouTube URL
    if YOUTUBE_TRANSCRIBER_AVAILABLE and is_youtube and video_id:
        print(f"[Scraper: YouTube] Attempting to fetch transcript for video ID: {video_id} (Languages: {youtube_transcript_languages})")
        # Use the correctly imported function name
        youtube_transcript_text = get_youtube_transcript(video_id, languages=youtube_transcript_languages)
        if youtube_transcript_text:
            print(f"[Scraper: YouTube] Successfully fetched transcript (length: {len(youtube_transcript_text)}).")
            source_method = f"{source_method}+YouTube" if source_method != "N/A" else "YouTube"
        else:
            print(f"[Scraper: YouTube] Failed to fetch transcript or no transcript available.")

    # Return None only if BOTH HTML extraction AND YouTube transcript failed
    if not extracted_text and not youtube_transcript_text:
        return None

    # Return dictionary with results
    return {
        "url": url,
        "title": original_title,
        "content": extracted_text or "", # Ensure content is always a string
        "youtube_transcript": youtube_transcript_text,
        "method": source_method
    }

# --- Jina AI Reader Scraper ---
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
    method: str = "llm-reader", # Default to our enhanced Trafilatura/Readability combo
    max_chars_per_url: Optional[int] = None # Added missing parameter from llm_reader_scrape
    
) -> None:
    """
    Scrape URLs using the specified method and save content as Markdown files.
    Handles async execution for 'llm-reader' and sync for others.
    """
    if not items_to_scrape:
        print("No items provided to scrape.")
        return
    if youtube_transcript_languages is None:
        youtube_transcript_languages = ['en']

    os.makedirs(output_folder, exist_ok=True)
    print(f"Ensured output directory exists: {output_folder}")
    print(f"Using scraping method: {method}")

    if method == "jina" and not jina_api_key:
        print("Warning: Jina method selected but JINA_API_KEY not provided. Scraping might fail.")
        jina_headers = {}
    elif method == "jina":
        jina_headers = {'Authorization': f'Bearer {jina_api_key}'}
    
    # --- Rate limit config (simplified) ---
    # Apply delay regardless of method for politeness between requests
    min_delay = delay 
    seen_urls = set()
    num_items = len(items_to_scrape)
    
    # Lists to store tasks and results
    tasks = []
    sync_results = [] # Store results from synchronous methods
    item_details = {} # Store details like title associated with each task/URL

    # --- Prepare Tasks/Run Sync Methods ---
    loop = asyncio.get_event_loop() # Get event loop once
    for i, item in enumerate(items_to_scrape):
        url = item.get('url')
        original_title = item.get('title', '')
        if not url or not original_title:
            print(f"Skipping item {i+1} due to missing URL or title: {item}")
            continue
        if url in seen_urls:
            print(f"Skipping duplicate URL in this run: {url}")
            continue
        seen_urls.add(url)
        print(f"\n[{i+1}/{num_items}] Processing: '{original_title}' ({url})")

        # Store item details for later result processing
        item_details[url] = item

        # Select and prepare/run the scraping method
        if method == "llm-reader":
            if LLM_READER_GET_PAGE_SOURCE_AVAILABLE:
                 print(f"[Scraper] Preparing async task (llm-reader) for {url}")
                 tasks.append(loop.create_task(llm_reader_scrape(url, max_chars=max_chars_per_url, youtube_transcript_languages=youtube_transcript_languages)))
            else:
                 print(f"[Scraper] Skipping llm-reader for {url} as get_page_source is unavailable.")
                 sync_results.append(None) # Add a placeholder failure
        elif method == "jina":
            print(f"[Scraper] Executing sync method (jina) for {url}")
            # Note: jina_reader_scrape returns content string or None
            jina_content = jina_reader_scrape(url, headers=jina_headers, max_chars=max_chars_per_url or 10000) 
            sync_results.append({ # Mimic dict structure from async result
                "url": url,
                "title": original_title,
                "content": jina_content or "",
                "youtube_transcript": None, # Jina doesn't handle transcripts
                "method": "Jina" if jina_content else "Jina (Failed)"
            }) 
        elif method == "fallback":
            print(f"[Scraper] Executing sync method (fallback) for {url}")
            # Note: fallback_html_scrape returns content string or None
            fallback_content = fallback_html_scrape(url, max_chars=max_chars_per_url or 10000)
            sync_results.append({ # Mimic dict structure
                "url": url,
                "title": original_title,
                "content": fallback_content or "",
                "youtube_transcript": None,
                "method": "Fallback" if fallback_content else "Fallback (Failed)"
            })
        else:
            print(f"Unknown scraping method: {method}. Skipping URL {url}.")
            sync_results.append(None) # Add a placeholder failure

        # Apply delay *between* starting requests/tasks
        if i < num_items - 1:
            print(f"Waiting {min_delay:.2f} seconds before next request/task...")
            time.sleep(min_delay)

    # --- Run Async Tasks ---
    async_results = []
    if tasks:
        print(f"\nRunning {len(tasks)} async scraping tasks...")
        # Use try/except for runtime errors (e.g., nested loops)
        try:
            async_results = loop.run_until_complete(asyncio.gather(*tasks))
        except RuntimeError as e:
            if "cannot be started again" in str(e):
                 print("Detected running event loop. Attempting to run within existing loop.")
                 # This might happen if called from an already async context, though unlikely here.
                 # In simple script scenarios, the initial loop.run_until_complete is usually fine.
                 # For robustness in complex apps, consider loop management libraries or checks.
                 async def gather_tasks():
                     return await asyncio.gather(*tasks)
                 async_results = loop.run_until_complete(gather_tasks())
            elif "There is no current event loop" in str(e):
                 print("Error: No current event loop. Creating a new one.")
                 loop = asyncio.new_event_loop()
                 asyncio.set_event_loop(loop)
                 async_results = loop.run_until_complete(asyncio.gather(*tasks))
            else:
                 print(f"RuntimeError running async tasks: {e}. Trying nest_asyncio as fallback.")
                 try:
                      import nest_asyncio
                      nest_asyncio.apply()
                      # Retry getting loop and running gather after applying nest_asyncio
                      loop = asyncio.get_event_loop() 
                      async_results = loop.run_until_complete(asyncio.gather(*tasks))
                 except ImportError:
                      print("nest_asyncio not installed. Cannot handle nested loops automatically. Install with 'pip install nest_asyncio'.")
                      async_results = [None] * len(tasks) # Mark tasks as failed
                 except Exception as ne:
                      print(f"Error even after nest_asyncio: {ne}")
                      async_results = [None] * len(tasks) # Mark tasks as failed
        except Exception as ex:
             print(f"Unexpected error running async tasks: {ex}")
             async_results = [None] * len(tasks) # Mark tasks as failed
             
        print("Finished running async tasks.")
    else:
        print("\nNo async tasks were scheduled.")

    # --- Process All Results (Sync + Async) ---
    all_results = sync_results + async_results # Combine results
    saved_count = 0
    print("\nProcessing results and saving files...")
    for result in all_results: 
        if result and isinstance(result, dict) and (result.get("content") or result.get("youtube_transcript")):
            url = result.get("url")
            # Get title from original item details if not in result (might happen with async errors)
            original_title = result.get("title") or (item_details.get(url, {}).get('title', "Untitled"))
            content = result.get("content", "")
            youtube_transcript_text = result.get("youtube_transcript")
            source_method = result.get("method", "Unknown") # Get the method used

            # Create a slug from the title
            slug = slugify(original_title)
            filename = f"{slug}.md"
            filepath = os.path.join(output_folder, filename)

            # Handle potential filename collisions (simple counter)
            counter = 1
            while os.path.exists(filepath):
                filename = f"{slug}_{counter}.md"
                filepath = os.path.join(output_folder, filename)
                counter += 1

            # --- Generate Header ---
            now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            header = f"# {original_title}\n\n**Source URL:** <{url}>\n**Scraped on:** {now}\n**Method:** {source_method}\n\n---\n\n"
            # --- End Header ---

            # --- Combine content and save ---
            final_content_to_save = header + content # Start with header and main content

            if youtube_transcript_text:
                transcript_header = "\n\n---\n\n## YouTube Transcript\n\n"
                final_content_to_save += f"{transcript_header}{youtube_transcript_text}"

            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(final_content_to_save)
                print(f"Successfully saved content from '{url}' (using {source_method}) to '{filepath}'")
                saved_count += 1
            except Exception as e:
                print(f"Error saving file {filepath}: {e}")
        elif result and isinstance(result, dict): # Result exists but has no content or transcript
             url = result.get("url", "Unknown URL")
             source_method = result.get("method", "Unknown")
             print(f"Scraping failed or yielded no content for '{url}' (method: {source_method}).")
        elif result is None:
             # This happens if a sync method failed or an async task failed fundamentally
             # We don't know the URL here easily unless we restructure result storage
             print("Processing a failed task/result (URL unknown at this stage).") 
        else:
             print(f"Processing an unexpected result type: {type(result)}")


    print(f"\nScraping complete. Saved {saved_count} files to '{output_folder}'.")

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
    results_subfolder_name = "scraped_content" # Define a fixed name for the subfolder
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
        # --- Determine Unique Run Folder Path ---
        base_run_folder_name = slugify(search_query)
        parent_output_dir = "outputs" # Main directory for all runs
        base_run_folder_path = os.path.join(parent_output_dir, base_run_folder_name)

        unique_run_folder_path = base_run_folder_path
        counter = 1
        while os.path.exists(unique_run_folder_path) and os.path.isdir(unique_run_folder_path):
             print(f"[Main] Base folder '{unique_run_folder_path}' already exists. Generating a new name.")
             unique_run_folder_path = f"{base_run_folder_path}_{counter}"
             counter += 1
        if unique_run_folder_path != base_run_folder_path:
            print(f"[Main] Using unique run folder: '{unique_run_folder_path}'")
        else:
            print(f"[Main] Using base folder: '{unique_run_folder_path}'")

        # Define the final path for scraped content within the unique run folder
        output_path_for_scraping = os.path.join(unique_run_folder_path, results_subfolder_name)
        # --- End Determine Unique Run Folder Path ---

        print(f"\nStarting scraping process, saving content to '{output_path_for_scraping}'...")
        scrape_urls_to_markdown(
             items_for_scraping, 
             output_path_for_scraping, # Pass the final, unique path including the subfolder
             jina_api_key=jina_key, 
             delay=request_delay,
             youtube_transcript_languages=youtube_transcript_preferred_languages
        )
    else:
         print("No items to scrape. Either search failed or no example items were defined.") 