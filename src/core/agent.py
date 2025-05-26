"""
agent.py
Agentic workflow orchestration with clean public API and core building blocks.
"""
from typing import List, Optional, Dict
import os
from dotenv import load_dotenv
load_dotenv()

# Import from our new modular structure
from ..search.search import get_brave_search_results
from ..utils.scraper import scrape_urls_to_markdown, slugify
from ..utils.output_utils import save_run_outputs
from ..llm.providers import simple_agentic_prompt
from .config import AgentConfig
from .prompts import (
    AGENTIC_SYSTEM_PROMPT,
    FINAL_SYNTHESIS_SYSTEM_PROMPT,
    SYSTEM_PROMPT_SLUG,
    SEARCH_QUERY_DIVERSIFICATION_SYSTEM_PROMPT,
    build_iteration_user_prompt,
    build_final_synthesis_prompt,
    build_search_query_generation_prompt,
)
from .constants import (
    FINAL_ANSWER_FILENAME,
    ALL_ITERATION_ANSWERS_FILENAME,
    SCRAPED_CONTENT_DIR,
    PARENT_OUTPUT_DIR,
    DEFAULT_SCRAPE_OUTPUT_FOLDER,
    LEGACY_RESULT_PREFIX,
)

# =============================================================================
# CORE WORKFLOW BLOCKS (Internal Functions)
# =============================================================================

def _generate_search_queries(user_question: str, config: AgentConfig) -> List[str]:
    """
    Generate diverse search queries for the user question.
    """
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
    
    return queries[:config.num_iterations]

def _search_step(query: str, config: AgentConfig) -> List[Dict]:
    """
    Execute search for a single query.
    """
    search_results = get_brave_search_results(
        query, 
        api_key=os.environ.get("BRAVE_API_KEY"), 
        count=config.num_search_results_per_iteration
    )
    return search_results or []

def _scrape_step(search_results: List[Dict], already_scraped_urls: set, scraped_content_subfolder: str, config: AgentConfig) -> tuple:
    """
    Scrape content from search results, avoiding duplicates.
    Returns: (aggregated_content, urls_this_iter, warnings)
    """
    warnings = []
    
    # Filter already scraped URLs
    filtered_search_results = [
        item for item in search_results 
        if item.get('url') and item.get('url') not in already_scraped_urls
    ]
    urls_this_iter = [item.get('url') for item in filtered_search_results if item.get('url')]
    
    if not filtered_search_results:
        return "", urls_this_iter, ["All search results already scraped."]
    
    # Scrape content
    scrape_urls_to_markdown(
        filtered_search_results,
        scraped_content_subfolder,
        jina_api_key=config.jina_api_key,
        delay=config.delay,
        youtube_transcript_languages=config.youtube_transcript_languages
    )
    
    # Aggregate content
    aggregated_content = []
    for item_idx, item in enumerate(filtered_search_results, 1):
        title = item.get('title', f'{LEGACY_RESULT_PREFIX}{item_idx}')
        filepath = _get_scraped_content_filepath(scraped_content_subfolder, title, item_idx, slugify)
        if filepath and os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                aggregated_content.append(f"# {title}\n\n{content}\n")
            except Exception as e:
                warnings.append(f"Error reading {filepath}: {e}")
        else:
            warnings.append(f"Scraped content file not found: {filepath}")
    
    if not aggregated_content:
        return "", urls_this_iter, ["No content could be scraped from the search results."]
    
    sources_text = "\n\n---\n\n".join(aggregated_content)
    return sources_text, urls_this_iter, warnings

def _llm_answer_step(query: str, sources: str, config: AgentConfig) -> str:
    """
    Generate an answer using the LLM based on the query and sources.
    """
    prompt = build_iteration_user_prompt(query, sources)
    answer = simple_agentic_prompt(
        user_prompt=prompt,
        model_name=config.model_name,
        temperature=config.temperature,
        system_prompt=AGENTIC_SYSTEM_PROMPT
    )
    return answer

def _synthesis_step(user_question: str, answers: List[str], config: AgentConfig) -> str:
    """
    Synthesize all iteration answers into a final comprehensive answer.
    """
    print("\n--- Boiling down all answers into a final comprehensive answer ---")
    boil_down_prompt = build_final_synthesis_prompt(user_question, answers)
    final_answer = simple_agentic_prompt(
        user_prompt=boil_down_prompt,
        model_name=config.model_name,
        temperature=config.temperature,
        system_prompt=FINAL_SYNTHESIS_SYSTEM_PROMPT
    )
    return final_answer

