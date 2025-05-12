from llama_index.llms.groq import Groq
from llama_index.core.llms import ChatMessage
from typing import List, Optional, Dict
import os
from dotenv import load_dotenv
load_dotenv()

# Import search and scraping utilities
from search import get_brave_search_results
from scraper import scrape_urls_to_markdown, slugify

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

class GroqLLMWrapper:
    def __init__(
        self,
        model_name: str = "llama-3.3-70b-versatile",
        temperature: float = 0.1
    ):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set in environment variables or .env file")
        
        self.llm = Groq(
            model=model_name,
            api_key=api_key,
            temperature=temperature
        )
        self.model_name = model_name
        self.temperature = temperature
        
    def get_llm(self):
        return self.llm

    def chat(self, messages: List[ChatMessage]) -> str:
        try:
            response = self.llm.chat(messages)
            return response.message.content
        except Exception as e:
            raise Exception(f"Error in Groq API call: {str(e)}")

# --- Simple agentic function using the wrapper ---
def simple_agentic_prompt(
    user_prompt: str,
    model_name: str = "llama-3.3-70b-versatile",
    temperature: float = 0.1,
    system_prompt: Optional[str] = None
) -> str:
    """
    A simple agentic function that sends a prompt to the Groq LLM.
    Optionally includes a system prompt for agentic behavior.
    """
    wrapper = GroqLLMWrapper(model_name=model_name, temperature=temperature)
    messages = []
    if system_prompt:
        messages.append(ChatMessage(role="system", content=system_prompt))
    messages.append(ChatMessage(role="user", content=user_prompt))
    return wrapper.chat(messages)

# --- Improved system prompt for maximal extraction ---
AGENTIC_SYSTEM_PROMPT = (
    "You are a research assistant. Your job is to extract, quote, and synthesize as much information as possible from the provided sources. "
    "Be exhaustive, detailed, and reference the sources directly. Do not summarize unless explicitly asked. "
    "Err on the side of including more information, not less."
)

# --- Improved per-iteration user prompt template ---
def build_iteration_user_prompt(query: str, sources_text: str) -> str:
    return (
        f"Using the following sources, answer the question: {query}\n\n"
        f"SOURCES:\n\n{sources_text}\n\n"
        "Instructions:\n"
        "- Extract and include as much relevant information as possible.\n"
        "- Quote and reference the sources liberally.\n"
        "- Organize the answer in sections or bullet points if helpful.\n"
        "- Do NOT summarize or omit details unless they are clearly irrelevant.\n"
        "- The answer should be comprehensive, detailed, and full of references/quotes from the sources.\n"
    )

# --- Improved final synthesis system prompt ---
FINAL_SYNTHESIS_SYSTEM_PROMPT = (
    "You are a research synthesis agent. Your job is to combine all the information from the previous answers into a single, comprehensive, detailed, and referenced Markdown document. "
    "Err on the side of verbosity and coverage. Include all relevant details, quotes, and references from the answers. Do not summarize unless explicitly asked."
)

# --- Improved final synthesis user prompt template ---
def build_final_synthesis_prompt(user_question: str, answers: list) -> str:
    return (
        f"Given the user question: '{user_question}', and the following six answers from different search and scrape iterations, "
        "write a comprehensive, referenced Markdown answer that synthesizes all the information, cites sources, and is suitable for a technical audience.\n\n"
        "Instructions:\n"
        "- Be exhaustive and detailed.\n"
        "- Quote and reference the sources liberally.\n"
        "- Organize the answer in sections or bullet points if helpful.\n"
        "- Do NOT summarize or omit details unless they are clearly irrelevant.\n"
        "- The answer should be comprehensive, detailed, and full of references/quotes from the answers.\n\n"
        + chr(10).join([f"Answer {i+1}:\n{a}\n" for i, a in enumerate(answers)])
    )

