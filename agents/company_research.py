"""
company_research.py
===================
Researches a company and returns a plain-text summary for cover letter enrichment.

Pipeline:
    1. Tavily search  — fetches top 5 results for culture, tech, mission, values
    2. Score filter   — keeps only results with score >= 0.55, takes top 3
    3. Groq summarize — synthesizes filtered snippets into a clean 150-word summary

Returns empty string at any failure point — caller never needs to handle exceptions.
"""

import os
import logging

from dotenv import load_dotenv
from tavily import TavilyClient, BadRequestError
from prompts.company_research_prompt import COMPANY_RESEARCH_SYSTEM_PROMPT
from utils.llm import get_groq_client

load_dotenv()
logger = logging.getLogger(__name__)

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
groq_client = get_groq_client() 


def get_company_data(company: str) -> str:
    """
    Search Tavily for company information and return filtered, joined snippets.

    Fetches up to 5 results, filters by score threshold (0.55), sorts descending,
    and joins the content fields of the top 3 results into a single string.

    Args:
        company: Company name to search for.

    Returns:
        Joined content string from top results, or empty string if no results
        pass the score threshold or if Tavily fails.
    """

    try:
        logger.info(f"Searching with Tavily: {company}")

        response = tavily_client.search(
            search_depth="basic",
            include_answer=True,
            query=f"{company} engineering culture tech stack mission values",
            max_results=5
        )

        if response.get("results"):
            # Filter results by threshold score and sort by score
            threshold_score = 0.55
            
            # Filter out results below threshold
            filtered_results = [result for result in response["results"] 
            if result.get("score", 0) >= threshold_score
            ]
            
            # Sort by score in descending order
            sorted_results = sorted(filtered_results, key=lambda x: x.get("score", 0), reverse=True)

            # Get top 3 results
            top_results = sorted_results[:3]

            if top_results:
                company_data = "\n\n".join(r["content"] for r in top_results)
                return company_data
            else:
                logger.warning("Tavily returned no results")
                return ""
        return ""

    except (BadRequestError, Exception) as e:
        logger.warning(f"Tavily extract failed: {e}")
        return ""


def _groq_summarize(content: str) -> str:
    """
    Summarize raw Tavily snippets into a clean company overview via Groq.

    Sends joined snippet text to Groq with a structured system prompt that
    targets culture, engineering practices, tech stack, and values. Returns
    plain prose — no JSON, no bullet points.

    Args:
        content: Raw joined text from get_company_data.

    Returns:
        Clean 150-word company summary string.
    """

    try:
        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": COMPANY_RESEARCH_SYSTEM_PROMPT},
                {"role": "user",   "content": f"{content}"},
            ],
        )

        content = response.choices[0].message.content.strip()
        return content

    except Exception as e:
        logger.warning(f"Groq summarize failed: {e}")
        return ""


def company_research(company_name: str) -> str:
    """
    Orchestrate the full company research pipeline for a given company name.

    Calls get_company_data to fetch and filter Tavily results, then passes
    the joined content to _groq_summarize for a clean summary. Returns empty
    string if Tavily finds nothing useful — downstream agents handle this
    gracefully by omitting the company context section.

    Args:
        company_name: Company name string from the parsed JobDescription.

    Returns:
        Plain-text company summary for injection into the cover letter prompt,
        or empty string if research failed or returned low-quality results.
    """

    if not company_name or not company_name.strip():
        logger.warning("Empty company name — skipping company research")
        return ""

    company_data = get_company_data(company_name.strip())

    if not company_data:
        return ""

    company_details = _groq_summarize(company_data)
    # print(company_details)

    return company_details

