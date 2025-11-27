"""LLM configuration and factory."""

import os
from langchain_openai import ChatOpenAI


def get_llm():
    """Get configured LLM instance.

    Assumes OPENAI_API_KEY is set in environment.
    Returns a ChatOpenAI instance configured for detailed research tasks.
    """
    return ChatOpenAI(
        model="gpt-4.1",  # GPT-4.1 for detailed analysis and large contexts
        temperature=0,  # Zero temperature for maximum factual consistency
    )
