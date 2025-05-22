"""
agent.py
Agentic workflow orchestration. All LLM logic is now in llm.py.
"""
from llama_index.core.llms import ChatMessage
from typing import List, Optional, Dict
import os
from dotenv import load_dotenv
load_dotenv()

# Import search and scraping utilities
from search import get_brave_search_results
from scraper import scrape_urls_to_markdown, slugify

# Import prompts and constants
from prompts import (
    AGENTIC_SYSTEM_PROMPT,
    FINAL_SYNTHESIS_SYSTEM_PROMPT,
    SYSTEM_PROMPT_SLUG,
    SEARCH_QUERY_DIVERSIFICATION_SYSTEM_PROMPT,
    build_iteration_user_prompt,
    build_final_synthesis_prompt,
    build_search_query_generation_prompt,
)
from constants import (
    FINAL_ANSWER_FILENAME,
    ALL_ITERATION_ANSWERS_FILENAME,
    SCRAPED_CONTENT_DIR,
    PARENT_OUTPUT_DIR,
    DEFAULT_SCRAPE_OUTPUT_FOLDER,
    LEGACY_RESULT_PREFIX,
)
from output_utils import save_run_outputs
from config import AgentConfig
from llm import simple_agentic_prompt, GROQ_MODELS

# List of available Groq models (as of May 2025)
GROQ_MODELS: Dict[str, str] = {
    "llama-3.3-70b-versatile": "Meta Llama 3.3 70B Versatile",
    "llama-3.1-8b-instant": "Meta Llama 3.1 8B Instant",
    "llama-guard-3-8b": "Meta Llama Guard 3 8B (moderation)",
    "llama3-70b-8192": "Meta Llama 3 70B 8K",
    "llama3-8b-8192": "Meta Llama 3 8B 8K",
    "gemma2-9b-it": "Google Gemma 2 9B IT",
    "deepseek-r1-distill-llama-70b": "DeepSeek R1 Distill Llama 70B",
    "meta-llama/llama-4-maverick-17b-128e-instruct": "Meta Llama 4 Maverick 17B",
    "meta-llama/llama-4-scout-17b-16e-instruct": "Meta Llama 4 Scout 17B",
    # Add more as needed
}

# --- New: Search, Scrape, and Answer Agent Function ---
def search_scrape_and_answer(
    query: str,
    num_search_results_per_iteration: int = 3,
    model_name: str = "llama-3.3-70b-versatile",
    temperature: float = 0.2,
    system_prompt: Optional[str] = AGENTIC_SYSTEM_PROMPT,
    scrape_output_folder: str = DEFAULT_SCRAPE_OUTPUT_FOLDER,
    jina_api_key: Optional[str] = None,
    youtube_transcript_languages: Optional[List[str]] = None,
    delay: float = 1.0
) -> str:
    """
    Agent function: search, scrape, and answer a query using Groq LLM.
    Returns the LLM's answer and the sources used.
    """
    # 1. Search
    print(f"Searching for: {query}")
    search_results = get_brave_search_results(query, api_key=os.environ.get("BRAVE_API_KEY"), count=num_search_results_per_iteration)
    if not search_results:
        return "No search results found."

    # 2. Scrape
    print(f"Scraping top {len(search_results)} results...")
    # Scrape and save to temp folder (but we'll also aggregate content in memory)
    os.makedirs(scrape_output_folder, exist_ok=True)
    scrape_urls_to_markdown(
        search_results,
        scrape_output_folder,
        jina_api_key=jina_api_key,
        delay=delay,
        youtube_transcript_languages=youtube_transcript_languages or ['en']
    )
    # Read scraped content
    aggregated_content = []
    for i, item in enumerate(search_results, 1):
        title = item.get('title', f'{LEGACY_RESULT_PREFIX}{i}')
        filepath = get_scraped_content_filepath(scrape_output_folder, title, i, slugify)
        if not os.path.exists(filepath):
            continue
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        aggregated_content.append(f"# {title}\n\n{content}\n")
    if not aggregated_content:
        return "No content could be scraped from the search results."
    sources_text = "\n\n---\n\n".join(aggregated_content)

    # 3. Build prompt
    prompt = (
        f"Using the following sources, answer the question: {query}\n\n"
        f"SOURCES:\n\n{sources_text}\n"
        "\nCite the sources you use in your answer."
    )
    # 4. Call LLM
    print("Calling LLM with aggregated web content...")
    answer = simple_agentic_prompt(
        user_prompt=prompt,
        model_name=model_name,
        temperature=temperature,
        system_prompt=system_prompt
    )
    return answer

