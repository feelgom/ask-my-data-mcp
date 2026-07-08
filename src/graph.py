"""LangGraph Multi-Agent 파이프라인.

  router ─▶ (semantic) ─▶ rag ─────────────▶ synthesize ─▶ END
         ─▶ (structured) ─▶ text2sql ───────▶ synthesize
         ─▶ (both) ───────▶ rag ─▶ text2sql ─▶ synthesize
"""
from typing import List, TypedDict

from langgraph.graph import END, StateGraph

from . import rag as rag_mod
from . import router as router_mod
from . import text2sql as t2s_mod
from .synthesize import synthesize


class State(TypedDict, total=False):
    question: str
    route: str
    retrieved: List[dict]
    sql: str
    rows: List[dict]
    answer: str


def _router(state: State) -> State:
    state["route"] = router_mod.route(state["question"])
    return state


def _rag(state: State) -> State:
    state["retrieved"] = rag_mod.search(state["question"])
    return state


def _text2sql(state: State) -> State:
    sql, rows = t2s_mod.query(state["question"])
    state["sql"], state["rows"] = sql, rows
    return state


def _synthesize(state: State) -> State:
    state["answer"] = synthesize(
        state["question"],
        state.get("route", ""),
        state.get("retrieved", []),
        state.get("rows", []),
    )
    return state


def _from_router(state: State) -> str:
    return state["route"]


def _after_rag(state: State) -> str:
    # both 는 Text2SQL 로 이어붙이고, 아니면 바로 종합
    return "text2sql" if state.get("route") == "both" else "synthesize"


def _build():
    g = StateGraph(State)
    g.add_node("router", _router)
    g.add_node("rag", _rag)
    g.add_node("text2sql", _text2sql)
    g.add_node("synthesize", _synthesize)

    g.set_entry_point("router")
    g.add_conditional_edges(
        "router", _from_router,
        {"semantic": "rag", "structured": "text2sql", "both": "rag"},
    )
    g.add_conditional_edges(
        "rag", _after_rag,
        {"text2sql": "text2sql", "synthesize": "synthesize"},
    )
    g.add_edge("text2sql", "synthesize")
    g.add_edge("synthesize", END)
    return g.compile()


_APP = None


def app():
    global _APP
    if _APP is None:
        _APP = _build()
    return _APP


def run_pipeline(question: str) -> str:
    result = app().invoke({"question": question})
    return result.get("answer", "(답변을 생성하지 못했습니다.)")