def _execute_single_iteration(
    query: str,
    already_scraped_urls: set,
    scraped_content_subfolder: str,
    config: AgentConfig
) -> tuple:
    """
    Execute a single search/scrape/answer iteration.
    Returns: (answer, urls_this_iter, warnings)
    """
    # Search
    search_results = _search_step(query, config)
    if not search_results:
        return "No search results found.", [], ["No search results found."]
    
    # Scrape
    sources, urls_this_iter, warnings = _scrape_step(
        search_results, already_scraped_urls, scraped_content_subfolder, config
    )
    if not sources:
        return "No content could be scraped.", urls_this_iter, warnings
    
    # Generate answer
    answer = _llm_answer_step(query, sources, config)
    return answer, urls_this_iter, warnings

def _generate_query_slug(user_question: str, model_name: str = "llama-3.3-70b-versatile", temperature: float = 0.0) -> str:
    """
    Generate a unique folder name for the user query.
    """
    parent_output_dir = PARENT_OUTPUT_DIR
    os.makedirs(parent_output_dir, exist_ok=True)

    base_slug = simple_agentic_prompt(
        user_prompt=f"User question: {user_question}",
        model_name=model_name,
        temperature=temperature,
        system_prompt=SYSTEM_PROMPT_SLUG
    ).strip().replace("/", "_")

    # Cleanup slug
    import re
    base_slug = re.sub(r'[^a-z0-9_]', '', base_slug.lower().replace(' ', '_'))
    base_slug = re.sub(r'_+', '_', base_slug).strip('_')
    base_slug = base_slug[:60]
    if not base_slug:
        base_slug = "research_query"
    
    # Ensure uniqueness
    base_folder_path = os.path.join(parent_output_dir, base_slug)
    unique_folder_path = base_folder_path
    counter = 1
    while os.path.exists(unique_folder_path) and os.path.isdir(unique_folder_path):
        unique_folder_path = f"{base_folder_path}_{counter}"
        counter += 1

    return unique_folder_path

def _get_scraped_content_filepath(base_dir: str, title: str, item_index: int, slugify_func) -> str:
    """
    Returns the filepath for a scraped content file, ensuring uniqueness and handling legacy fallback names.
    """
    slug = slugify_func(title)
    
    # Try base slug first
    filename = f"{slug}.md"
    filepath = os.path.join(base_dir, filename)
    if os.path.exists(filepath):
        return filepath
    
    # Try numbered versions
    counter = 1
    while counter <= 10:
        filename = f"{slug}_{counter}.md"
        filepath = os.path.join(base_dir, filename)
        if os.path.exists(filepath):
            return filepath
        counter += 1
    
    # Try legacy fallback
    legacy_filename = f"{LEGACY_RESULT_PREFIX}{item_index}.md"
    legacy_filepath = os.path.join(base_dir, legacy_filename)
    if os.path.exists(legacy_filepath):
        return legacy_filepath
    
    # Return base slug path if nothing exists
    return os.path.join(base_dir, f"{slug}.md")

# =============================================================================
# PUBLIC API (Simple, Clean Interface)
# =============================================================================