# --- New: Search, Scrape, and Answer Agent Function ---
def search_scrape_and_answer(
    query: str,
    num_results: int = 3,
    model_name: str = "llama-3.3-70b-versatile",
    temperature: float = 0.2,
    system_prompt: Optional[str] = AGENTIC_SYSTEM_PROMPT,
    scrape_output_folder: str = "outputs/_agent_temp_scraped",
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
    search_results = get_brave_search_results(query, api_key=os.environ.get("BRAVE_API_KEY"), count=num_results)
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
        title = item.get('title', f'result_{i}')
        slug = slugify(title)
        filename = f"{slug}.md"
        filepath = os.path.join(scrape_output_folder, filename)
        if not os.path.exists(filepath):
            # Try fallback: result_{i}.md (legacy)
            fallback = os.path.join(scrape_output_folder, f"result_{i}.md")
            if os.path.exists(fallback):
                filepath = fallback
            else:
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
    parent_output_dir = "outputs" # Main directory for all runs
    os.makedirs(parent_output_dir, exist_ok=True)

    system_prompt_slug = (
        "You are a filename/slug generator. Given a user research question, generate a short, lowercase, underscore-separated folder name (max 60 chars, no special chars, no spaces, no numbers unless in the query, no stopwords, always deterministic for the same input). Output ONLY the slug, nothing else."
    )
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
def multi_agentic_search_scrape_answer(
    user_question: str,
    num_iterations: int = 3,
    num_results: int = 2,
    model_name: str = "llama-3.3-70b-versatile",
    temperature: float = 0.2,
    system_prompt: Optional[str] = AGENTIC_SYSTEM_PROMPT,
    scrape_output_folder: str = "outputs/_agent_temp_scraped",
    jina_api_key: Optional[str] = None,
    youtube_transcript_languages: Optional[List[str]] = None,
    delay: float = 1.0
) -> str:
    """
    Runs the full multi-agent workflow: generate queries, search, scrape, answer per iteration, synthesize.
    Ensures a unique output folder for each run.
    """
    # 1. Generate Unique Output Folder Path for this Run
    unique_run_folder = generate_query_slug(user_question, model_name=model_name)
    # Define the specific subfolder for scraped content within the unique run folder
    scraped_content_subfolder = os.path.join(unique_run_folder, "scraped_content") 

    # 2. Generate Diverse Search Queries
    print("\nGenerating unique, diverse search queries with the LLM...")
    search_query_generation_prompt = (
        f"Given the user question: '{user_question}', generate a list of {num_iterations} unique, diverse, and non-overlapping search queries that, together, will maximize the coverage of relevant information. "
        "Each query should be different in focus, keywords, or angle, but all should be relevant to the user question. Output only the list, one per line."
    )
    queries_text = simple_agentic_prompt(
        user_prompt=search_query_generation_prompt,
        model_name=model_name,
        temperature=temperature,
        system_prompt="You are a search query diversification agent."
    )
    # Parse queries (split by lines, remove empty)
    queries = [q.strip('"').strip() for q in queries_text.splitlines() if q.strip()]
    if len(queries) < num_iterations:
        print(f"Warning: Only {len(queries)} unique queries generated, expected {num_iterations}.")
        queries += [user_question] * (num_iterations - len(queries))
    print("\nGenerated search queries:")
    for i, q in enumerate(queries[:num_iterations], 1):
        print(f"{i}. {q}")

    # 3. For each query, search, scrape, and answer
    answers = []
    search_prompts = []
    all_search_urls = []
    for i in range(num_iterations):
        print(f"\n--- Iteration {i+1} ---")
        query = queries[i]
        search_prompts.append(query)
        print(f"Search prompt for iteration {i+1}: {query}")

        # Search
        search_results = get_brave_search_results(query, api_key=os.environ.get("BRAVE_API_KEY"), count=num_results)
        if not search_results:
            print(f"No search results for iteration {i+1}.")
            answers.append("No search results found.")
            all_search_urls.append([])
            continue
        urls_this_iter = [item.get('url') for item in search_results if item.get('url')]
        all_search_urls.append(urls_this_iter)
        print(f"Brave search URLs for iteration {i+1}:")
        for url in urls_this_iter:
            print(f"- {url}")

        # Scrape (Pass the unique path for this run's scraped content)
        # scrape_urls_to_markdown will create the scraped_content_subfolder if it doesn't exist
        scrape_urls_to_markdown(
            search_results,
            scraped_content_subfolder, # Use the subfolder path within the unique run folder
            jina_api_key=jina_api_key,
            delay=delay,
            youtube_transcript_languages=youtube_transcript_languages or ['en']
        )

        # Aggregate content (Read from the correct subfolder)
        aggregated_content = []
        for item_idx, item in enumerate(search_results, 1):
            title = item.get('title', f'result_{item_idx}')
            slug = slugify(title)
            # Ensure filename uniqueness within the subfolder (same logic as in scraper.py)
            filename_candidate = f"{slug}.md"
            filepath = os.path.join(scraped_content_subfolder, filename_candidate) 
            file_counter = 1
            while not os.path.exists(filepath):
                 # If the primary name doesn't exist, check for numbered fallbacks
                 # This might happen if slugify was inconsistent or file saving failed/retried
                 filename_candidate = f"{slug}_{file_counter}.md"
                 filepath = os.path.join(scraped_content_subfolder, filename_candidate)
                 file_counter += 1
                 if file_counter > 5: # Safety break to avoid infinite loop
                      filepath = None # Assume file is missing
                      break 
            # If after checking numbered versions, still no file, try the original fallback
            if not filepath or not os.path.exists(filepath):
                 fallback = os.path.join(scraped_content_subfolder, f"result_{item_idx}.md") # Legacy name
                 if os.path.exists(fallback):
                      filepath = fallback
                 else:
                      print(f"Warning: Scraped file for '{title}' not found at expected paths in {scraped_content_subfolder}.")
                      continue # Skip this result if file not found
                      
            if filepath:
                 try:
                      with open(filepath, 'r', encoding='utf-8') as f:
                           content = f.read()
                      aggregated_content.append(f"## Source: {title}\nURL: <{item.get('url')}>\n\n{content}\n")
                 except Exception as e:
                      print(f"Error reading file {filepath}: {e}")
        
        if not aggregated_content:
            answers.append("No content could be scraped from the search results.")
            continue
        sources_text = "\n\n---\n\n".join(aggregated_content)
        user_prompt = build_iteration_user_prompt(query, sources_text)
        answer = simple_agentic_prompt(
            user_prompt=user_prompt,
            model_name=model_name,
            temperature=temperature,
            system_prompt=system_prompt
        )
        answers.append(answer)
        print(f"\nAgentic answer for iteration {i+1} (truncated):\n{answer[:500]}\n{'...' if len(answer) > 500 else ''}")

    # 4. Boil down all answers into a final comprehensive answer
    print("\n--- Boiling down all answers into a final comprehensive answer ---")
    boil_down_prompt = build_final_synthesis_prompt(user_question, answers)
    final_answer = simple_agentic_prompt(
        user_prompt=boil_down_prompt,
        model_name=model_name,
        temperature=temperature,
        system_prompt=FINAL_SYNTHESIS_SYSTEM_PROMPT
    )
    print("\nFINAL SYNTHESIZED ANSWER:\n")
    print(final_answer)

    # Save the final answer and all per-iteration answers in the base of the query folder
    output_file = os.path.join(unique_run_folder, "final_answer.md")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(final_answer)
    print(f"\nFinal answer saved to {output_file}")

    all_answers_file = os.path.join(unique_run_folder, "all_iteration_answers.md")
    with open(all_answers_file, 'w', encoding='utf-8') as f:
        for i, (prompt, answer, urls) in enumerate(zip(search_prompts, answers, all_search_urls), 1):
            f.write(f"\n---\n\n# Iteration {i}\n\n## Search Prompt:\n{prompt}\n\n## Brave Search URLs:\n" + "\n".join(urls) + f"\n\n## Agentic Answer:\n{answer}\n")
    print(f"All iteration answers saved to {all_answers_file}")

    return final_answer

# --- Example usage ---
if __name__ == "__main__":
    print("Available Groq models:")
    for k, v in GROQ_MODELS.items():
        print(f"- {k}: {v}")
    
    #user_question = "Urze. Portugal, Coimbra, Pampilhosa da Serra, Malhada do Rei. Produção de mel e enxames de abelhas, rainhas e optimização das colónias, desdobramentos. Tradição do mel da Urze. Mecanismos de monitorização e controlo de colónias. Precision beekeeping. Como implementar soluções existentes e até open source para a nossa região?"
    #user_question = "We want to implement our monitoring system for beehives. Open source solutions for beekeeping, lora, batteries, solar panels, recording audio, sensors"
    user_question = "Como cultivar urze de forma controlada?"
    print("\nRunning multi-agentic search-scrape-answer workflow...")

    NUM_ITERATIONS = 3
    SEARCH_RESULTS_PER_ITER = 2
    model_name = "meta-llama/llama-4-maverick-17b-128e-instruct"
    temperature = 0.25

    # Generate a consistent folder name for this run based on the user query
    output_dir = generate_query_slug(user_question, model_name=model_name, temperature=0.0)
    scrape_output_folder = os.path.join(output_dir, "scraped_content")
    os.makedirs(output_dir, exist_ok=True)
    jina_api_key = os.environ.get("JINA_API_KEY")
    youtube_transcript_languages = ['en', 'pt']
    delay = 1.5

    answers = []
    search_prompts = []
    all_search_urls = []

    # 1. Generate a list of unique, diverse search queries using the LLM
    print("\nGenerating unique, diverse search queries with the LLM...")
    search_query_generation_prompt = (
        f"Given the user question: '{user_question}', generate a list of {NUM_ITERATIONS} unique, diverse, and non-overlapping search queries that, together, will maximize the coverage of relevant information. "
        "Each query should be different in focus, keywords, or angle, but all should be relevant to the user question. Output only the list, one per line."
    )
    queries_text = simple_agentic_prompt(
        user_prompt=search_query_generation_prompt,
        model_name=model_name,
        temperature=temperature,
        system_prompt="You are a search query diversification agent."
    )
    # Parse queries (split by lines, remove empty)
    queries = [q.strip('"').strip() for q in queries_text.splitlines() if q.strip()]
    if len(queries) < NUM_ITERATIONS:
        print(f"Warning: Only {len(queries)} unique queries generated, expected {NUM_ITERATIONS}.")
        queries += [user_question] * (NUM_ITERATIONS - len(queries))
    print("\nGenerated search queries:")
    for i, q in enumerate(queries[:NUM_ITERATIONS], 1):
        print(f"{i}. {q}")

    # 2. For each query, search, scrape, and answer
    for i in range(NUM_ITERATIONS):
        print(f"\n--- Iteration {i+1} ---")
        search_prompt = queries[i]
        search_prompts.append(search_prompt)
        print(f"Search prompt for iteration {i+1}: {search_prompt}")

        # Brave search
        search_results = get_brave_search_results(search_prompt, api_key=os.environ.get("BRAVE_API_KEY"), count=SEARCH_RESULTS_PER_ITER)
        if not search_results:
            answers.append("No search results found.")
            all_search_urls.append([])
            continue
        urls_this_iter = [item.get('url') for item in search_results if item.get('url')]
        all_search_urls.append(urls_this_iter)
        print(f"Brave search URLs for iteration {i+1}:")
        for url in urls_this_iter:
            print(f"- {url}")

        # Scrape
        scrape_urls_to_markdown(
            search_results,
            scrape_output_folder,
            jina_api_key=jina_api_key,
            delay=delay,
            youtube_transcript_languages=youtube_transcript_languages
        )
        aggregated_content = []
        for idx, item in enumerate(search_results, 1):
            title = item.get('title', f'result_{idx}')
            slug = slugify(title)
            filename = f"{slug}.md"
            filepath = os.path.join(scrape_output_folder, filename)
            if not os.path.exists(filepath):
                fallback = os.path.join(scrape_output_folder, f"result_{idx}.md")
                if os.path.exists(fallback):
                    filepath = fallback
                else:
                    print(f"[Scrape Error] Could not find file for '{title}' (slug: {slug}) in iteration {i+1}.")
                    continue
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                aggregated_content.append(f"# {title}\n\n{content}\n")
            except Exception as e:
                print(f"[Scrape Error] Failed to read file {filepath}: {e}")
        if not aggregated_content:
            answers.append("No content could be scraped from the search results.")
            continue
        sources_text = "\n\n---\n\n".join(aggregated_content)
        user_prompt = build_iteration_user_prompt(search_prompt, sources_text)
        answer = simple_agentic_prompt(
            user_prompt=user_prompt,
            model_name=model_name,
            temperature=temperature,
            system_prompt=AGENTIC_SYSTEM_PROMPT
        )
        answers.append(answer)
        print(f"\nAgentic answer for iteration {i+1} (truncated):\n{answer[:500]}\n{'...' if len(answer) > 500 else ''}")

    # 3. Boil down all answers into a final comprehensive answer
    print("\n--- Boiling down all answers into a final comprehensive answer ---")
    boil_down_prompt = build_final_synthesis_prompt(user_question, answers)
    final_answer = simple_agentic_prompt(
        user_prompt=boil_down_prompt,
        model_name=model_name,
        temperature=temperature,
        system_prompt=FINAL_SYNTHESIS_SYSTEM_PROMPT
    )
    print("\nFINAL SYNTHESIZED ANSWER:\n")
    print(final_answer)

    # Save the final answer and all per-iteration answers in the base of the query folder
    output_file = os.path.join(output_dir, "final_answer.md")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(final_answer)
    print(f"\nFinal answer saved to {output_file}")

    all_answers_file = os.path.join(output_dir, "all_iteration_answers.md")
    with open(all_answers_file, 'w', encoding='utf-8') as f:
        for i, (prompt, answer, urls) in enumerate(zip(search_prompts, answers, all_search_urls), 1):
            f.write(f"\n---\n\n# Iteration {i}\n\n## Search Prompt:\n{prompt}\n\n## Brave Search URLs:\n" + "\n".join(urls) + f"\n\n## Agentic Answer:\n{answer}\n")
    print(f"All iteration answers saved to {all_answers_file}")