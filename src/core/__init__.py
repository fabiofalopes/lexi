"""
Core modules for the Lexi Owl agentic workflow system.
"""

from .agent import research_workflow, quick_research, deep_research
from .config import AgentConfig, DEFAULT_CONFIG, FAST_CONFIG, DEEP_RESEARCH_CONFIG, BALANCED_CONFIG
from .prompts import *
from .constants import *

__all__ = [
    "research_workflow",
    "quick_research",
    "deep_research", 
    "AgentConfig",
    "DEFAULT_CONFIG",
    "FAST_CONFIG",
    "DEEP_RESEARCH_CONFIG",
    "BALANCED_CONFIG"
] 