import requests
from urllib.parse import quote

API_URL = "https://arquivo.pt/textsearch"


def search_text(q, from_date=None, to_date=None, type=None, offset=0, site_search=None, collection=None, max_items=50, dedup_value=None, dedup_field=None, fields=None, pretty_print=True):
    """
    Perform a full-text search on Arquivo.pt.
    Returns the parsed JSON response.
    """
    params = {
        "q": q,
        "offset": offset,
        "maxItems": max_items,
        "prettyPrint": str(pretty_print).lower(),
    }
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date
    if type:
        params["type"] = type
    if site_search:
        params["siteSearch"] = site_search
    if collection:
        params["collection"] = collection
    if dedup_value:
        params["dedupValue"] = dedup_value
    if dedup_field:
        params["dedupField"] = dedup_field
    if fields:
        params["fields"] = fields

    try:
        resp = requests.get(API_URL, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[Arquivo.pt] Error: {e}")
        return None


def search_url_versions(url, from_date=None, to_date=None, max_items=50, offset=0, pretty_print=True):
    """
    Search for all preserved versions of a given URL.
    Returns the parsed JSON response.
    """
    params = {
        "versionHistory": quote(url, safe=''),
        "maxItems": max_items,
        "offset": offset,
        "prettyPrint": str(pretty_print).lower(),
    }
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date

    try:
        resp = requests.get(API_URL, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[Arquivo.pt] Error: {e}")
        return None


def search_metadata(url_with_timestamp, pretty_print=True):
    """
    Search for metadata of a specific archived URL and timestamp.
    url_with_timestamp: e.g. 'http://www.expresso.pt//20000302151731'
    Returns the parsed JSON response.
    """
    params = {
        "metadata": quote(url_with_timestamp, safe=''),
        "prettyPrint": str(pretty_print).lower(),
    }
    try:
        resp = requests.get(API_URL, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[Arquivo.pt] Error: {e}")
        return None


def print_results(results):
    if not results:
        print("No results (None returned).")
        return
    if "response_items" not in results:
        print("No 'response_items' in response. Raw response:")
        print(results)
        return
    if not results["response_items"]:
        print("No response_items found.")
        return
    for item in results["response_items"]:
        print(f"- {item.get('title')} | {item.get('originalURL')} | {item.get('linkToArchive')}")


if __name__ == "__main__":
    print("Arquivo.pt API quick test\n")
    print("Text search for 'Albert Einstein':")
    res = search_text("Albert Einstein", max_items=3)
    print_results(res)
    print("\nURL version history for 'expresso.pt':")
    res2 = search_url_versions("expresso.pt", max_items=3)
    print_results(res2)
    print("\nMetadata search for 'http://www.expresso.pt//20000302151731':")
    

    # Search metadata from the first result in res2, if available
    if res2 and "response_items" in res2 and res2["response_items"]:
        first_item = res2["response_items"][0]
        url = first_item.get("originalURL")
        tstamp = first_item.get("tstamp")
        if url and tstamp:
            url_with_timestamp = f"{url}//{tstamp}"
            print(f"\nMetadata search for first result in res2: {url_with_timestamp}")
            res_meta = search_metadata(url_with_timestamp)
            print_results(res_meta)
        else:
            print("\nCould not extract url and tstamp from first res2 item.")
    else:
        print("\nNo response_items in res2 to search metadata.") 