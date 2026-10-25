import psycopg

from app.core.config import settings

with psycopg.connect(settings.database_url) as conn:
    row = conn.execute("SELECT version()").fetchone()
    print("Connected:", row[0])