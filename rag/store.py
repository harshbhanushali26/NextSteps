"""
rag/store.py
============
Module-level ChromaDB operations for CareerAgent's two-store RAG pipeline.

Two collections per job session:
    cv_skills_{job_id}  — individual skill embeddings for skill matcher
    cv_chunks_{job_id}  — CV text chunks for interview agent RAG

Both collections are deleted and recreated on new session start via
delete_session() — prevents data collision between sessions.

Public API:
    add_skills(job_id, skills, embeddings)           -> None
    add_chunks(job_id, chunks, embeddings)           -> None
    query_skills(job_id, query_embedding, n_results) -> list[dict]
    query_chunks(job_id, query_embedding, n_results) -> list[dict]
    delete_session(job_id)                           -> None
"""

import os
import logging
import numpy as np
import chromadb

from typing import List

logger = logging.getLogger(__name__)

CHROMA_PERSIST_DIR = "data/chroma_db"


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton client — created once, reused everywhere
# ─────────────────────────────────────────────────────────────────────────────

os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)


def _get_client() -> chromadb.PersistentClient:
    """Return the module-level singleton ChromaDB client."""
    return _client


def _get_collection(name: str) -> chromadb.Collection:
    """
    Get or create a ChromaDB collection by name. Internal use.

    Args:
        name: Collection name — either cv_skills_{job_id} or cv_chunks_{job_id}.

    Returns:
        ChromaDB Collection instance.
    """
    return _client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def get_collection(name: str) -> chromadb.Collection:
    """
    Public API to get a ChromaDB collection by name.

    Use this from outside the store module (e.g. interviewer.py)
    instead of importing the private _get_collection.

    Args:
        name: Collection name string.

    Returns:
        ChromaDB Collection instance.
    """
    return _get_collection(name)


def _skills_name(job_id: str) -> str:
    """Return the skills collection name for a given job_id."""
    return f"cv_skills_{job_id}"


def _chunks_name(job_id: str) -> str:
    """Return the chunks collection name for a given job_id."""
    return f"cv_chunks_{job_id}"


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def add_skills(job_id: str, skills: List[str], embeddings: np.ndarray) -> None:
    """
    Upsert CV skill strings and their embeddings into the skills collection.

    Uses deterministic IDs so re-running on the same session is idempotent.

    Args:
        job_id:     Job session identifier.
        skills:     List of skill name strings from CandidateProfile.skills.
        embeddings: np.ndarray of shape (n_skills, embedding_dim).

    Raises:
        ValueError:   If skills and embeddings lengths don't match.
        RuntimeError: If ChromaDB upsert fails.
    """
    if len(skills) != len(embeddings):
        raise ValueError(
            f"Skills ({len(skills)}) and embeddings ({len(embeddings)}) count mismatch."
        )

    collection = _get_collection(_skills_name(job_id))

    ids             = [f"skill_{i}_{s[:20].replace(' ', '_')}" for i, s in enumerate(skills)]
    embeddings_list = [e.tolist() for e in embeddings]

    try:
        collection.upsert(
            ids=ids,
            embeddings=embeddings_list,
            documents=skills,
        )
        logger.info(f"Upserted {len(skills)} skills into {_skills_name(job_id)}")
    except Exception as e:
        raise RuntimeError(f"Failed to upsert skills into ChromaDB: {e}")


def add_chunks(job_id: str, chunks: List[str], embeddings: np.ndarray) -> None:
    """
    Upsert CV text chunks and their embeddings into the chunks collection.

    Uses deterministic IDs so re-running on the same session is idempotent.

    Args:
        job_id:     Job session identifier.
        chunks:     List of CV text chunk strings.
        embeddings: np.ndarray of shape (n_chunks, embedding_dim).

    Raises:
        ValueError:   If chunks and embeddings lengths don't match.
        RuntimeError: If ChromaDB upsert fails.
    """
    if len(chunks) != len(embeddings):
        raise ValueError(
            f"Chunks ({len(chunks)}) and embeddings ({len(embeddings)}) count mismatch."
        )

    collection = _get_collection(_chunks_name(job_id))

    ids             = [f"chunk_{i}" for i in range(len(chunks))]
    embeddings_list = [e.tolist() for e in embeddings]

    try:
        collection.upsert(
            ids=ids,
            embeddings=embeddings_list,
            documents=chunks,
        )
        logger.info(f"Upserted {len(chunks)} chunks into {_chunks_name(job_id)}")
    except Exception as e:
        raise RuntimeError(f"Failed to upsert chunks into ChromaDB: {e}")


def query_skills(job_id: str, query_embedding: np.ndarray, n_results: int = 1) -> list[dict]:
    """
    Query the skills collection for the closest matching candidate skill.

    Used by skill_matcher.py — one query per JD skill to find the best
    matching candidate skill and its cosine similarity score.

    Args:
        job_id:          Job session identifier.
        query_embedding: np.ndarray of shape (embedding_dim,) — embedded JD skill.
        n_results:       Number of nearest neighbours to return (default 1).

    Returns:
        List of dicts with keys: document (skill string), score (float).
    """
    collection = _get_collection(_skills_name(job_id))

    results = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=n_results,
        include=["documents", "distances"],
    )

    output = []
    for doc, distance in zip(results["documents"][0], results["distances"][0]):
        output.append({
            "document": doc,
            "score":    1 - distance,   # cosine distance → similarity
        })

    return output


def query_chunks(job_id: str, query_embedding: np.ndarray, n_results: int = 5) -> list[dict]:
    """
    Query the chunks collection for the most relevant CV passages.

    Used by interviewer.py — queries with an embedded interview question
    to retrieve the most relevant CV context for answer scoring.

    Args:
        job_id:          Job session identifier.
        query_embedding: np.ndarray of shape (embedding_dim,) — embedded question.
        n_results:       Number of nearest chunks to return (default 5).

    Returns:
        List of dicts with keys: document (chunk string), score (float).
    """
    collection = _get_collection(_chunks_name(job_id))

    results = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=n_results,
        include=["documents", "distances"],
    )

    output = []
    for doc, distance in zip(results["documents"][0], results["distances"][0]):
        output.append({
            "document": doc,
            "score":    1 - distance,
        })

    return output


def delete_session(job_id: str) -> None:
    """
    Delete both ChromaDB collections for a given job session.

    Called at the start of each new session to prevent data collision.
    Logs a warning if a collection does not exist — never raises.

    Args:
        job_id: Job session identifier whose collections should be deleted.
    """
    client = _get_client()

    for name in [_skills_name(job_id), _chunks_name(job_id)]:
        try:
            client.delete_collection(name)
            logger.info(f"Deleted collection: {name}")
        except Exception as e:
            logger.warning(f"Could not delete collection {name}: {e}")



