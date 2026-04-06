"""
utils/llm.py
============
Shared LLM client and response parsing utilities.

All agents import from here — one place for Groq client creation,
JSON fence stripping, and response parsing.

Public API:
    get_groq_client()        → Groq instance (singleton)
    clean_json_response(str) → str (fences stripped)
    parse_json_response(str) → dict | list (cleaned + parsed)
"""

import json
import os
import logging

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Singleton Groq client ─────────────────────────────────────────────────────
_groq_client: Groq | None = None


def get_groq_client() -> Groq:
    """
    Return a singleton Groq client instance.

    Created on first call, reused across all agents. Uses the
    GROQ_API_KEY environment variable set via .env.

    Returns:
        Configured Groq client instance.
    """
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _groq_client


def clean_json_response(text: str) -> str:
    """
    Strip markdown code fences from LLM JSON responses.

    Handles all fence formats from different models:
        - ```json ... ```
        - ``` ... ```
        - No fences (returned as-is)

    Args:
        text: Raw LLM response string.

    Returns:
        Clean JSON string with fences removed.
    """
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        # Take the content between the first pair of fences
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def parse_json_response(text: str) -> dict | list:
    """
    Clean and parse an LLM JSON response in a single call.

    Strips markdown fences, then parses JSON. Single source of truth
    for all agents that expect structured JSON from Groq.

    Args:
        text: Raw LLM response string.

    Returns:
        Parsed Python dict or list.

    Raises:
        json.JSONDecodeError: If the cleaned text is not valid JSON.
    """
    cleaned = clean_json_response(text)
    return json.loads(cleaned)
