"""Graph builder for the RAG pipeline.

The graph is compiled once at import time (module‑level singleton `rag_graph`).
It wires the async node functions defined in `app.graph.nodes` together and
adds the optional relevance‑grading node behind the `settings.enable_relevance_grading`
feature flag.

All edges use the `Dict[str, Any]` state (`RAGState`).  The graph follows the
exact flow of the original `chat` endpoint, so the observable behaviour is
unchanged when the flag is off.
"""

from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import StateGraph, START, END
from app.core.config import settings
from .state import RAGState
from . import nodes


def _after_retrieve(state: Dict[str, Any]) -> str:
    """Decide where to go after the `retrieve` node.

    * If no hits → ``refuse``.
    * If the relevance‑grading flag is enabled → ``grade``.
    * Otherwise → ``generate``.
    """
    if not state.get("hits"):
        return "refuse"
    if settings.enable_relevance_grading:
        return "grade"
    return "generate"


def _after_grade(state: Dict[str, Any]) -> str:
    """Decision logic after the optional ``grade`` node.

    * ``state["relevant"]`` True → ``generate``.
    * Not relevant and we have retries left → ``rewrite`` (retry).
    * Not relevant and retries exhausted → ``refuse``.
    """
    if state.get("relevant"):
        return "generate"
    # increment retry count (state["retries"] may be missing on first pass)
    retries = state.get("retries", 0) + 1
    state["retries"] = retries
    if retries < settings.max_retrieval_retries:
        return "rewrite"
    return "refuse"


def build_graph() -> StateGraph:
    """Create and compile the RAG `StateGraph`.

    The graph is a singleton; call this function once at import time.
    """
    graph = StateGraph(RAGState)

    # ------------------------------------------------------------------
    # Nodes
    # ------------------------------------------------------------------
    graph.add_node("plain_chat", nodes.plain_chat)
    graph.add_node("rewrite", nodes.rewrite)
    graph.add_node("retrieve", nodes.retrieve)
    graph.add_node("generate", nodes.generate)
    graph.add_node("refuse", nodes.refuse)
    if settings.enable_relevance_grading:
        graph.add_node("grade", nodes.grade)

    # ------------------------------------------------------------------
    # Conditional edge from START based on the `use_documents` flag
    # ------------------------------------------------------------------
    def _start_branch(state: Dict[str, Any]) -> str:
        return "plain_chat" if not state.get("use_documents", True) else "rewrite"

    graph.add_conditional_edges(
        START,
        _start_branch,
        {
            "plain_chat": "plain_chat",
            "rewrite": "rewrite",
        },
    )

    # rewrite -> retrieve
    graph.add_edge("rewrite", "retrieve")

    # retrieve -> generate / refuse / grade (conditional)
    graph.add_conditional_edges(
        "retrieve",
        _after_retrieve,
        {
            "generate": "generate",
            "refuse": "refuse",
            "grade": "grade",
        },
    )

    # If grading is enabled, add the grade conditional edges
    if settings.enable_relevance_grading:
        graph.add_conditional_edges(
            "grade",
            _after_grade,
            {
                "generate": "generate",
                "rewrite": "rewrite",
                "refuse": "refuse",
            },
        )

    # Terminal edges
    graph.add_edge("generate", END)
    graph.add_edge("refuse", END)
    graph.add_edge("plain_chat", END)

    compiled = graph.compile()
    return compiled

# Compile once – the module variable is imported by the FastAPI route.
rag_graph = build_graph()
