# Refactoring Plan for agent.py

## 1. Introduction

The primary goal of this refactoring effort is to significantly enhance the organization, reusability, maintainability, and overall effectiveness of the `agent.py` script. Key focus areas include:

*   Standardizing and centralizing prompt definitions.
*   Creating robust and reusable logic for handling scraped content file paths.
*   Implementing a more structured approach to configuration management.
*   Optimizing and modularizing the iteration logic for search, scrape, and answer workflows.
*   Standardizing results saving mechanisms to ensure comprehensive logging and better encapsulation of knowledge gathered per run. This includes structuring outputs within unique run folders, which can serve as a form of cache or knowledge base for human review and potential future automated use.
*   Ensuring consistency in function parameters and default values.

These changes are crucial for making the agent more robust, easier to debug, and more adaptable for future enhancements, including deeper integration with LlamaIndex.

## 2. Core Refactoring Areas

### 2.1. Prompt Management (Critical)

*   **Problem:** Numerous prompt strings (for system messages, user instructions, query generation, slug generation) are hardcoded and sometimes duplicated across different functions.
*   **Solution:**
    *   Define all static prompt strings as constants in a dedicated section at the top of `agent.py` or in a separate `prompts.py` module if they become numerous or complex.
    *   For dynamic prompts (like `build_iteration_user_prompt`), continue using template functions but ensure they are consistently used and clearly defined.
    *   **Examples for refactoring:**
        *   `search_query_generation_prompt` (in `multi_agentic_search_scrape_answer` and `run_search_and_synthesize_workflow`)
        *   `system_prompt_slug` (in `generate_query_slug`)
        *   The user prompt string within `search_scrape_and_answer` (lines 143-147).

### 2.2. Scraped Content File Path Handling (Crucial)

*   **Problem:** Complex and duplicated logic for determining file paths for scraped content, including slug generation, ensuring filename uniqueness (e.g., `slug_1.md`), and handling fallbacks (e.g., `result_{i}.md`). This logic is present in `search_scrape_and_answer`, `multi_agentic_search_scrape_answer`, and `run_search_and_synthesize_workflow`.
*   **Solution:**
    *   Create a dedicated helper function, e.g., `get_scraped_content_filepath(base_dir: str, title: str, item_index: int, slugify_func: callable) -> str`.
    *   This function will encapsulate:
        *   Slugification of the title.
        *   Logic to check for existing files and append counters (`_1`, `_2`, etc.) to ensure uniqueness within the `base_dir`.
        *   Handling of legacy fallback names if necessary.
    *   All functions that save or read scraped content should use this utility.

### 2.3. Configuration Management (Important)

*   **Problem:** Functions like `multi_agentic_search_scrape_answer` and `run_search_and_synthesize_workflow` accept many individual parameters for configuration (model names, temperature, API keys, paths, delays, etc.), which can become unwieldy.
*   **Solution:**
    *   Introduce a configuration object (e.g., a Pydantic model or a dataclass like `AgentConfig`) to group common settings.
    *   This config object can hold defaults and be overridden by environment variables or parameters passed during instantiation.
    *   Functions would then accept this `AgentConfig` object, or destructure relevant parts from it, simplifying their signatures.
    *   Consider a hierarchy if needed (e.g., `LLMConfig`, `ScraperConfig` nested within `AgentConfig`).

### 2.4. Iteration Logic Optimization (Important)

