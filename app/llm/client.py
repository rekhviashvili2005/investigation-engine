"""Gemini-ს გარსი: retry, timeout და შეცდომების ერთიანი ტიპები.

agent ამ მოდულის ტიპებს იყენებს (Message, ToolSpec, LLMResponse) და SDK-ს არ იცნობს.
"""
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from google import genai
from google.genai import errors, types

from app.core.config import settings

RETRYABLE_CODES = {429, 500, 502, 503, 504}


class LLMError(Exception):
    """LLM-თან კომუნიკაციის საბოლოო შეცდომა (retry-ების შემდეგ)."""


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict          # JSON schema


@dataclass
class ToolCall:
    name: str
    args: dict


@dataclass
class Message:
    role: str                 # "user" | "model" | "tool"
    text: str = ""
    tool_results: list[tuple[str, dict]] = field(default_factory=list)  # (tool_name, result)
    raw: Any = None           # model-ის ორიგინალი პასუხი, უცვლელად ბრუნდება უკან


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[ToolCall]
    raw: Any = None


def with_retry(fn: Callable[[], Any], max_attempts: int = 4, base_delay: float = 2.0,
               sleep: Callable[[float], None] = time.sleep) -> Any:
    """ლიმიტზე (429) და სერვერის დროებით შეცდომებზე ვცდილობთ ხელახლა,
    ექსპონენციალური პაუზით: 2s, 4s, 8s. სხვა შეცდომა მაშინვე ითვლება საბოლოოდ."""
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except errors.APIError as e:
            code = getattr(e, "code", None)
            if code in RETRYABLE_CODES and attempt < max_attempts:
                sleep(base_delay * 2 ** (attempt - 1))
                continue
            raise LLMError(f"LLM request failed (code={code}): {e}") from e
        except (TimeoutError, ConnectionError) as e:
            if attempt < max_attempts:
                sleep(base_delay * 2 ** (attempt - 1))
                continue
            raise LLMError(f"LLM connection failed: {e}") from e


def _to_content(m: Message) -> types.Content:
    if m.raw is not None:                       # model-ის წინა პასუხი უცვლელად
        return m.raw
    if m.role == "tool":
        parts = [types.Part.from_function_response(name=n, response=r) for n, r in m.tool_results]
        return types.Content(role="user", parts=parts)
    return types.Content(role=m.role, parts=[types.Part.from_text(text=m.text)])


class LLMClient:
    def __init__(self, api_key: str | None = None, model: str | None = None,
                 timeout_s: int = 60, temperature: float = 0.0):
        self.model = model or settings.llm_model
        self.temperature = temperature
        self._client = genai.Client(
            api_key=api_key or settings.llm_api_key,
            http_options=types.HttpOptions(timeout=timeout_s * 1000),   # მილიწამებში
        )

    def generate(self, messages: list[Message], system: str = "",
                 tools: list[ToolSpec] | None = None, json_mode: bool = False) -> LLMResponse:
        config = types.GenerateContentConfig(
            system_instruction=system or None,
            temperature=self.temperature,
            response_mime_type="application/json" if json_mode else None,
            tools=[types.Tool(function_declarations=[
                types.FunctionDeclaration(name=t.name, description=t.description, parameters=t.parameters)
                for t in tools
            ])] if tools else None,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        contents = [_to_content(m) for m in messages]

        resp = with_retry(lambda: self._client.models.generate_content(
            model=self.model, contents=contents, config=config))

        calls = [ToolCall(fc.name, dict(fc.args or {})) for fc in (resp.function_calls or [])]
        try:
            text = resp.text or ""
        except Exception:        # როცა პასუხში მხოლოდ function call არის, .text შეიძლება ცარიელი იყოს
            text = ""
        raw = resp.candidates[0].content if resp.candidates else None
        return LLMResponse(text=text, tool_calls=calls, raw=raw)