# Lexi Owl: Phase 1 Refactoring TODO List

**Objective:** Establish a clean project entry point with `main.py` and refactor `agent.py` to function as a callable module, enabling a more organized and scalable codebase.

---

## Core Tasks:

1.  **Create `main.py` File:**
    *   [ ] In the root of your `lexi_owl` project, create a new, empty file named `main.py`.

2.  **Analyze `agent.py`'s Main Execution Block:**
    *   [ ] Open `agent.py`.
    *   [ ] Carefully review all the code currently within the `if __name__ == "__main__":` block.
    *   [ ] Identify the distinct logical steps and parameters used (e.g., setting up models, defining queries, calling search, scraping, synthesizing, saving results).

3.  **Define and Create Workflow Function(s) in `agent.py`:**
    *   [ ] Based on the analysis, define one or more functions within `agent.py` that will encapsulate the logic from its current `__main__` block.
        *   *Suggestion:* A primary function like `def run_search_and_synthesize_workflow(user_query: str, anyscale_model: str, temperature: float, serper_api_key: str, anyscale_api_key: str, output_folder_name: str = "output", ...):` (add other parameters as needed).
    *   [ ] Move the relevant code from the `if __name__ == "__main__":` block into this new function(s).
    *   [ ] Ensure these functions take necessary parameters (like API keys, query, model names) and return meaningful results or handle outputs (like saving files).

4.  **Update `agent.py`'s `__main__` Block (Optional but Recommended):**
    *   [ ] Decide if you want to keep an `if __name__ == "__main__":` block in `agent.py` for its own isolated testing.
    *   [ ] If yes, modify it to call the new workflow function(s) you created in step 3, providing it with example/test parameters.
        ```python
        # Example for agent.py
        # ... (your function definitions like run_search_and_synthesize_workflow)

        if __name__ == "__main__":
            # This is now for testing agent.py itself, if needed
            print("Testing agent.py workflow function...")
            test_query = "What are the latest advancements in AI?"
            # ... define other test parameters ...
            run_search_and_synthesize_workflow(
                user_query=test_query,
                # ... other test parameters ...
            )
            print("agent.py test complete.")
        ```
    *   [ ] If no, you can remove or comment out the `if __name__ == "__main__":` block in `agent.py`.

5.  **Implement `main.py` to Orchestrate the Workflow:**
    *   [ ] Open `main.py`.
    *   [ ] Import the workflow function(s) you created in `agent.py` (e.g., `from agent import run_search_and_synthesize_workflow`).
    *   [ ] In the `if __name__ == "__main__":` block of `main.py`:
        *   Define the necessary parameters that your workflow function(s) expect (e.g., user query, API keys, model names). Initially, you can hardcode these for simplicity.
        *   Call the imported workflow function(s) from `agent.py`, passing these parameters.
        *   Print any results or confirmation messages.
    *   **Example `main.py` structure:**
        ```python
        from agent import run_search_and_synthesize_workflow # Or your chosen function name
        # Import any other necessary modules if main.py needs them directly

        if __name__ == "__main__":
            print("Lexi Owl Main Entry Point Activated")

            # --- Configuration ---
            # (Initially hardcode these. Later, this can come from args or config files)
            USER_QUERY = "YOUR_DESIRED_TEST_QUERY"
            ANYSCALE_MODEL_NAME = "mistralai/Mixtral-8x7B-Instruct-v0.1"
            TEMPERATURE_SETTING = 0.7
            SERPER_API_KEY = "YOUR_SERPER_API_KEY" # IMPORTANT: Consider how to handle secrets
            ANYSCALE_API_KEY = "YOUR_ANYSCALE_API_KEY" # IMPORTANT: Consider how to handle secrets
            OUTPUT_DIR_NAME = "my_agent_run_output"
            # ... add any other parameters your workflow function needs ...

            # --- Execute Workflow ---
            try:
                run_search_and_synthesize_workflow(
                    user_query=USER_QUERY,
                    anyscale_model=ANYSCALE_MODEL_NAME,
                    temperature=TEMPERATURE_SETTING,
                    serper_api_key=SERPER_API_KEY,
                    anyscale_api_key=ANYSCALE_API_KEY,
                    output_folder_name=OUTPUT_DIR_NAME
                    # ... pass other parameters ...
                )
                print(f"Workflow execution finished. Check the '{OUTPUT_DIR_NAME}' folder.")
            except Exception as e:
                print(f"An error occurred during workflow execution: {e}")

        ```

6.  **Test the New Entry Point:**
    *   [ ] Run `python main.py` from your terminal.
    *   [ ] Verify that the agent workflow executes as it did before, producing the expected outputs in the correct location.
    *   [ ] Debug any import errors or parameter mismatches.

---

## Considerations for Utility Scripts:

*   **`scraper.py`, `search.py`, `youtube_transcriber.py`:**
    *   For now, you can keep their existing `if __name__ == "__main__":` blocks if you use them for quick, isolated testing or development of those specific modules. This aligns with the goal of rapid iteration.
    *   Ensure they don't accidentally run full workflows if `main.py` is the intended orchestrator. Their `__main__` blocks should focus on testing their specific functionality.

---

This checklist should provide a clear path for the initial refactoring. Let me know if you want any adjustments or further details on any step! 