def generate_query_slug(user_question: str, model_name: str = "llama-3.3-70b-versatile", temperature: float = 0.0) -> str:
    """
    Use the LLM to generate a rigid, consistent slug/folder name for the user query,
    AND ensures the final path within 'outputs' is unique.
    Returns the unique path (e.g., outputs/my_query_slug_1).
    """
    parent_output_dir = PARENT_OUTPUT_DIR # Main directory for all runs
    os.makedirs(parent_output_dir, exist_ok=True)

    system_prompt_slug = SYSTEM_PROMPT_SLUG
    base_slug = simple_agentic_prompt(
        user_prompt=f"User question: {user_question}",
        model_name=model_name,
        temperature=temperature,
        system_prompt=system_prompt_slug
    ).strip().replace("/", "_")

    # Fallback and cleanup for base slug
    import re
    base_slug = re.sub(r'[^a-z0-9_]', '', base_slug.lower().replace(' ', '_'))
    base_slug = re.sub(r'_+', '_', base_slug).strip('_') # Remove multiple underscores
    base_slug = base_slug[:60]
    if not base_slug:
        base_slug = "research_query"
    
    # Construct the base path within the parent directory
    base_folder_path = os.path.join(parent_output_dir, base_slug)

    # --- Ensure Unique Folder Path ---
    unique_folder_path = base_folder_path
    counter = 1
    while os.path.exists(unique_folder_path) and os.path.isdir(unique_folder_path):
        print(f"[AgentSetup] Base folder '{unique_folder_path}' already exists. Generating a new name.")
        unique_folder_path = f"{base_folder_path}_{counter}"
        counter += 1
    # --- End Ensure Unique Folder Path ---

    if unique_folder_path != base_folder_path:
        print(f"[AgentSetup] Using unique run folder: '{unique_folder_path}'")
    else:
        print(f"[AgentSetup] Using base run folder: '{unique_folder_path}'")

    # Return the final unique path
    return unique_folder_path

# --- Multi-Iteration Agentic Workflow ---
def execute_single_iteration(
    query: str,
    already_scraped_urls: set,
    scraped_content_subfolder: str,
    model_name: str,
    temperature: float,
    system_prompt: str,
    num_search_results: int,
    jina_api_key: str = None,
    youtube_transcript_languages: list = None,
    delay: float = 1.0
):
    """
    Executes a single search/scrape/answer iteration.
    Returns: (answer, urls_this_iter, warnings)
    """
    warnings = []
    # 1. Search
    search_results = get_brave_search_results(query, api_key=os.environ.get("BRAVE_API_KEY"), count=num_search_results)
    if not search_results:
        return "No search results found.", [], ["No search results found."]
    # 2. Filter already scraped URLs
    filtered_search_results = [item for item in search_results if item.get('url') and item.get('url') not in already_scraped_urls]
    urls_this_iter = [item.get('url') for item in filtered_search_results if item.get('url')]
    if not filtered_search_results:
        return "No new search results to scrape.", urls_this_iter, ["All search results already scraped."]
    # 3. Scrape
    scrape_urls_to_markdown(
        filtered_search_results,
        scraped_content_subfolder,
        jina_api_key=jina_api_key,
        delay=delay,
        youtube_transcript_languages=youtube_transcript_languages or ['en']
    )
    # 4. Aggregate content
    aggregated_content = []
    for item_idx, item in enumerate(filtered_search_results, 1):
        title = item.get('title', f'{LEGACY_RESULT_PREFIX}{item_idx}')
        filepath = get_scraped_content_filepath(scraped_content_subfolder, title, item_idx, slugify)
        if filepath and os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                aggregated_content.append(f"## Source: {title}\nURL: <{item.get('url')}>\n\n{content}\n")
            except Exception as e:
                warnings.append(f"Error reading file {filepath}: {e}")
        else:
            warnings.append(f"Scraped file for '{title}' not found at expected paths.")
    if not aggregated_content:
        return "No content could be scraped from the search results.", urls_this_iter, warnings
    sources_text = "\n\n---\n\n".join(aggregated_content)
    user_prompt = build_iteration_user_prompt(query, sources_text)
    answer = simple_agentic_prompt(
        user_prompt=user_prompt,
        model_name=model_name,
        temperature=temperature,
        system_prompt=system_prompt
    )
    return answer, urls_this_iter, warnings

