import os
from brave import Brave
from typing import List, Dict, Optional
from dotenv import load_dotenv

def get_brave_search_results(query: str, api_key: str, count: int = 10) -> List[Dict[str, str]]:
    """
    Retrieves top web search results from Brave Search API.

    Args:
        query: The search term.
        api_key: Your Brave Search API key.
        count: The maximum number of results to return (default 10).

    Returns:
        A list of dictionaries, where each dictionary contains
        the 'title' and 'url' of a search result. Returns an empty
        list if an error occurs or no results are found.
    """
    results_list = []
    try:
        # Initialize the Brave client with the API key
        brave = Brave(api_key=api_key)

        # Perform the search, requesting only web results
        # The 'search' method defaults to the 'web' endpoint
        search_results = brave.search(q=query, count=count, result_filter="web")

        # Access results using attributes of the WebSearchApiResponse object
        if hasattr(search_results, 'web') and search_results.web and hasattr(search_results.web, 'results') and search_results.web.results:
            web_results_list = search_results.web.results
            # Limit to the requested count, as the API might return more internally
            for result in web_results_list[:count]:
                # Access attributes of the result object (likely also a custom type)
                if hasattr(result, 'title') and hasattr(result, 'url'):
                    results_list.append({
                        'title': result.title,
                        'url': str(result.url) # Ensure URL is a string
                    })
        else:
            # This path should only be hit if the API response structure is missing 'web' or 'web.results'
            print(f"Web results attribute not found or empty in API response for query: {query}")

    except Exception as e:
        print(f"An error occurred during Brave Search API call: {e}")
        # Log the type of exception as well for more detail
        print(f"Exception Type: {type(e).__name__}")
        # Consider more specific error handling based on potential exceptions
        # from the 'brave-search' library or network issues.

    return results_list

# --- Example Usage ---
if __name__ == "__main__":
    # It's recommended to load the API key from environment variables
    # or a secure configuration method.
    load_dotenv()

    brave_api_key = os.environ.get("BRAVE_API_KEY", "YOUR_BRAVE_API_KEY") # Replace with your key if not using env var

    if brave_api_key == "YOUR_BRAVE_API_KEY":
        print("Warning: Please set your BRAVE_API_KEY environment variable or replace 'YOUR_BRAVE_API_KEY' in the script.")
    else:
        search_query = "best python web frameworks"
        top_results = get_brave_search_results(search_query, brave_api_key, count=5) # Get top 5 results

        if top_results:
            print(f"Top {len(top_results)} Brave search results for '{search_query}':")
            for i, result in enumerate(top_results, 1):
                print(f"{i}. Title: {result.get('title')}") # Use .get for safety
                print(f"   URL: {result.get('url')}")
        else:
            # Keep this message generic as failure could be API error or no results found
            print(f"Could not retrieve results for '{search_query}'.") 