*   **Problem:** The main loop in `multi_agentic_search_scrape_answer` and `run_search_and_synthesize_workflow` (handling query execution, search, filtering already scraped URLs, scraping, content aggregation, and invoking the LLM for an iteration-specific answer) shares significant structural similarity.
*   **Solution:**
    *   Refactor the core logic of a single iteration into a more clearly defined, reusable function. This function might look like: `execute_iteration(query: str, config: AgentConfig, already_scraped_urls: set, scraped_content_subfolder: str) -> Tuple[str, List[str]]` returning the answer and list of URLs processed.
    *   The existing `search_scrape_and_answer` function is a good starting point but needs to be adapted to fit into the multi-iteration flow (e.g., handling `already_scraped_urls` and using the unique run's subfolder for scraping).
    *   The main multi-iteration functions will then call this `execute_iteration` function in a loop, managing the collection of `already_scraped_urls`, answers, and prompts.

### 2.5. Results Saving, Logging, and Knowledge Encapsulation (Very Important)

*   **Problem:** Logic for saving the final synthesized answer and all per-iteration details (prompts, answers, URLs) is duplicated and could be more robust. The current output structure per run is good but can be formalized.
*   **Solution:**
    *   The `generate_query_slug` function correctly creates a `unique_run_folder`. This folder should be the single source of truth for all artifacts of a given agent run.
    *   Create a dedicated helper function, e.g., `save_run_outputs(run_folder: str, user_question: str, final_answer: str, iteration_data: List[Dict],  model_config: Dict)`.
    *   `iteration_data` could be a list of dictionaries, each containing the search prompt, URLs, and agentic answer for that iteration.
    *   This function will be responsible for creating:
        *   `final_answer.md`
        *   `all_iteration_details.md` (or perhaps a JSON/YAML for easier parsing if needed in the future)
        *   A `run_summary.json` or `run_config.json` storing the initial user question, key configuration parameters (model, temp, iterations), and timestamps.
    *   The `scraped_content` subfolder within `unique_run_folder` will continue to store raw scraped data.
    *   This structured output enhances human-in-the-loop review and provides a foundation for a ".cache" or knowledge base that future processes could leverage.

### 2.6. Parameter Consistency (Important)

*   **Problem:** Potential for inconsistencies in parameter names (e.g., `num_results` vs `search_results_per_iter`) and default values across different functions.
*   **Solution:**
    *   Conduct a thorough review of all function signatures in `agent.py`.
    *   Standardize parameter names for similar concepts (e.g., consistently use `num_search_results_per_iteration`).
    *   Ensure default values are consistent and sensible. This effort aligns well with the Configuration Management (2.3) changes.

### 2.7. LLM Call Abstraction (Consideration)

*   **Problem:** Distinct LLM calls are made for specific generation tasks like creating slugs (`generate_query_slug`) and diversifying search queries.
*   **Solution (for now and future thought):**
    *   For the immediate refactoring, ensure the prompts for these tasks are managed as per Point 2.1.
    *   Long-term: If more such specialized LLM generation tasks are identified, consider creating a more generic helper function, e.g., `generate_via_llm(input_text: str, system_prompt_key: str, llm_config: LLMConfig) -> str`. This is not a priority for the initial refactor unless the need is strong.

### 2.8. Centralized Constants for Filenames and Paths

*   **Problem:** String literals like `"final_answer.md"`, `"all_iteration_answers.md"`, and `"scraped_content"` are used directly.
*   **Solution:** Define these as constants at the top of the module or within a dedicated constants section/file. This improves maintainability and reduces the risk of typos.

## 3. Proposed Refactoring Plan (Phased Approach)

### Phase 1: Foundations & Critical Fixes

1.  **Prompt Centralization (2.1):**
    *   Identify all hardcoded prompts.
    *   Define them as constants or ensure dynamic prompts use robust template functions.
2.  **Constants Definition (2.8):**
    *   Define common filenames (e.g., `FINAL_ANSWER_FILENAME = "final_answer.md"`) and directory names (e.g., `SCRAPED_CONTENT_DIR = "scraped_content"`) as constants.
3.  **Scraped Content File Path Helper (2.2):**
    *   Implement the `get_scraped_content_filepath` utility function.
    *   Integrate this utility into `search_scrape_and_answer`, `multi_agentic_search_scrape_answer`, and `run_search_and_synthesize_workflow` to replace existing file path logic.
4.  **Parameter Review & Standardization (2.6):**
    *   Review function signatures for consistency in naming and default values. Make necessary adjustments.

### Phase 2: Core Workflow and Output Standardization

1.  **Results Saving Helper (2.5):**
    *   Design and implement the `save_run_outputs` function.
    *   Update `multi_agentic_search_scrape_answer` and `run_search_and_synthesize_workflow` to use this function for all output saving. Ensure the `unique_run_folder` is the root for these outputs.
2.  **Iteration Logic Refinement (2.4 - Partial):**
    *   Analyze the iteration logic within `multi_agentic_search_scrape_answer` and `run_search_and_synthesize_workflow`.
    *   Adapt `search_scrape_and_answer` or create a new `execute_single_iteration` function that can be called by the main workflow functions. This function should cleanly handle scraping to the correct subfolder and respect `already_scraped_urls`.

### Phase 3: Configuration and Advanced Structure

1.  **Configuration Management (2.3):**
    *   Define an `AgentConfig` (and potentially nested `LLMConfig`, `ScraperConfig`) dataclass or Pydantic model.
    *   Refactor functions to accept and utilize this configuration object.
    *   Establish how default configurations are loaded and can be overridden.
2.  **Full Iteration Logic Optimization (2.4 - Full):**
    *   Ensure the multi-iteration workflows (`multi_agentic_search_scrape_answer`, `run_search_and_synthesize_workflow`) are streamlined by predominantly calling the `execute_single_iteration` function developed in Phase 2.

### Phase 4: Review and Future Enhancements

1.  **Code Review:** Perform a comprehensive review of all changes for clarity, correctness, and efficiency.
2.  **Documentation:** Update any internal comments or documentation to reflect the refactored structure.
3.  **LLM Call Abstraction (2.7):** Re-evaluate if a generic LLM call abstraction is beneficial based on the refactored codebase and potential new use cases.

## 4. Alignment with LlamaIndex

This refactoring effort will create a more modular and maintainable codebase, which is beneficial for any future integrations, including those with LlamaIndex:

*   **Cleaner Integrations:** A well-organized `agent.py` will make it easier to incorporate LlamaIndex components (e.g., custom LLMs, `QueryEngine` tools, `VectorStoreIndex` for retrieved documents, custom agent tools).
*   **Modular Prompts (2.1):** Centralized and templated prompts can be easily adapted or fed into LlamaIndex's `PromptTemplate` objects or used with its agent frameworks.
*   **Structured Configuration (2.3):** The `AgentConfig` can be extended to include LlamaIndex-specific configurations (e.g., `ServiceContext` parameters, embedding model choices, index configurations).
*   **Managed Data (2.2, 2.5):** The standardized handling of scraped content and run outputs means this data is more readily available and structured if it needs to be ingested into LlamaIndex data structures (e.g., creating a knowledge base from past run results).

## 5. LLM-Related Files / "Bigger Agent Picture"

To support the "bigger agent picture" and potentially enhance how the LLM components are managed:

*   **Externalized Prompt Templates:** If prompt templates become very large or numerous, consider storing them in separate `.txt` or `.md` files. These would be loaded by the application at runtime. This keeps `agent.py` cleaner.
*   **Configuration Files:** The `AgentConfig` (from 2.3) could eventually be loaded from a dedicated configuration file (e.g., `config.yaml`, `agent_settings.py`). This file becomes an explicit "LLM-related file" that defines agent behavior and settings.
*   **Structured Knowledge Output (2.5):** The `unique_run_folder` with its well-defined structure (scraped content, iteration details, final answer, run summary) effectively becomes a piece of encapsulated knowledge. This makes each run's output a self-contained "knowledge packet" that is human-readable and potentially machine-parseable for future meta-analysis or for feeding into a larger LlamaIndex-powered knowledge base over multiple agent runs.

By implementing this plan, `agent.py` will become a more robust and flexible component of the overall system.