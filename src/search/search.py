import os
from dotenv import load_dotenv
from .brave_search import get_brave_search_results # Import from brave_search.py
from .arquivo import search_text as get_arquivo_text_search_results # Import from arquivo.py

# Function to wrap Arquivo.pt text search
def get_arquivo_search_results(query: str, max_items: int = 5):
    """
    Retrieves text search results from Arquivo.pt.

    Args:
        query: The search term.
        max_items: The maximum number of results to return (default 5).

    Returns:
        The JSON response from Arquivo.pt API or None if an error occurs.
    """
    print(f"[Arquivo.pt] Searching for: {query} (max_items={max_items})")
    results = get_arquivo_text_search_results(q=query, max_items=max_items)
    return results

# --- Example Usage ---
if __name__ == "__main__":
    # It's recommended to load the API key from environment variables
    # or a secure configuration method.
    load_dotenv()

    # --- Brave Search Example ---
    brave_api_key = os.environ.get("BRAVE_API_KEY", "YOUR_BRAVE_API_KEY")
    if brave_api_key == "YOUR_BRAVE_API_KEY":
        print("Warning: Please set your BRAVE_API_KEY environment variable or replace 'YOUR_BRAVE_API_KEY' in the script.")
    else:
        search_query_brave = "latest AI advancements"
        print(f"\n--- Running Brave Search for: '{search_query_brave}' ---")
        top_results_brave = get_brave_search_results(search_query_brave, brave_api_key, count=3)
        if top_results_brave:
            print(f"Top {len(top_results_brave)} Brave search results:")
            for i, result in enumerate(top_results_brave, 1):
                print(f"{i}. Title: {result.get('title')}")
                print(f"   URL: {result.get('url')}")
        else:
            print(f"Could not retrieve Brave results for '{search_query_brave}'.")

    # --- Arquivo.pt Search Example ---
    search_query_arquivo = "história de Portugal"
    print(f"\n--- Running Arquivo.pt Search for: '{search_query_arquivo}' ---")
    results_arquivo = get_arquivo_search_results(search_query_arquivo, max_items=3)
    if results_arquivo and results_arquivo.get("response_items"):
        print(f"Top {len(results_arquivo['response_items'])} Arquivo.pt search results:")
        for i, item in enumerate(results_arquivo["response_items"], 1):
            print(f"{i}. Title: {item.get('title')}")
            print(f"   Original URL: {item.get('originalURL')}")
            print(f"   Link to Archive: {item.get('linkToArchive')}")
    else:
        print(f"Could not retrieve Arquivo.pt results for '{search_query_arquivo}'.")

