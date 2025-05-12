# Lexi Owl: Agentic Web Research Pipeline

Lexi Owl is an open-source, agentic research workflow for technical and scientific web research. It combines web search, multi-method web scraping (including open-source LLM-friendly scrapers), and LLM synthesis to produce exhaustive, reference-rich answers with full traceability.

## Features

- **Agentic multi-step workflow:** Iteratively searches, scrapes, and synthesizes answers for maximal coverage.
- **Flexible & Robust scraping:** 
    - Uses `trafilatura` for main content extraction.
    - Falls back to `readability-lxml` if `trafilatura` fails.
    - Leverages `llm-reader`'s `get_page_source` for JavaScript-rendered pages.
    - Supports Jina Reader API and basic BeautifulSoup fallback.
- **YouTube support:** Extracts transcripts from YouTube links.
- **LLM synthesis:** Uses Groq API (LlamaIndex) for answer generation and synthesis.
- **Reference-rich output:** All answers are verbose, reference-heavy, and saved for audit.
- **Organized & Informative outputs:** 
    - Each run creates a dedicated, uniquely named folder (e.g., `outputs/your_query_slug_1`).
    - Scraped files include a header with URL, timestamp, and extraction method.

## Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd lexi_owl
```

### 2. Install Python dependencies

It is recommended to use a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install all dependencies:

```bash
pip install -r requirements.txt
```

**Note:**  
- The `requirements.txt` file includes necessary libraries like `trafilatura`, `readability-lxml`, `beautifulsoup4`, `youtube-transcript-api`, and libraries for `llm-reader`'s page fetching.
- You may need to install Playwright browsers for the page fetching part used by the `llm-reader` method:
  ```bash
  pip install playwright
  playwright install
  ```

### 3. Environment Variables

Create a `.env` file in the project root with your API keys:

```env
GROQ_API_KEY=your_groq_api_key
BRAVE_API_KEY=your_brave_search_api_key
JINA_API_KEY=your_jina_api_key  # Optional, for higher Jina Reader rate limits
```

## Usage

### Main Agentic Workflow

Run the main agent:

```bash
python agent.py
```

- The script will prompt the LLM to generate diverse search queries for your research question.
- It will determine a unique output folder name for the run (e.g., `outputs/your_query_slug_1`).
- For each query, it will:
  - Search using Brave Search API.
  - Scrape the top results using the configured method (defaulting to the Trafilatura/Readability combo via `llm-reader` mode).
  - Aggregate and synthesize answers using the Groq LLM.
- All outputs are saved in the dedicated run folder under `outputs/`.

### Output Structure

Each run creates a uniquely named folder in `outputs/`:

```
outputs/
  your_query_slug_N/             # N increments if the base slug exists
    final_answer.md                # Synthesized, reference-rich answer
    all_iteration_answers.md       # All per-step answers, search prompts, and URLs
    scraped_content/
      *.md                        # LLM-friendly Markdown file for each scraped source
                                  # Includes header: Title, URL, Scraped Timestamp, Method
```

### Example

After running, you might see:

```
outputs/beekeeping_lora_open_source_monitoring_solar_sensors_audio/
  final_answer.md
  all_iteration_answers.md
  scraped_content/
    the_beehive_topic_use_cases_the_things_network.md
    ...
```

## Scraping Methods

- **llm-reader (default):** 
    - Uses `url_to_llm_text.get_page_source` (async, headless browser) to fetch HTML.
    - Extracts main content using `trafilatura`.
    - Falls back to `readability-lxml` if `trafilatura` yields minimal content.
    - Recommended for complex, JavaScript-heavy pages.
- **Jina Reader:** Free (20 RPM) or with API key (500 RPM), Markdown output. Simple API call.
- **Fallback:** Basic `requests` + `BeautifulSoup` HTML-to-text for simple static pages.

You can control the scraping method in `agent.py` via the `method` parameter passed to `scrape_urls_to_markdown` (currently hardcoded to `llm-reader` in the main block, but could be changed).

## Customization

- **Change the research question:** Edit the `user_question` variable in `agent.py`.
- **Number of iterations/searches:** Adjust `NUM_ITERATIONS` in `agent.py`.
- **LLM model:** Change the `model_name` in `agent.py` (see available Groq models printed at startup).
- **Add new scraping methods:** Extend `scraper.py` with new scrapers as needed.

## Troubleshooting

- **`get_page_source` not working or other `llm-reader` related issues?**
  - Ensure you installed its dependencies (Playwright):  
    `pip install playwright && playwright install`
  - Check if `url_to_llm_text` is correctly installed (implicitly via requirements or manually if needed: `pip install git+https://github.com/m92vyas/llm-reader.git`)
- **`trafilatura` or `readability` errors?**
  - Ensure they are installed via `pip install -r requirements.txt`.
- **Jina Reader 402/429 errors?**
  - You are rate-limited. Use an API key or throttle requests.
- **YouTube transcript errors?**
  - Ensure `youtube_transcript_api` is installed and `youtube_transcriber.py` is present.

## References

- [Trafilatura](https://trafilatura.readthedocs.io/)
- [Readability-lxml](https://github.com/buriy/python-readability)
- [llm-reader (for get_page_source)](https://github.com/m92vyas/llm-reader)
- [Jina Reader API](https://jina.ai/reader/)
- [LlamaIndex](https://github.com/jerryjliu/llama_index)
- [Brave Search API](https://brave.com/search/api/)

## Scrapers to consider
- [Scrapegraph-ai](https://github.com/ScrapeGraphAI/Scrapegraph-ai)
- [scrape2md](https://github.com/tarasglek/scrape2md)