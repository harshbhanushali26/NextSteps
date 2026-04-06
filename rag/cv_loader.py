"""
cv_loader.py
============
Loads a parsed CandidateProfile into ChromaDB for downstream RAG usage.

Responsibilities:
    1. Delete existing session collections — prevents data collision
    2. Embed CV skills — stored in cv_skills_{job_id} for skill matcher
    3. Embed CV text chunks — stored in cv_chunks_{job_id} for interview agent

Section-aware chunking splits raw_text on markdown headers first,
then applies character chunking with overlap within long sections.
This preserves semantic units (Experience, Education, Projects) for
better RAG retrieval quality.

Public API:
    load_cv(profile, job_id) -> None
"""

import logging

import numpy as np

from models.schemas import CandidateProfile
from rag.store import add_skills, add_chunks, delete_session

from rag.embedder import get_embedder
embedder = get_embedder()

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
MIN_CHUNK_LENGTH = 50


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────


def _split_into_sections(raw_text: str) -> list[str]:
    """
    Split markdown CV text into sections by header lines.

    Splits on lines beginning with one or more # characters.
    Each section includes its header line and all content until
    the next header. Empty sections are discarded.

    Args:
        raw_text: Full CV text in markdown format from pymupdf4llm.

    Returns:
        List of section strings, each starting with its header line.
    """

    lines    = raw_text.split("\n")
    sections = []
    current  = []

    for line in lines:
        if line.startswith("#") and current:
            section = "\n".join(current).strip()
            if section:
                sections.append(section)
            current = [line]
        else:
            current.append(line)

    # Append final section
    if current:
        section = "\n".join(current).strip()
        if section:
            sections.append(section)

    return sections


def _chunk_section(section: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Apply character chunking with overlap to a single CV section.

    Attempts to break at sentence boundaries (. ! ?) within each chunk
    window. Falls back to hard character split if no boundary is found.
    Only called when section length exceeds chunk_size.

    Args:
        section:    Section text to chunk.
        chunk_size: Maximum character length per chunk.
        overlap:    Number of characters to overlap between chunks.

    Returns:
        List of chunk strings from this section.
    """

    chunks = []
    start  = 0

    while start < len(section):
        end = start + chunk_size

        if end < len(section):
        # Find the last sentence boundary within the window
            best_end = start

            for ending in [".", "!", "?"]:
                pos =  section.rfind(ending, start, end)
                if pos > best_end:
                    best_end = pos

            # Use boundary if found, otherwise hard cut
            end = (best_end + 1) if best_end > start else end

        chunk = section[start:end].strip()
        if len(chunk) >= MIN_CHUNK_LENGTH:
            chunks.append(chunk)

        # Guard against infinite loop on very short chunks
        start = max(end - overlap, start + 1)

    return chunks


def _build_chunks(raw_text: str) -> list[str]:
    """
    Build final list of chunks from raw CV markdown text.

    Splits into sections first, then chunks any section exceeding
    CHUNK_SIZE. Short sections are kept as single chunks.

    Args:
        raw_text: Full CV text in markdown format.

    Returns:
        Flat list of chunk strings ready for embedding.
    """
    sections = _split_into_sections(raw_text)
    chunks   = []

    for section in sections:
        if len(section) > CHUNK_SIZE:
            chunks.extend(_chunk_section(section))
        else:
            if len(section) >= MIN_CHUNK_LENGTH:
                chunks.append(section)

    return chunks



# ─────────────────────────────────────────────────────────────────────────────
# Embedding functions
# ─────────────────────────────────────────────────────────────────────────────


def _embed_cv_skills(profile: CandidateProfile, job_id: str) -> None:
    """
    Embed candidate skills and store in cv_skills_{job_id} collection.

    Takes the clean skill list from CandidateProfile — no chunking needed.
    Logs a warning and returns early if skills list is empty.

    Args:
        profile: Parsed CandidateProfile with skills list.
        job_id:  Job session identifier.
    """

    skills = profile.skills

    if not skills:
        logger.warning(f"No skills found in profile for job {job_id} — skipping skill embedding")
        return

    embeddings, shape, count = embedder.generate_embeddings(skills)
    logger.info(f"Generated skill embeddings: {shape} for job {job_id}")

    add_skills(job_id, skills, embeddings)


def _embed_cv_text(profile: CandidateProfile, job_id: str) -> None:
    """
    Chunk and embed CV raw text, store in cv_chunks_{job_id} collection.

    Applies section-aware chunking to preserve semantic units from the
    markdown CV. Logs a warning and returns early if no chunks are produced.

    Args:
        profile: Parsed CandidateProfile with raw_text field.
        job_id:  Job session identifier.
    """

    chunks = _build_chunks(profile.raw_text)

    if not chunks:
        logger.warning(f"No chunks produced from CV text for job {job_id} — skipping text embedding")
        return

    embeddings, shape, count = embedder.generate_embeddings(chunks)
    logger.info(f"Generated chunk embeddings: {shape} for job {job_id}")

    add_chunks(job_id, chunks, embeddings)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def load_cv(profile: CandidateProfile, job_id: str) -> None:
    """
    Full CV loading pipeline — delete old session, embed skills and text.

    Single entry point called by the FastAPI router after CV parsing.
    Deletes existing collections for job_id first to prevent stale data,
    then runs skill embedding and text chunk embedding in sequence.

    Args:
        profile: Validated CandidateProfile from cv_parser.py.
        job_id:  Job session identifier from JobDescription.job_id.

    Raises:
        RuntimeError: If embedding or ChromaDB operations fail.
    """
    logger.info(f"Loading CV into ChromaDB for job {job_id}")

    delete_session(job_id)

    _embed_cv_skills(profile, job_id)
    _embed_cv_text(profile, job_id)

    logger.info(f"CV loading complete for job {job_id}")