def research_workflow(user_question: str, config: AgentConfig = None) -> str:
    """
    Main entry point for multi-iteration research workflow.
    
    Args:
        user_question: The research question to investigate
        config: Configuration object (uses defaults if None)
    
    Returns:
        Final synthesized answer
    """
    if config is None:
        from .config import DEFAULT_CONFIG
        config = DEFAULT_CONFIG
    
    # Ensure required config
    if config.youtube_transcript_languages is None:
        config.youtube_transcript_languages = ['en', 'pt']
    
    # Generate output directory
    if config.output_dir is None:
        output_dir = _generate_query_slug(user_question, model_name=config.model_name, temperature=0.0)
    else:
        output_dir = config.output_dir
    
    scrape_output_folder = os.path.join(output_dir, "scraped_content")
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate search queries
    queries = _generate_search_queries(user_question, config)
    
    # Execute iterations
    answers = []
    search_prompts = []
    all_search_urls = []
    already_scraped_urls = set()  # FIXED: Persistent URL tracking
    
    for i in range(config.num_iterations):
        print(f"\n--- Iteration {i+1} ---")
        query = queries[i]
        
        answer, urls_this_iter, warnings = _execute_single_iteration(
            query=query,
            already_scraped_urls=already_scraped_urls,
            scraped_content_subfolder=scrape_output_folder,
            config=config
        )
        
        answers.append(answer)
        search_prompts.append(query)
        all_search_urls.append(urls_this_iter)
        already_scraped_urls.update(urls_this_iter)  # FIXED: Update persistent set
        
        print(f"\nAgentic answer for iteration {i+1} (truncated):\n{answer[:500]}\n{'...' if len(answer) > 500 else ''}")
        if warnings:
            print("\nWarnings for iteration:")
            for warning in warnings:
                print(f"- {warning}")
    
    # Synthesize final answer
    final_answer = _synthesis_step(user_question, answers, config)
    
    print("\nFINAL SYNTHESIZED ANSWER:\n")
    print(final_answer)
    
    # Save outputs
    iteration_data = [
        {'search_prompt': prompt, 'answer': answer, 'urls': urls} 
        for prompt, answer, urls in zip(search_prompts, answers, all_search_urls)
    ]
    model_config = {'model_name': config.model_name, 'temperature': config.temperature}
    save_run_outputs(output_dir, user_question, final_answer, iteration_data, model_config)
    
    return final_answer

def quick_research(user_question: str, config: AgentConfig = None) -> str:
    """
    Single-iteration research for quick answers.
    
    Args:
        user_question: The research question to investigate
        config: Configuration object (uses FAST_CONFIG if None)
    
    Returns:
        Answer from single iteration
    """
    if config is None:
        from .config import FAST_CONFIG
        config = FAST_CONFIG
    
    # Force single iteration
    config.num_iterations = 1
    
    return research_workflow(user_question, config)

def deep_research(user_question: str, config: AgentConfig = None) -> str:
    """
    Deep multi-iteration research for comprehensive answers.
    
    Args:
        user_question: The research question to investigate
        config: Configuration object (uses DEEP_RESEARCH_CONFIG if None)
    
    Returns:
        Final synthesized answer from deep research
    """
    if config is None:
        from .config import DEEP_RESEARCH_CONFIG
        config = DEEP_RESEARCH_CONFIG
    
    return research_workflow(user_question, config)

# =============================================================================
# LEGACY COMPATIBILITY (Deprecated but maintained for backward compatibility)
# =============================================================================

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
    DEPRECATED: Use quick_research() instead.
    Legacy single-iteration workflow for backward compatibility.
    """
    print("[DEPRECATED] search_scrape_and_answer is deprecated. Use quick_research() instead.")
    
    config = AgentConfig(
        model_name=model_name,
        temperature=temperature,
        num_iterations=1,
        num_search_results_per_iteration=num_search_results_per_iteration,
        jina_api_key=jina_api_key,
        youtube_transcript_languages=youtube_transcript_languages or ['en'],
        delay=delay
    )
    
    return quick_research(query, config)

# Alias for backward compatibility
def multi_agentic_search_scrape_answer(user_question: str, config: AgentConfig) -> str:
    """
    DEPRECATED: Use research_workflow() instead.
    Legacy multi-iteration workflow for backward compatibility.
    """
    print("[DEPRECATED] multi_agentic_search_scrape_answer is deprecated. Use research_workflow() instead.")
    return research_workflow(user_question, config)

# FIXED: Proper function signature and implementation
def run_search_and_synthesize_workflow(user_question: str, config: AgentConfig) -> str:
    """
    DEPRECATED: Use research_workflow() instead.
    Legacy workflow function - FIXED to work properly.
    """
    print("[DEPRECATED] run_search_and_synthesize_workflow is deprecated. Use research_workflow() instead.")
    return research_workflow(user_question, config)

# =============================================================================
# UTILITY FUNCTIONS (Public for advanced usage)
# =============================================================================

def generate_query_slug(user_question: str, model_name: str = "llama-3.3-70b-versatile", temperature: float = 0.0) -> str:
    """
    Public utility to generate a query slug.
    """
    return _generate_query_slug(user_question, model_name, temperature)

def get_scraped_content_filepath(base_dir: str, title: str, item_index: int, slugify_func) -> str:
    """
    Public utility to get scraped content filepath.
    """
    return _get_scraped_content_filepath(base_dir, title, item_index, slugify_func) 