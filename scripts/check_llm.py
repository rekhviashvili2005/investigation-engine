from google import genai

from app.core.config import settings

client = genai.Client(api_key=settings.llm_api_key)
resp = client.models.generate_content(
    model=settings.llm_model,
    contents="Reply with one word: ready",
)
print(resp.text)