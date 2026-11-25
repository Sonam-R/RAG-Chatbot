"""Graph builder for the RAG pipeline.

Compiled once at import time (`rag_graph`). Guardrail nodes are included only when
their settings flags are enabled so the baseline path stays unchanged.
"""

from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import StateGraph, START, END
from app.core.config import settings
from .state import RAGState
from . import nodes


def _rag_entry(state: Dict[str, Any]) -> str:
    """After optional input guard: plain chat vs document RAG."""
    return "plain_chat" if not state.get("use_documents", True) else "rewrite"


def _after_input_guard(state: Dict[str, Any]) -> str:
    if state.get("input_blocked"):
        return "__end__"
    return _rag_entry(state)


def _after_retrieve(state: Dict[str, Any]) -> str:
    if not state.get("hits"):
        return "refuse"
    if settings.enable_relevance_grading:
        return "grade"
    return "generate"


def _after_grade(state: Dict[str, Any]) -> str:
    if state.get("relevant"):
        return "generate"
    retries = state.get("retries", 0)
    if retries < settings.max_retrieval_retries:
        return "rewrite"
    return "refuse"


def build_graph() -> StateGraph:
    graph = StateGraph(RAGState)

    graph.add_node("plain_chat", nodes.plain_chat)
    graph.add_node("rewrite", nodes.rewrite)
    graph.add_node("retrieve", nodes.retrieve)
    graph.add_node("generate", nodes.generate)
    graph.add_node("refuse", nodes.refuse)

    if settings.enable_input_guard:
        graph.add_node("input_guard", nodes.input_guard)
        graph.add_conditional_edges(
            START,
            lambda _state: "input_guard",
            {"input_guard": "input_guard"},
        )
        graph.add_conditional_edges(
            "input_guard",
            _after_input_guard,
            {
                "plain_chat": "plain_chat",
                "rewrite": "rewrite",
                "__end__": END,
            },
        )
    else:
        graph.add_conditional_edges(
            START,
            _rag_entry,
            {
                "plain_chat": "plain_chat",
                "rewrite": "rewrite",
            },
        )

    graph.add_edge("rewrite", "retrieve")

    grade_targets: dict[str, str] = {
        "generate": "generate",
        "refuse": "refuse",
    }
    if settings.enable_relevance_grading:
        graph.add_node("grade", nodes.grade)
        grade_targets["grade"] = "grade"
        graph.add_conditional_edges(
            "retrieve",
            _after_retrieve,
            grade_targets,
        )
        graph.add_conditional_edges(
            "grade",
            _after_grade,
            {
                "generate": "generate",
                "rewrite": "rewrite",
                "refuse": "refuse",
            },
        )
    else:
        graph.add_conditional_edges(
            "retrieve",
            _after_retrieve,
            grade_targets,
        )

    if settings.enable_output_check:
        graph.add_node("output_check", nodes.output_check)
        graph.add_edge("generate", "output_check")
        graph.add_edge("output_check", END)
    else:
        graph.add_edge("generate", END)

    graph.add_edge("refuse", END)
    graph.add_edge("plain_chat", END)

    return graph.compile()


rag_graph = build_graph()