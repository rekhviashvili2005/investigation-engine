# """Streamlit UI: კითხვა-პასუხი, დოკუმენტების ატვირთვა და მართვა.
#
# გაშვება (API უკვე გაშვებული უნდა იყოს):
#     python -m streamlit run app/ui.py
# """
# import os
#
# import httpx
# import streamlit as st
#
# API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")
# TIMEOUT = 120.0
#
# st.set_page_config(page_title="AI Investigation Engine", layout="wide")
# st.title("AI Investigation Engine")
#
# tab_ask, tab_docs = st.tabs(["Ask", "Documents"])
#
#
# def api(method: str, path: str, **kwargs):
#     """ერთიანი გამოძახება: შეცდომებს ადამიანურად აჩვენებს."""
#     try:
#         r = httpx.request(method, f"{API_URL}{path}", timeout=TIMEOUT, **kwargs)
#         if r.status_code >= 400:
#             detail = r.json().get("detail", r.text) if r.headers.get("content-type", "").startswith("application/json") else r.text
#             st.error(f"Error {r.status_code}: {detail}")
#             return None
#         return r.json()
#     except httpx.HTTPError as e:
#         st.error(f"API unavailable: {type(e).__name__}")
#         return None
#
#
# STATUS_LABEL = {
#     "answered": "✅ Answered",
#     "insufficient_evidence": "⚠️ Insufficient evidence",
#     "conflict": "⚡ Conflicting sources",
# }
#
# with tab_ask:
#     question = st.text_area("Your question", height=100,
#                             placeholder="e.g. Which Cloudflare incidents were caused by a configuration change?")
#     mode = st.selectbox("Search mode", ["hybrid", "dense", "bm25"])
#     if st.button("Ask", type="primary", disabled=len(question.strip()) < 3):
#         with st.spinner("Searching and reasoning..."):
#             res = api("POST", "/ask", json={"question": question, "mode": mode})
#         if res:
#             st.subheader(STATUS_LABEL.get(res["status"], res["status"]))
#             if res["answer"]:
#                 st.write(res["answer"])
#             if res["conflicts"]:
#                 st.warning("Conflicts found:")
#                 for c in res["conflicts"]:
#                     st.write(f"- {c}")
#             if res["missing"]:
#                 st.info(f"Missing: {res['missing']}")
#             if res["sources"]:
#                 st.markdown("#### Sources")
#                 for s in res["sources"]:
#                     with st.expander(f"[{s['id']}] {s['title']}"):
#                         st.caption(s["source"])
#                         st.write(s["text"])
#             with st.expander("Reasoning trace"):
#                 st.json(res["trace"])
#
# with tab_docs:
#     st.subheader("Upload")
#     strategy = st.selectbox("Chunking strategy", ["sentence", "fixed"])
#     up = st.file_uploader("File (txt, md, html, pdf, json)", type=["txt", "md", "html", "htm", "pdf", "json"])
#     if up and st.button("Ingest"):
#         with st.spinner("Processing..."):
#             res = api("POST", f"/documents?strategy={strategy}",
#                       files={"file": (up.name, up.getvalue())})
#         if res:
#             for r in res:
#                 st.success(f"{r['status']}: document {r['document_id']}, {r['chunks']} chunks")
#
#     st.subheader("Your documents")
#     docs = api("GET", "/documents")
#     if docs:
#         st.dataframe(docs, use_container_width=True)
#         del_id = st.selectbox("Delete document", [d["id"] for d in docs],
#                               format_func=lambda i: next(f"{d['id']}: {d['title'][:50]}" for d in docs if d["id"] == i))
#         if st.button("Delete"):
#             if api("DELETE", f"/documents/{del_id}"):
#                 st.success("Deleted")
#                 st.rerun()
#     elif docs == []:
#         st.caption("No uploaded documents yet.")


"""Streamlit UI: პირდაპირ იყენებს ჩვენს მოდულებს (ერთი პროცესი, ნაკლები მეხსიერება).

გაშვება:  python -m streamlit run app/ui.py
"""
import tempfile
from pathlib import Path

import streamlit as st

from app.db import repository as repo
from app.db.connection import get_connection
from app.ingestion.parsers import PARSERS, parse_file
from app.ingestion.pipeline import ingest_document
from app.llm.agent import run_agent

MAX_UPLOAD_BYTES = 5 * 1024 * 1024

st.set_page_config(page_title="AI Investigation Engine", layout="wide")
st.title("AI Investigation Engine")

tab_ask, tab_docs = st.tabs(["Ask", "Documents"])

STATUS_LABEL = {
    "answered": "✅ Answered",
    "insufficient_evidence": "⚠️ Insufficient evidence",
    "conflict": "⚡ Conflicting sources",
}

with tab_ask:
    question = st.text_area("Your question", height=100,
                            placeholder="e.g. Which Cloudflare incidents were caused by a configuration change?")
    mode = st.selectbox("Search mode", ["hybrid", "dense", "bm25"])
    if st.button("Ask", type="primary", disabled=len(question.strip()) < 3):
        with st.spinner("Searching and reasoning..."):
            try:
                with get_connection() as conn:
                    a = run_agent(conn, question, mode=mode, rerank=False)
            except Exception as e:
                st.error(f"Error: {type(e).__name__}")
                a = None
        if a and a.status == "error":
            st.error(a.missing)
        elif a:
            st.subheader(STATUS_LABEL.get(a.status, a.status))
            if a.answer:
                st.write(a.answer)
            if a.conflicts:
                st.warning("Conflicts found:")
                for c in a.conflicts:
                    st.write(f"- {c}")
            if a.missing:
                st.info(f"Missing: {a.missing}")
            if a.sources:
                st.markdown("#### Sources")
                for s in a.sources:
                    with st.expander(f"[{s['id']}] {s['title']}"):
                        st.caption(s["source"])
                        st.write(s["text"])
            with st.expander("Reasoning trace"):
                st.json(a.trace)

with tab_docs:
    st.subheader("Upload")
    strategy = st.selectbox("Chunking strategy", ["sentence", "fixed"])
    up = st.file_uploader("File (txt, md, html, pdf, json)",
                          type=[e.lstrip(".") for e in PARSERS])
    if up and st.button("Ingest"):
        if up.size > MAX_UPLOAD_BYTES:
            st.error("File too large (max 5 MB)")
        else:
            with st.spinner("Processing..."):
                try:
                    with tempfile.TemporaryDirectory() as tmp:
                        path = Path(tmp) / Path(up.name).name
                        path.write_bytes(up.getvalue())
                        docs = parse_file(path)
                    with get_connection() as conn:
                        for doc in docs:
                            doc.source = f"upload://{up.name}" + (
                                f"#{doc.source.split('#')[-1]}" if len(docs) > 1 else "")
                            r = ingest_document(conn, doc, strategy=strategy)
                            st.success(f"{r.status}: document {r.document_id}, {r.chunks} chunks")
                except Exception as e:
                    st.error(f"Could not process file: {type(e).__name__}")

    st.subheader("Your documents")
    with get_connection() as conn:
        docs = [d for d in repo.list_documents(conn) if d["source"].startswith("upload://")]
    if docs:
        st.dataframe(docs, use_container_width=True)
        del_id = st.selectbox("Delete document", [d["id"] for d in docs],
                              format_func=lambda i: next(f"{d['id']}: {d['title'][:50]}" for d in docs if d["id"] == i))
        if st.button("Delete"):
            with get_connection() as conn:
                repo.delete_document(conn, del_id)
                conn.commit()
            st.success("Deleted")
            st.rerun()
    else:
        st.caption("No uploaded documents yet.")