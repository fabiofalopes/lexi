"""
Lexi Owl - Agentic Research Workflow System

A modular system for conducting multi-iteration research using LLMs,
web search, and content scraping.
"""

from .core.agent import research_workflow, quick_research, deep_research
from .core.config import AgentConfig, DEFAULT_CONFIG, FAST_CONFIG, DEEP_RESEARCH_CONFIG, BALANCED_CONFIG

__version__ = "2.0.0"
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