# Refactoring Plan 2: Separation of Agentic Workflow and LLM Logic

## Motivation & Goals

- **Clarity:** Make `agent.py` focused solely on agentic workflow/orchestration, not LLM implementation details.
- **Reusability:** Enable LLM logic to be reused across different agents, tools, or integrations (e.g., LlamaIndex).
- **Extensibility:** Make it easy to add, swap, or extend LLM providers and tasks in the future.
- **Testability:** Allow LLM logic to be tested and mocked independently from agent workflows.

## What Will Change

- All LLM-specific code (model wrappers, prompt sending, LLM config, etc.) will move to a new module (e.g., `llm.py`).
- `agent.py` will import only the LLM interface(s) it needs (e.g., `simple_agentic_prompt`).
- Agentic workflow logic (search, scrape, aggregate, save, etc.) will remain in `agent.py`.
- (Optional) Define an abstract interface for LLMs to support multiple providers in the future.

## Concrete Steps

1. **Create `llm.py` (or `llm_utils.py`):**
   - Move all LLM-related classes/functions from `agent.py` (e.g., `GroqLLMWrapper`, `simple_agentic_prompt`).
   - Move any LLM-specific config or helper functions.
2. **Update Imports:**
   - In `agent.py` and elsewhere, import LLM functions/classes from `llm.py`.
3. **Refactor Usage:**
   - Ensure all LLM calls in `agent.py` go through the new module.
   - Remove any LLM implementation details from `agent.py`.
4. **(Optional) Abstract LLM Interface:**
   - Define a base class or protocol for LLMs if you want to support multiple providers (e.g., OpenAI, Groq, local models).
   - Implement the interface for each provider as needed.
5. **Testing:**
   - Run the main workflow to ensure everything works as before.
   - Add or update tests for LLM logic in isolation.
6. **Documentation:**
   - Update `log-dev.md` and internal comments to reflect the new structure.

## Future Considerations

- **Multiple LLM Providers:**
  - With this structure, adding new LLM backends (OpenAI, local, etc.) is straightforward.
- **Advanced LLM Tasks:**
  - Specialized LLM tasks (e.g., slug generation, query diversification) can be added as methods in `llm.py`.
- **Integration with LlamaIndex or other frameworks:**
  - The agentic workflow can easily call out to LlamaIndex or other tools, using the LLM interface as needed.

## Sensible Defaults & Simplicity

- **Default-Driven Agent Calls:**  
  The agentic workflow should be callable with minimal arguments, relying on the defaults defined in `AgentConfig` for most settings.
- **Override Only When Needed:**  
  Advanced users or integrations can override defaults by passing a custom `AgentConfig`, but this is not required for typical use.
- **Benefit:**  
  This keeps the agent interface simple, reduces boilerplate, and makes the codebase easier to maintain and use.

## AgentConfig Presets

- **Multiple Presets:**
  - Define several `AgentConfig` objects (e.g., `default_config`, `fast_config`, `deep_research_config`, etc.), each representing a different agent mode or use case.
- **Usage:**
  - Pass the desired config to the agent workflow to quickly switch between behaviors (e.g., quick vs. thorough, cheap vs. high-quality, LlamaIndex integration, etc.).
- **Example:**

    ```python
    from config import AgentConfig

    default_config = AgentConfig()
    fast_config = AgentConfig(num_iterations=1, num_search_results_per_iteration=2, temperature=0.1)
    deep_research_config = AgentConfig(num_iterations=5, num_search_results_per_iteration=8, temperature=0.3)

    # Usage:
    run_search_and_synthesize_workflow(config=fast_config)
    run_search_and_synthesize_workflow(config=deep_research_config)
    ```
- **Benefits:**
  - Quickly define the "core" of the agent for different scenarios.
  - No code duplication—just different config objects.
  - Easy to extend—add new configs as new use cases arise.

## Agent Development Plan Best Practices

This section adapts proven software and modular design best practices to the agentic/LLM context, ensuring the project remains robust, maintainable, and future-ready:

- **Purpose & Scope:** Clearly state the goal: a modular, maintainable, and extensible agentic system, separating workflow/orchestration from LLM logic, and ready for future integrations.
- **Modular Design Principles:**
  - Single Responsibility: Each module (agent, LLM, config, output, etc.) should have one clear purpose.
  - High Cohesion, Low Coupling: Keep related logic together, minimize dependencies between modules.
  - Encapsulation: Expose only what's necessary; keep implementation details private.
  - Clear Boundaries: Define what each module is responsible for.
- **Configuration Management:**
  - Use a central config object (`AgentConfig`) with sensible defaults and support for multiple presets.
  - Allow overrides, but keep the default interface simple.
- **Quality Assurance:**
  - Write unit tests for each module.
  - Test the full workflow after each major change.
  - Use code linters and formatters for consistency.
- **Documentation & Communication:**
  - Keep `plan2.md` and `log-dev.md` up to date as living documents.
  - Use clear, descriptive names for modules, functions, and configs.
  - Document module boundaries and responsibilities in code comments.
- **Extensibility & Future-Proofing:**
  - Design LLM interfaces to be pluggable (easy to swap providers).
  - Structure outputs for easy review, caching, and downstream use.
  - Plan for integration with frameworks like LlamaIndex by keeping agent and LLM logic decoupled.
- **Avoid Common Pitfalls:**
  - Don't let modules grow too large or take on multiple responsibilities.
  - Avoid circular dependencies.
  - Don't skip documentation or testing, even for "simple" modules.

**References:**
- [Best Practices for Modular Code Design](https://blog.pixelfreestudio.com/best-practices-for-modular-code-design/)
- [Software Development Plan (SDP) Outline](https://acqnotes.com/acqnote/careerfields/software-development-plan)

---

**This plan ensures the codebase remains clean, modular, and ready for future growth.** 