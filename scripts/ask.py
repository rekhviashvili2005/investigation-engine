import sys

from app.db.connection import get_connection
from app.llm.agent import run_agent

question = " ".join(sys.argv[1:])
with get_connection() as conn:
    a = run_agent(conn, question)

print("STATUS:", a.status)
print("ANSWER:", a.answer)
if a.conflicts:
    print("CONFLICTS:", a.conflicts)
if a.missing:
    print("MISSING:", a.missing)
for s in a.sources:
    print(f"  [{s['id']}] {s['title']}: {s['text'][:100]}...")
print("TRACE:", a.trace)