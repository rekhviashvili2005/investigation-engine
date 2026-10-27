#!/usr/bin/env bash
# API შიდა პორტზე (8000), UI საჯარო პორტზე (7860)
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000 &
exec python -m streamlit run app/ui.py --server.port 7860 --server.address 0.0.0.0 \
    --server.headless true --browser.gatherUsageStats false