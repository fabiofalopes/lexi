# Lexi Owl: Agentic Web Research Pipeline

Lexi Owl is an open-source, agentic research workflow for technical and scientific web research. It combines web search, multi-method web scraping (including open-source LLM-friendly scrapers), and LLM synthesis to produce exhaustive, reference-rich answers with full traceability.

## Features

- **Agentic multi-step workflow:** Iteratively searches, scrapes, and synthesizes answers for maximal coverage.
- **Flexible scraping:** Supports Jina Reader API, open-source [llm-reader](https://github.com/m92vyas/llm-reader), and BeautifulSoup fallback.
- **YouTube support:** Extracts transcripts from YouTube links.
- **LLM synthesis:** Uses Groq API (LlamaIndex) for answer generation and synthesis.
- **Reference-rich output:** All answers are verbose, reference-heavy, and saved for audit.
- **Organized outputs:** Each run creates a dedicated folder with all scraped content and answers.

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
- The project uses [llm-reader](https://github.com/m92vyas/llm-reader) (async, headless browser-based).  
- You may need to install Playwright browsers for llm-reader:
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
- For each query, it will:
  - Search using Brave Search API.
  - Scrape the top results using llm-reader (or Jina Reader/fallback).
  - Aggregate and synthesize answers using the Groq LLM.
- All outputs are saved in a dedicated folder under `outputs/`, named after your research question.

### Output Structure

Each run creates a folder in `outputs/`:

```
outputs/
  your_query_slug/
    final_answer.md                # Synthesized, reference-rich answer
    all_iteration_answers.md       # All per-step answers, search prompts, and URLs
    scraped_content/
      *.md                        # LLM-friendly Markdown files for each scraped source
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

- **llm-reader (default):** Open-source, async, headless browser-based, LLM-friendly Markdown output.
- **Jina Reader:** Free (20 RPM) or with API key (500 RPM), Markdown output.
- **Fallback:** BeautifulSoup HTML-to-text for simple pages.

You can control the scraping method in `scraper.py` via the `method` parameter (`'auto'`, `'llm-reader'`, `'jina'`, `'fallback'`).

## Customization

- **Change the research question:** Edit the `user_question` variable in `agent.py`.
- **Number of iterations/searches:** Adjust `NUM_ITERATIONS` in `agent.py`.
- **LLM model:** Change the `model_name` in `agent.py` (see available Groq models printed at startup).
- **Add new scraping methods:** Extend `scraper.py` with new scrapers as needed.

## Troubleshooting

- **llm-reader not working?**
  - Ensure you installed it from GitHub:  
    `pip install git+https://github.com/m92vyas/llm-reader.git`
  - Install Playwright and browsers:  
    `pip install playwright && playwright install`
- **Jina Reader 402/429 errors?**
  - You are rate-limited. Use an API key or throttle requests.
- **YouTube transcript errors?**
  - Ensure `youtube_transcript_api` is installed and `youtube_transcriber.py` is present.

## References

- [llm-reader](https://github.com/m92vyas/llm-reader)
- [Jina Reader API](https://jina.ai/reader/)
- [LlamaIndex](https://github.com/jerryjliu/llama_index)
- [Brave Search API](https://brave.com/search/api/)

## Scrapers to consider
- [Scrapegraph-ai](https://github.com/ScrapeGraphAI/Scrapegraph-ai)
- [scrape2md](https://github.com/tarasglek/scrape2md)