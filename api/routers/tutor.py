# """
# api/routers/tutor.py
# Phase 5 — AI Tutor + Code Coach.  Three stateless endpoints:

#   POST /tutor/chat    — Socratic tutor chat (history in body)
#   POST /tutor/problem — generate a code practice problem for a skill
#   POST /tutor/review  — score submitted code on 4 axes

# All endpoints are stateless — conversation history is passed in by the client.
# Tavily skill-context enrichment happens inside tutor.py (your agent code).
# """

# import logging
# from typing import List

# from fastapi import APIRouter, HTTPException
# from pydantic import BaseModel

# from agents.tutor import (
#     tutor_chat,
#     generate_problem,
#     review_code,
# )

# logger = logging.getLogger(__name__)
# router = APIRouter()


# # ── Request models ─────────────────────────────────────────────────────────────

# class Message(BaseModel):
#     role:    str    # "user" | "assistant"
#     content: str


# class ChatRequest(BaseModel):
#     skill:   str           # e.g. "Docker", "System Design"
#     message: str           # latest user message
#     history: List[Message] = []   # full prior conversation


# class ProblemRequest(BaseModel):
#     skill: str             # e.g. "FastAPI", "SQL joins"
#     role:  str = ""        # e.g. "Backend Engineer" — shapes difficulty/context


# class ReviewRequest(BaseModel):
#     skill:    str
#     problem:  str          # the problem statement that was given
#     code:     str          # code the candidate submitted
#     language: str = "python"


# # ── Endpoints ──────────────────────────────────────────────────────────────────

# @router.post("/chat")
# def chat_with_tutor(body: ChatRequest):
#     """
#     Socratic tutor chat.
#     The tutor asks guiding questions — it does NOT lecture.
#     Tavily enriches context for the skill before each response.
#     History is the full conversation so far; the new message is appended server-side
#     before the Groq call, so the response stays contextually grounded.

#     Returns:
#       {
#         "response": "That's a good start! Can you tell me why you'd use ...",
#         "skill":    "Docker"
#       }
#     """
#     try:
#         logger.info("Tutor chat — skill=%s, history_len=%d", body.skill, len(body.history))
#         history_dicts = [m.model_dump() for m in body.history]
#         response = tutor_chat(
#             skill=body.skill,
#             message=body.message,
#             history=history_dicts,
#         )
#         return {
#             "response": response,
#             "skill":    body.skill,
#         }
#     except Exception as e:
#         logger.exception("Tutor chat failed")
#         raise HTTPException(status_code=500, detail=f"Tutor chat failed: {str(e)}")


# @router.post("/problem")
# def get_practice_problem(body: ProblemRequest):
#     """
#     Generate a code practice problem for a given skill + role.
#     Difficulty and framing are shaped by the candidate's target role.

#     Returns:
#       {
#         "problem":      "Write a function that ...",
#         "hints":        ["Think about edge cases ...", "Consider time complexity ..."],
#         "skill":        "SQL joins",
#         "starter_code": "def solve(...):\n    pass"   # optional
#       }
#     """
#     try:
#         logger.info("Generating problem — skill=%s, role=%s", body.skill, body.role)
#         result = generate_problem(skill=body.skill, role=body.role)
#         return {
#             **result,
#             "skill": body.skill,
#         }
#     except Exception as e:
#         logger.exception("Problem generation failed")
#         raise HTTPException(status_code=500, detail=f"Problem generation failed: {str(e)}")


# @router.post("/review")
# def review_submitted_code(body: ReviewRequest):
#     """
#     Score submitted code on 4 axes: correctness, efficiency, readability, best_practices.
#     Each axis scored 0.0 – 1.0. Feedback is actionable.

#     Returns:
#       {
#         "scores": {
#           "correctness":     0.9,
#           "efficiency":      0.7,
#           "readability":     0.85,
#           "best_practices":  0.8
#         },
#         "overall":   0.81,
#         "feedback":  "Your solution is correct. Consider using a dict instead of ...",
#         "suggestion": "Revised version: ..."   # optional improved snippet
#       }
#     """
#     try:
#         logger.info(
#             "Reviewing code — skill=%s, lang=%s, code_len=%d",
#             body.skill, body.language, len(body.code),
#         )
#         result = review_code(
#             skill=body.skill,
#             problem=body.problem,
#             code=body.code,
#             language=body.language,
#         )
#         return result
#     except Exception as e:
#         logger.exception("Code review failed")
#         raise HTTPException(status_code=500, detail=f"Code review failed: {str(e)}")