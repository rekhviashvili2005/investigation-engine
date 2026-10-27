FROM python:3.12-slim

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH" \
    HOME=/home/user \
    FASTEMBED_CACHE_PATH=/home/user/.cache/fastembed \
    OMP_NUM_THREADS=1 \
    PYTHONUNBUFFERED=1

WORKDIR /home/user/app
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user . .

# embedding მოდელი build-ის დროს, რომ გაშვება სწრაფი იყოს
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"

# Render აწვდის PORT-ს; ნაგულისხმევად 10000
CMD ["sh", "-c", "python -m streamlit run app/ui.py --server.port ${PORT:-10000} --server.address 0.0.0.0 --server.headless true --browser.gatherUsageStats false"]