"""Agentic RAG: დაშლა -> ძიება (tool calling) -> სტრუქტურირებული პასუხი -> ვალიდაცია."""
import json
from dataclasses import dataclass, field

import psycopg

from app.llm import prompts
from app.llm.client import LLMClient, LLMError, Message
from app.llm.tools import SEARCH_TOOL, EvidenceStore, execute_tool

MAX_STEPS = 6


@dataclass
class AgentAnswer:
    status: str                      # answered | insufficient_evidence | conflict | error
    answer: str
    citations: list[int] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    missing: str = ""
    sources: list[dict] = field(default_factory=list)   # ციტირებული მტკიცებულებები
    trace: list[dict] = field(default_factory=list)     # ნაბიჯების ჟურნალი


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def decompose(llm: LLMClient, question: str) -> list[str]:
    try:
        r = llm.generate([Message("user", question)], system=prompts.DECOMPOSE_SYSTEM, json_mode=True)
        subs = _parse_json(r.text).get("sub_questions", [])
        subs = [s for s in subs if isinstance(s, str) and s.strip()][:4]
        return subs or [question]
    except LLMError:
        return [question]            # დაშლა ვერ მოხერხდა: ვაგრძელებთ თავდაპირველი კითხვით


def validate(raw: dict, store: EvidenceStore) -> AgentAnswer:
    """LLM-ის პასუხის შემოწმება ჩვენივე კოდით, მას ბრმად არ ვენდობით."""
    status = raw.get("status", "insufficient_evidence")
    if status not in ("answered", "insufficient_evidence", "conflict"):
        status = "insufficient_evidence"

    cited = [c for c in raw.get("citations", []) if isinstance(c, int) and c in store.items]
    answer = str(raw.get("answer", "")).strip()
    conflicts = [str(c) for c in raw.get("conflicts", [])]
    missing = str(raw.get("missing", ""))

    # პასუხი რეალური ციტატის გარეშე არ მიიღება
    if status == "answered" and not cited:
        status = "insufficient_evidence"
        missing = missing or "The answer could not be grounded in retrieved evidence."
    if status == "conflict" and not conflicts:
        status = "insufficient_evidence"

    sources = [{"id": n, "title": store.items[n].title, "source": store.items[n].source,
                "text": store.items[n].content} for n in cited]
    return AgentAnswer(status, answer, cited, conflicts, missing, sources)


def run_agent(conn: psycopg.Connection, question: str, llm: LLMClient | None = None,
              max_steps: int = MAX_STEPS, mode: str = "hybrid", rerank: bool = True,
              exclude_titles: frozenset[str] | None = None) -> AgentAnswer:
    llm = llm or LLMClient()
    store = EvidenceStore()
    trace: list[dict] = []

    try:
        subs = decompose(llm, question)
        trace.append({"step": "decompose", "sub_questions": subs})

        plan = "\n".join(f"{i}. {s}" for i, s in enumerate(subs, 1))
        messages = [Message("user", f"Question: {question}\n\nSuggested steps:\n{plan}")]

        for step in range(max_steps):
            r = llm.generate(messages, system=prompts.ANSWER_SYSTEM, tools=[SEARCH_TOOL])
            if not r.tool_calls:
                break
            messages.append(Message("model", r.text, raw=r.raw))
            results = []
            for call in r.tool_calls:
                out = execute_tool(conn, store, call.name, call.args, mode=mode,
                                   rerank=rerank, exclude_titles=exclude_titles)
                trace.append({"step": "search", "query": call.args.get("query"),
                              "found": [x["id"] for x in out.get("results", [])]})
                results.append((call.name, out))
            messages.append(Message("tool", tool_results=results))

        if not store.items:
            return AgentAnswer("insufficient_evidence", "", missing="No evidence was retrieved.", trace=trace)

        evidence = "\n\n".join(f"[{n}] {h.title}: {h.content}" for n, h in store.items.items())
        final = llm.generate(
            [Message("user", f"Question: {question}\n\nEvidence:\n{evidence}")],
            system=prompts.FINAL_SYSTEM, json_mode=True,
        )
        result = validate(_parse_json(final.text), store)
        result.trace = trace
        return result

    except LLMError as e:
        return AgentAnswer("error", "", missing=f"LLM unavailable: {e}", trace=trace)