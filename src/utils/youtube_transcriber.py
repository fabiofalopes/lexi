import os
import re
from typing import List, Optional, Dict

# Attempt to import the YouTubeTranscriptApi. If not found, print an error and exit.
try:
    from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled, VideoUnavailable
    from youtube_transcript_api.formatters import TextFormatter
except ImportError:
    print("ERROR: The 'youtube-transcript-api' library is not installed.")
    print("Please install it by running: pip install youtube-transcript-api")
    exit(1)

# --- Helper Function for Filename Generation (similar to scraper.py) ---
def slugify_yt(text: str, max_length: int = 200) -> str:
    """
    Converts a string into a "slug" suitable for use as a filename.
    Lowercase, spaces to underscores, removes most special characters.
    For YouTube IDs or titles.
    """
    if not text:
        return "untitled_video"
    s = re.sub(r'[^\w\s-]', '', text).strip().lower() # Remove non-alphanumeric, non-space, non-hyphen
    s = re.sub(r'[-\s]+', '_', s) # Replace spaces and hyphens with underscore
    s = s.strip('_') # Remove leading/trailing underscores
    s = s[:max_length] # Truncate
    if not s: # If slugging resulted in empty string
        return "untitled_video"
    return s

def extract_video_id(url: str) -> Optional[str]:
    """
    Extracts the YouTube video ID from a URL.
    Supports standard, shortened, and embed URLs.
    More robust regex to ensure it only matches actual YouTube URLs.
    """
    # Patterns to identify YouTube URLs and capture the 11-character video ID.
    # Order can matter if there were overlaps, but these are fairly distinct.
    regex_patterns = [
        r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/(?:watch\?v=|embed\/|v\/|shorts\/|live\/|playlist\?list=[^#&?]*watch\?v=|attribution_link\?a=[^#&?]*u=\%2Fwatch\%3Fv\%3D)([^#&?]{11})", # Standard, embed, shorts, live, playlist links with v=
        r"(?:https?:\/\/)?(?:www\.)?youtu\.be\/([^#&?]{11})", # Shortened youtu.be links
        r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/oembed\?format=json&url=https?:\/\/www\.youtube\.com\/watch\?v=([^#&?]{11})" # oEmbed links
    ]

    for pattern in regex_patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1) # The captured group is the video ID
        
    # print(f"Debug: No YouTube video ID extracted from URL: {url}") # Optional: for debugging non-matches
    return None

def get_youtube_transcript(video_id: str, languages: Optional[List[str]] = None) -> Optional[str]:
    """
    Fetches the transcript for a given YouTube video ID.

    Args:
        video_id: The ID of the YouTube video.
        languages: A list of preferred language codes (e.g., ['en', 'es']).
                   Defaults to trying English first.

    Returns:
        A string containing the formatted transcript, or None if an error occurs.
    """
    if languages is None:
        languages = ['en'] # Default to English if no languages are specified

    try:
        print(f"Fetching transcript for video ID: {video_id} (Languages: {languages})")
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Try to find a transcript in the preferred languages
        # This will raise NoTranscriptFound if none of the preferred languages are available.
        transcript_data_obj = transcript_list.find_transcript(languages)
        
        fetched_transcript_segments = transcript_data_obj.fetch()
        
        formatter = TextFormatter()
        formatted_text = formatter.format_transcript(fetched_transcript_segments)
        
        print(f"Successfully fetched and formatted transcript for {video_id}. Language: {transcript_data_obj.language_code}")
        return formatted_text
    except NoTranscriptFound:
        print(f"No transcript found for video ID '{video_id}' in preferred languages: {languages}. Attempting to list available... ")
        try:
            # If preferred languages failed, list what is available
            available_transcripts_list = YouTubeTranscriptApi.list_transcripts(video_id)
            available_codes = sorted(list(set(t.language_code for t in available_transcripts_list)))
            if available_codes:
                print(f"Available transcript language codes for '{video_id}': {available_codes}")
                print(f"Tip: Try running again with one of these, e.g., --languages {available_codes[0]}")
            else:
                print(f"No transcripts at all seem to be available for video ID '{video_id}'.")
        except Exception as e_list:
            print(f"Could not list available transcripts for '{video_id}' after NoTranscriptFound: {e_list}")
    except TranscriptsDisabled:
        print(f"Transcripts are disabled for video ID '{video_id}'.")
    except VideoUnavailable:
        print(f"Video '{video_id}' is unavailable or private.")
    except Exception as e:
        print(f"An unexpected error occurred while fetching transcript for video ID '{video_id}': {e}")
        print(f"Exception type: {type(e).__name__}")
    return None

def save_transcript_to_file(video_id: str, transcript_content: str, output_folder: str, filename_prefix: Optional[str] = None) -> Optional[str]:
    """
    Saves the transcript content to a text file.

    Args:
        video_id: The YouTube video ID (used for default filename if prefix is not given).
        transcript_content: The string content of the transcript.
        output_folder: The folder where the file will be saved.
        filename_prefix: Optional. A prefix for the filename (e.g., video title slug).
                         If None, video_id will be used.

    Returns:
        The full path to the saved file, or None if saving fails.
    """
    os.makedirs(output_folder, exist_ok=True)
    
    base_name = slugify_yt(filename_prefix if filename_prefix else video_id)
    filename = f"{base_name}_transcript.txt"
    filepath = os.path.join(output_folder, filename)
    
    # Handle potential filename collisions by appending a counter
    counter = 1
    temp_filepath = filepath
    while os.path.exists(temp_filepath):
        name_part, ext_part = os.path.splitext(filename)
        # Remove previous counter if exists to avoid base_name_1_2.txt
        name_part = re.sub(r'_\d+$', '', name_part) 
        temp_filepath = os.path.join(output_folder, f"{name_part}_{counter}{ext_part}")
        counter += 1
    filepath = temp_filepath

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(transcript_content)
        print(f"Transcript successfully saved to: {filepath}")
        return filepath
    except IOError as e:
        print(f"Error saving transcript to file {filepath}: {e}")
    return None

# --- Example Usage ---
if __name__ == "__main__":
    # Test URLs:
    # example_video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # English
    #example_video_url = "https://www.youtube.com/watch?v=Nsb7qocje-A" # User requested test URL
    # example_video_url = "https://www.youtube.com/watch?v=o_XVt5rdpFY" # Portuguese available
    # example_video_url = "https://youtu.be/rokGy0huYEA" # Shortened URL, English
    # example_video_url = "https://www.youtube.com/embed/LEd98A9334M" # Embed URL, English
    # example_video_url_no_transcript = "https://www.youtube.com/watch?v=AYmNUGdGabc" # Likely no manual transcript
    # example_video_url_private_or_deleted = "https://www.youtube.com/watch?v=xxxxxxxxxxx" # Non-existent
    
    example_video_url = "https://www.youtube.com/watch?v=V-TlS3SQUfU"

    output_directory = "youtube_transcripts"
    # To test different language preferences:
    # preferred_languages = ['en']
    preferred_languages = ['pt', 'en'] # Try Portuguese, then English
    # preferred_languages = ['ja'] # Try Japanese (for a video that has it)

    print(f"--- YouTube Transcript Fetcher Example ---")
    print(f"Processing URL: {example_video_url}")
    video_id_to_fetch = extract_video_id(example_video_url)

    if video_id_to_fetch:
        print(f"Extracted Video ID: {video_id_to_fetch}")
        transcript = get_youtube_transcript(video_id_to_fetch, languages=preferred_languages)
        
        if transcript:
            # In a real application, you might fetch the video title using another API (e.g., YouTube Data API)
            # or a library like pytube to use as a more descriptive filename_prefix.
            # For this example, we'll use the video_id.
            saved_file_path = save_transcript_to_file(
                video_id_to_fetch, 
                transcript, 
                output_directory,
                filename_prefix=slugify_yt(video_id_to_fetch) # Using video ID as prefix for simplicity
            )
            if saved_file_path:
                print(f"Process completed. Transcript at: {saved_file_path}")
            else:
                print("Failed to save the transcript.")
        else:
            print(f"Could not retrieve transcript for video ID: {video_id_to_fetch}. Check logs for details.")
    else:
        print(f"Could not extract video ID from URL: {example_video_url}")

    print(f"\n--- End of Example ---")
 