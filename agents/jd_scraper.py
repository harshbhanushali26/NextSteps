"""
jd_scraper.py
=============
Scrapes a job listing URL and returns a structured JobDescription.

Primary path : Tavily extract  (clean text, no JS headaches)
Fallback path : requests + bs4 (silent, fires only if Tavily fails / < 200 chars)

Design rules:
    - Every external call wrapped in try/except → logs warning, never raises
    - job_id  = md5(url)[:12]  injected locally before model_validate
    - raw_text = full scrape stored on model (for RAG)
    - Only 4 000 chars sent to Groq (truncated)
    - url + job_id injected locally, Groq never sees them
"""

import os
import hashlib
import logging
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from tavily import TavilyClient, BadRequestError

from models.schemas import JobDescription
from prompts.jd_scraper_prompt import JD_SCRAPER_SYSTEM_PROMPT
from utils.llm import get_groq_client, parse_json_response


load_dotenv()
logger = logging.getLogger(__name__)

groq_client   = get_groq_client()
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def generate_job_id(url: str) -> str:
    """
    Generate a deterministic 12-character job ID from the posting URL.

    Uses MD5 so the same URL always produces the same ID — safe to call
    multiple times without creating duplicates in the job store.

    Args:
        url: The job posting URL.

    Returns:
        First 12 hex characters of the MD5 hash of the URL.
    """
    return hashlib.md5(url.encode()).hexdigest()[:12]


def _tavily_extract(job_url: str) -> str:
    """
    Attempt to extract job description text via Tavily's extract endpoint.

    Sends a structured query to Tavily and returns the raw content if it
    meets the minimum length threshold (200 chars). Falls back gracefully
    on any error — including bad URLs, rate limits, or API failures.

    Args:
        job_url: The job posting URL to extract from.

    Returns:
        Cleaned text string if extraction succeeded, empty string otherwise.
    """
    try:
        logger.info(f"Extracting JD with Tavily: {job_url}")

        response = tavily_client.extract(
            urls=job_url,
            extract_depth="basic",
            query=(
                "Extract the full job title, company name, location, "
                "key responsibilities, required skills, nice-to-have skills, "
                "and the complete job description."
            ),
        )

        if response.get("results"):
            result   = response["results"][0]
            raw_text = result.get("raw_content", "") or result.get("markdown", "")

            if len(raw_text.strip()) >= 200:
                return raw_text.strip()

            logger.warning("Tavily returned content < 200 chars — falling back")

        else:
            logger.warning("Tavily returned no results — falling back")

    except (BadRequestError, Exception) as e:
        logger.warning(f"Tavily extract failed: {e} — falling back to bs4")

    return ""


def _bs4_extract(job_url: str) -> str:
    """
    Fallback extraction using requests and BeautifulSoup.

    Strips noise tags (script, style, nav, footer, header) before extracting
    text. Only called when Tavily fails or returns insufficient content.

    Args:
        job_url: The job posting URL to scrape.

    Returns:
        Cleaned plain text from the page, or empty string on any failure.
    """
    try:
        logger.info(f"Extracting JD with bs4 fallback: {job_url}")
        headers = {"User-Agent": "Mozilla/5.0 (compatible; CareerAgent/1.0)"}

        resp = requests.get(job_url, headers=headers, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        return soup.get_text(separator="\n", strip=True)

    except Exception as e:
        logger.warning(f"bs4 fallback also failed: {e}")
        return ""


def _fetch_text(job_url: str) -> str:
    """
    Orchestrate the two-stage fetch: Tavily first, bs4 fallback second.

    Never raises — if both paths fail, returns empty string and lets
    the caller (scrape_jd) raise the appropriate ValueError.

    Args:
        job_url: The job posting URL to fetch text from.

    Returns:
        Raw text string from whichever path succeeded, or empty string.
    """
    text = _tavily_extract(job_url)
    if not text:
        text = _bs4_extract(job_url)
    return text


def _extract_with_groq(raw_text: str, url: str) -> dict:
    """
    Send truncated job description text to Groq and parse the JSON response.

    Truncates input to 4 000 characters before sending to stay within token
    limits. Strips accidental markdown fences from the response before
    parsing. url is included in the user message as context for the model.

    Args:
        raw_text: Full scraped text from the job posting page.
        url:      Original job posting URL, passed as context to Groq.

    Returns:
        Parsed dict matching the JD_SCRAPER_SYSTEM_PROMPT JSON schema.

    Raises:
        json.JSONDecodeError: If Groq returns malformed JSON.
    """
    truncated = raw_text[:4000]

    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": JD_SCRAPER_SYSTEM_PROMPT},
            {"role": "user",   "content": f"Job URL: {url}\n\n---\n\n{truncated}"},
        ],
    )

    content = response.choices[0].message.content.strip()
    return parse_json_response(content)


def scrape_jd(url: str) -> JobDescription:
    """
    Scrape and parse a job listing URL into a structured JobDescription.

    Orchestrates the full pipeline: fetch raw text → extract with Groq →
    inject local fields → validate against schema. url, job_id, and raw_text
    are injected after Groq extraction so the model never needs to produce them.

    Args:
        url: The job posting URL to scrape.

    Returns:
        Validated JobDescription instance.

    Raises:
        ValueError:            If both Tavily and bs4 return empty text.
        json.JSONDecodeError:  If Groq returns malformed JSON.
        ValidationError:       If the parsed data doesn't match JobDescription.
    """
    raw_text = _fetch_text(url)

    if not raw_text:
        raise ValueError(
            f"Could not fetch job description from: {url}\n"
            "Both Tavily extract and bs4 fallback returned empty text."
        )

    data = _extract_with_groq(raw_text, url)

    data["url"]      = url
    data["job_id"]   = generate_job_id(url)
    data["raw_text"] = raw_text

    # Flag empty skill extraction so frontend can warn the user
    required = data.get("required_skills") or []
    nice     = data.get("nice_to_have") or []
    if not required and not nice:
        logger.warning("Groq extracted zero skills from JD — URL: %s", url)
        data["skills_extraction_warning"] = True
    else:
        data["skills_extraction_warning"] = False


    return JobDescription.model_validate(data)

