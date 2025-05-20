# Lexi Owl Project: Agentic Workflow & Codebase Organization Feedback

## 1. Current State: What Works Well
- **Functional Modularity:** You have clear separation of concerns: `scraper.py` for scraping, `search.py` for search, `youtube_transcriber.py` for YouTube, and `agent.py` for orchestration. This is a strong foundation.
- **Reusable Utilities:** Helper functions (e.g., `slugify`, cookie banner removal, YouTube transcript extraction) are well-encapsulated and reused across files.
- **Agentic Workflow:** The main agentic workflow (multi-step search, scrape, synthesize) is implemented and outputs are well-organized into unique folders per run, with Markdown files for traceability.
- **Output Structure:** Each run creates a dedicated folder with all relevant outputs, making results easy to audit and extend.
- **Configurable Parameters:** Many parameters (model, temperature, number of iterations, etc.) are exposed at the top of the main script, making experimentation easy.

## 2. Main Pain Points & Opportunities
- **Hardcoded Main Function:** The main entry point (`if __name__ == "__main__"` in `agent.py`) is monolithic and mixes configuration, workflow logic, and example usage. This makes it harder to reuse, test, or extend.
- **Scattered Main Functions:** Other files (e.g., `scraper.py`, `youtube_transcriber.py`) also have their own `__main__` blocks for testing, which is useful for development but can lead to confusion or duplication.
- **Workflow Coupling:** The agentic workflow is tightly coupled to specific steps (search, scrape, synthesize) and output structure. Adding new modalities (e.g., image models, new LLMs, different input types) would require editing the main agent script directly.
- **Testing & Iteration:** There is no clear separation between development/testing code and production/agentic workflow code. This can slow down iteration and make it harder to onboard new contributors or port code from other projects.
- **Extensibility:** While you have modular scripts, the process for plugging in new functionalities (e.g., a new transcription method, a new agent type) is not yet standardized.

## 3. Recommendations for Organization & Workflow

### A. Main Entry Point: Centralize and Simplify
- **Single Entrypoint:** Create a single `main.py`. This file will be your project's command center. Initially, `agent.py` can house the core workflow logic in functions, and `main.py` will call these.
- **No Logic in `main.py`'s Top Level:** The `main.py` file itself should primarily parse arguments (eventually), load configurations, and then call the main workflow function(s) from `agent.py` or other dedicated workflow modules.
  ```python
  # Example structure for main.py
  # from agent import run_my_workflow # Or whatever you call your main function
  # from config_loader import load_config # If you add a config loader

  # def main():
  #     # args = parse_args() # For later CLI integration
  #     # config = load_config(args)
  #     print("Starting Lexi Owl Agent...")
  #     # result = run_my_workflow(some_parameters) # Call your workflow
  #     # print(f"Workflow finished. Output: {result}")
  #     pass # Replace with actual calls

  if __name__ == "__main__":
      # main()
      print("Placeholder for main.py execution. Refactor agent.py's main block here.")
  ```
- **Refactor `agent.py`'s `__main__` block:** The current logic within `if __name__ == "__main__":` in `agent.py` should be moved into one or more well-defined functions within `agent.py` itself (e.g., `def execute_agent_workflow(...)`). This transforms `agent.py` into a library of functions that `main.py` can call.
- **Support CLI & Programmatic Use:** Design `main.py` so that its core logic can be triggered by command-line arguments or imported and called as a function from other Python scripts or notebooks.

### B. Modular Agentic Workflows
- **Workflow Functions:** Define each agentic workflow as a function (e.g., `def run_search_scrape_synthesize(...)`).
- **Composable Steps:** Each step (search, scrape, transcribe, synthesize) should be a function with clear inputs/outputs. This makes it easy to swap, extend, or test steps independently.
- **Plug-and-Play:** Use a registry or config pattern to allow new steps (e.g., image analysis, different LLMs) to be plugged in without editing the main workflow code.

### C. Development & Testing
- **Dedicated Test/Example Scripts:** For now, you can keep using `if __name__ == "__main__":` blocks in your individual modules (`scraper.py`, `youtube_transcriber.py`) for quick, isolated unit testing or development.
- **Move complex tests/examples:** For more integrated tests or showcasing complete workflows, consider an `examples/` or `dev_scripts/` folder. These scripts would import from your main modules and `main.py`.
- **Unit Tests (Future Goal):** For each utility or workflow function, adding simple unit tests later (even if just smoke tests) will ensure changes don't break core functionality. This is a good practice to grow into.

### D. Extensibility & Reuse
- **Standardize Interfaces:** Define clear interfaces for new modules (e.g., all scrapers should implement `scrape(url, ...) -> dict`).
- **Config-Driven Workflows:** Use a config file (YAML, TOML, or JSON) to define which steps to run, which models to use, and where to output results. This makes it easy to add new workflows or change parameters without code changes.
- **Document Extension Points:** In your README or a `CONTRIBUTING.md`, document how to add a new agent, scraper, or workflow step.

### E. Output & Results
- **Consistent Output Structure:** Keep the current pattern of unique output folders per run. Consider adding a manifest file (e.g., `run_metadata.json`) in each output folder summarizing the run parameters, steps, and outputs.
- **Logging:** Add logging (not just print statements) to track workflow progress and errors. This helps with debugging and reproducibility.

## 4. Example: Refactored Main Workflow Layout