def multi_agentic_search_scrape_answer(
    user_question: str,
    config: AgentConfig
) -> str:
    """
    Runs the full multi-agent workflow: generate queries, search, scrape, answer per iteration, synthesize.
    Ensures a unique output folder for each run.
    """
    unique_run_folder = generate_query_slug(user_question, model_name=config.model_name)
    scraped_content_subfolder = os.path.join(unique_run_folder, "scraped_content")
    already_scraped_urls = set()
    print("\nGenerating unique, diverse search queries with the LLM...")
    search_query_generation_prompt = build_search_query_generation_prompt(user_question, config.num_iterations)
    queries_text = simple_agentic_prompt(
        user_prompt=search_query_generation_prompt,
        model_name=config.model_name,
        temperature=config.temperature,
        system_prompt=SEARCH_QUERY_DIVERSIFICATION_SYSTEM_PROMPT
    )
    queries = [q.strip('"').strip() for q in queries_text.splitlines() if q.strip()]
    if len(queries) < config.num_iterations:
        print(f"Warning: Only {len(queries)} unique queries generated, expected {config.num_iterations}.")
        queries += [user_question] * (config.num_iterations - len(queries))
    print("\nGenerated search queries:")
    for i, q in enumerate(queries[:config.num_iterations], 1):
        print(f"{i}. {q}")
    answers = []
    search_prompts = []
    all_search_urls = []
    for i in range(config.num_iterations):
        print(f"\n--- Iteration {i+1} ---")
        query = queries[i]
        answer, urls_this_iter, warnings = execute_single_iteration(
            query=query,
            already_scraped_urls=already_scraped_urls,
            scraped_content_subfolder=scraped_content_subfolder,
            model_name=config.model_name,
            temperature=config.temperature,
            system_prompt=AGENTIC_SYSTEM_PROMPT,
            num_search_results=config.num_search_results_per_iteration,
            jina_api_key=config.jina_api_key,
            youtube_transcript_languages=config.youtube_transcript_languages,
            delay=config.delay
        )
        answers.append(answer)
        search_prompts.append(query)
        all_search_urls.append(urls_this_iter)
        already_scraped_urls.update(urls_this_iter)
        print(f"\nAgentic answer for iteration {i+1} (truncated):\n{answer[:500]}\n{'...' if len(answer) > 500 else ''}")
        if warnings:
            print("\nWarnings for iteration:")
            for warning in warnings:
                print(f"- {warning}")
    print("\n--- Boiling down all answers into a final comprehensive answer ---")
    boil_down_prompt = build_final_synthesis_prompt(user_question, answers)
    final_answer = simple_agentic_prompt(
        user_prompt=boil_down_prompt,
        model_name=config.model_name,
        temperature=config.temperature,
        system_prompt=FINAL_SYNTHESIS_SYSTEM_PROMPT
    )
    print("\nFINAL SYNTHESIZED ANSWER:\n")
    print(final_answer)
    iteration_data = [{'search_prompt': prompt, 'answer': answer, 'urls': urls} for prompt, answer, urls in zip(search_prompts, answers, all_search_urls)]
    model_config = {'model_name': config.model_name, 'temperature': config.temperature}
    save_run_outputs(unique_run_folder, user_question, final_answer, iteration_data, model_config)
    return final_answer

