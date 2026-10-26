from app.db.connection import get_connection

with get_connection() as conn:
    rows = conn.execute(
        """SELECT split_part(d.source, '://', 1) AS kind,
                  count(DISTINCT d.id) AS docs,
                  count(c.id)          AS chunks
           FROM documents d LEFT JOIN chunks c ON c.document_id = d.id
           GROUP BY kind ORDER BY kind"""
    ).fetchall()
    for kind, docs, chunks in rows:
        print(f"{kind:12} documents={docs:6}  chunks={chunks}")