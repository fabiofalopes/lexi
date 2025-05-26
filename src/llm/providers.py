"""
llm.py
LLM provider abstraction and utility functions for agentic workflows.
Contains all LLM-specific logic (model wrappers, prompt sending, config, etc.).
"""

from typing import List, Optional, Dict
from llama_index.llms.groq import Groq
from llama_index.core.llms import ChatMessage
import os

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