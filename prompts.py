# prompts.py
"""
Centralized prompt strings and templates for agentic workflows.
"""

# --- Static System Prompts ---
AGENTIC_SYSTEM_PROMPT = (
    "You are a research assistant. Your job is to extract, quote, and synthesize as much information as possible from the provided sources. "
    "Be exhaustive, detailed, and reference the sources directly. Do not summarize unless explicitly asked. "
    "Err on the side of including more information, not less."
)

FINAL_SYNTHESIS_SYSTEM_PROMPT = (
    "You are a research synthesis agent. Your job is to combine all the information from the previous answers into a single, comprehensive, detailed, and referenced Markdown document. "
    "Err on the side of verbosity and coverage. Include all relevant details, quotes, and references from the answers. Do not summarize unless explicitly asked."
)

SYSTEM_PROMPT_SLUG = (
    "You are a filename/slug generator. Given a user research question, generate a short, lowercase, underscore-separated folder name (max 60 chars, no special chars, no spaces, no numbers unless in the query, no stopwords, always deterministic for the same input). Output ONLY the slug, nothing else."
)

SEARCH_QUERY_DIVERSIFICATION_SYSTEM_PROMPT = (
    "You are a search query diversification agent."
)

# --- Prompt Templates (as functions) ---
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

def build_final_synthesis_prompt(user_question: str, answers: list) -> str:
    return (
        f"Given the user question: '{user_question}', and the following several answers from different search and scrape iterations, "
        "write a comprehensive, referenced Markdown answer that synthesizes all the information, cites sources, and is suitable for a technical audience.\n\n"
        "Instructions:\n"
        "- Be exhaustive and detailed.\n"
        "- Quote and reference the sources liberally.\n"
        "- Organize the answer in sections or bullet points if helpful.\n"
        "- Do NOT summarize or omit details unless they are clearly irrelevant.\n"
        "- The answer should be comprehensive, detailed, and full of references/quotes from the answers.\n\n"
        + chr(10).join([f"Answer {i+1}:\n{a}\n" for i, a in enumerate(answers)])
    )

# --- Search Query Generation Prompt Template ---
def build_search_query_generation_prompt(user_question: str, num_iterations: int) -> str:
    return (
        f"Given the user question: '{user_question}', generate a list of {num_iterations} unique, diverse, and non-overlapping search queries that, together, will maximize the coverage of relevant information. "
        "Each query should be different in focus, keywords, or angle, but all should be relevant to the user question. Output only the list, one per line."
    ) 