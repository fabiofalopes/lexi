from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class AgentConfig:
    """
    Central configuration for the agentic workflows.
    """
    model_name: str = "meta-llama/llama-4-maverick-17b-128e-instruct"
    temperature: float = 0.2
    num_iterations: int = 3
    num_search_results_per_iteration: int = 3
    output_dir: Optional[str] = None
    jina_api_key: Optional[str] = None
    youtube_transcript_languages: List[str] = field(default_factory=lambda: ['en', 'pt'])
    delay: float = 1.0
    # Add more fields as needed (e.g., API keys, advanced LLM/scraper config) 