```
lexi_owl/
  agentic_workflows/
    __init__.py
    search_scrape_synthesize.py
    youtube_transcribe.py
    ...
  utils/
    __init__.py
    scraper_utils.py
    search_utils.py
    ...
  main.py  # Only parses args, loads config, calls workflow
  config/
    default.yaml
  tests/
    test_scraper.py
    test_agentic_workflow.py
  outputs/
    ...
  README.md
```

## 5. Next Steps
- **Refactor the main entry point to be minimal and delegate to workflow functions.**
- **Move all dev/test code to a dedicated folder.**
- **Standardize interfaces for new modules and document extension points.**
- **Adopt a config-driven approach for workflow selection and parameters.**
- **Add basic unit tests and logging.**

## 6. Phased Implementation Plan (Your "Wizard" Guide)

This section provides a more step-by-step approach to implement the recommendations, focusing on immediate impact with manageable effort.

**Phase 1: Establish a Clean Entry Point & Basic Organization (Your Immediate Focus)**

1.  **Create `main.py`:**
    *   Create a new file named `main.py` in the root of your `lexi_owl` project.
    *   This file will be the *sole* entry point for running your agentic workflows.
2.  **Refactor `agent.py`:**
    *   Open `agent.py`.
    *   Identify all the code currently inside the `if __name__ == "__main__":` block.
    *   Move this entire block of logic into one or more new functions within `agent.py`. For example, you could create a function like `def run_search_and_synthesize_workflow(user_query, anyscale_model, temperature, ...):`.
    *   The goal is to make `agent.py` a library of functions that `main.py` can call. Its own `if __name__ == "__main__":` block (if kept for its own testing) should be minimal or call its own functions with test data.
3.  **Connect `main.py` to `agent.py`:**
    *   In `main.py`, import the necessary function(s) you just created in `agent.py`.
    *   In `main.py`'s `if __name__ == "__main__":` block, call these imported function(s) with the parameters they need. Initially, you can hardcode these parameters in `main.py` just like they were in `agent.py`.
    *   **Example `main.py`:**
        ```python
        from agent import run_search_and_synthesize_workflow # Assuming this is your refactored function
        # Potentially import other things like scraper, youtube_transcriber if needed directly by main
        # or if agent.py doesn't orchestrate them fully.

        if __name__ == "__main__":
            print("Lexi Owl Main Entry Point Activated")
            # Define parameters previously in agent.py's main block
            user_query = "Your sample query"
            anyscale_model = "mistralai/Mixtral-8x7B-Instruct-v0.1"
            # ... other parameters ...

            # Call the workflow
            run_search_and_synthesize_workflow(
                user_query=user_query,
                anyscale_model=anyscale_model,
                # ... pass other parameters ...
            )
            print("Workflow execution finished.")
        ```
4.  **Organize Development Snippets:**
    *   **Keep `__main__` in utility scripts for now:** It's fine to keep the `if __name__ == "__main__":` blocks in `scraper.py`, `youtube_transcriber.py`, etc., for your quick, isolated development and testing of those specific modules.
    *   **Consider an `examples/` directory:** If you have scripts that demonstrate a full workflow or test integrations between multiple modules, create an `examples/` (or `dev_scripts/`) directory and place them there. These scripts would import functions from `agent.py`, `scraper.py`, etc.

**Why these steps first?**
*   **Clarity:** You'll immediately have a clear separation: `main.py` *runs* the show, and your other `.py` files *provide the tools and capabilities*.
*   **Simplicity:** This doesn't require a massive restructuring of your existing logic, just moving it into functions.
*   **Foundation:** This sets a solid base for all future enhancements (CLI arguments, config files, new modules).

**Phase 2: Enhance Configuration & Modularity (Once Phase 1 is Solid)**

*   **Command-Line Arguments:** Modify `main.py` to accept parameters (like the user query, model choice) via command-line arguments (e.g., using `argparse`).
*   **Configuration Files:** Introduce a simple configuration file (e.g., `config.ini`, JSON, or YAML) to manage settings like API keys, model names, default parameters, etc. `main.py` would load this.
*   **Formalize Workflow Functions:** Ensure each major step (search, scrape, transcribe, synthesize) is a distinct function with clear inputs and outputs. This makes them easier to combine in new ways.
*   **Basic Logging:** Introduce the `logging` module for better tracking and debugging, instead of just `print` statements.

**Phase 3: Advanced Structure & Testing (Long-Term Evolution)**

*   **Refined Directory Structure:** Fully implement the suggested directory structure (e.g., `agentic_workflows/`, `utils/`, `config/`, `tests/`).
*   **Unit Tests:** Start adding formal unit tests for key functions in a `tests/` directory.
*   **Plugin System/Registry (Optional):** For advanced extensibility, consider patterns like a registry for discovering and loading different tools or workflow steps.

By tackling this in phases, you can make steady progress and see immediate benefits without getting bogged down. The "wizard" advice is to start with Phase 1 – it's the highest leverage change you can make right now!

---

This feedback is based on your current codebase and your goals for extensibility, modularity, and rapid iteration. No code changes are suggested here—this is a roadmap for evolving your project structure as you continue to add new agentic capabilities and workflows.
This feedback is designed to be a practical guide. Focus on Phase 1 first, and you'll see a significant improvement in your project's organization and your ability to manage its growth. 