def run_search_and_synthesize_workflow(
    config: AgentConfig
):
    """
    Orchestrates the multi-agentic search, scrape, and synthesis workflow.
    """
    user_question = config.output_dir if config.output_dir else "User question not provided"
    if config.youtube_transcript_languages is None:
        config.youtube_transcript_languages = ['en', 'pt']
    if config.output_dir is None:
        output_dir = generate_query_slug(user_question, model_name=config.model_name, temperature=0.0)
    else:
        output_dir = config.output_dir
    scrape_output_folder = os.path.join(output_dir, "scraped_content")
    os.makedirs(output_dir, exist_ok=True)
    answers = []
    search_prompts = []
    all_search_urls = []
    print("\nGenerating unique, diverse search queries with the LLM...")
    search_query_generation_prompt = build_search_query_generation_prompt(user_question, config.num_iterations)
    queries_text = simple_agentic_prompt(
        user_prompt=search_query_generation_prompt,
        model_name=config.model_name,
        temperature=config.temperature,
        system_prompt=SEARCH_QUERY_DIVERSIFICATION_SYSTEM_PROMPT
    )
    queries = [q.strip('"').strip() for q in queries_text.splitlines() if q.strip()]
    if len(queries) < config.num_iterations:
        print(f"Warning: Only {len(queries)} unique queries generated, expected {config.num_iterations}.")
        queries += [user_question] * (config.num_iterations - len(queries))
    print("\nGenerated search queries:")
    for i, q in enumerate(queries[:config.num_iterations], 1):
        print(f"{i}. {q}")
    for i in range(config.num_iterations):
        print(f"\n--- Iteration {i+1} ---")
        search_prompt = queries[i]
        answer, urls_this_iter, warnings = execute_single_iteration(
            query=search_prompt,
            already_scraped_urls=set(),
            scraped_content_subfolder=scrape_output_folder,
            model_name=config.model_name,
            temperature=config.temperature,
            system_prompt=AGENTIC_SYSTEM_PROMPT,
            num_search_results=config.num_search_results_per_iteration,
            jina_api_key=config.jina_api_key,
            youtube_transcript_languages=config.youtube_transcript_languages,
            delay=config.delay
        )
        answers.append(answer)
        search_prompts.append(search_prompt)
        all_search_urls.append(urls_this_iter)
        print(f"\nAgentic answer for iteration {i+1} (truncated):\n{answer[:500]}\n{'...' if len(answer) > 500 else ''}")
        if warnings:
            print("\nWarnings for iteration:")
            for warning in warnings:
                print(f"- {warning}")
    print("\n--- Boiling down all answers into a final comprehensive answer ---")
    boil_down_prompt = build_final_synthesis_prompt(user_question, answers)
    final_answer = simple_agentic_prompt(
        user_prompt=boil_down_prompt,
        model_name=config.model_name,
        temperature=config.temperature,
        system_prompt=FINAL_SYNTHESIS_SYSTEM_PROMPT
    )
    print("\nFINAL SYNTHESIZED ANSWER:\n")
    print(final_answer)
    iteration_data = [{'search_prompt': prompt, 'answer': answer, 'urls': urls} for prompt, answer, urls in zip(search_prompts, answers, all_search_urls)]
    model_config = {'model_name': config.model_name, 'temperature': config.temperature}
    save_run_outputs(output_dir, user_question, final_answer, iteration_data, model_config)
    return final_answer

def get_scraped_content_filepath(base_dir: str, title: str, item_index: int, slugify_func) -> str:
    """
    Returns the filepath for a scraped content file, ensuring uniqueness and handling legacy fallback names.
    """
    import os
    slug = slugify_func(title)
    # Try base slug
    filename = f"{slug}.md"
    filepath = os.path.join(base_dir, filename)
    if os.path.exists(filepath):
        # Try numbered versions for uniqueness
        counter = 1
        while True:
            filename = f"{slug}_{counter}.md"
            filepath = os.path.join(base_dir, filename)
            if not os.path.exists(filepath):
                break
            counter += 1
    # If file still doesn't exist, try legacy fallback
    if not os.path.exists(filepath):
        legacy_filename = f"{LEGACY_RESULT_PREFIX}{item_index}.md"
        legacy_filepath = os.path.join(base_dir, legacy_filename)
        if os.path.exists(legacy_filepath):
            return legacy_filepath
    return filepath

# --- Example usage ---
if __name__ == "__main__":
    print("Testing agent.py workflow function...")
    test_query = "What are the latest advancements in AI?"
    test_model = "meta-llama/llama-4-maverick-17b-128e-instruct"
    test_temperature = 0.3
    test_num_iterations = 3
    test_search_results_per_iter = 3
    test_output_dir = "test_agent_output"
    test_jina_api_key = os.environ.get("JINA_API_KEY")
    test_youtube_transcript_languages = ['en', 'pt']
    test_delay = 1.0
    config = AgentConfig(
        model_name=test_model,
        temperature=test_temperature,
        num_iterations=test_num_iterations,
        num_search_results_per_iteration=test_search_results_per_iter,
        output_dir=test_output_dir,
        jina_api_key=test_jina_api_key,
        youtube_transcript_languages=test_youtube_transcript_languages,
        delay=test_delay
    )
    run_search_and_synthesize_workflow(config=config)
    print("agent.py test complete.")