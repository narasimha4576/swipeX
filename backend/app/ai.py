# One small helper for every AI feature. It works with any OpenAI-compatible service
# (Groq, Google Gemini, OpenRouter, a local Ollama...). Settings come from backend/.env.
import os

import httpx
from dotenv import load_dotenv

load_dotenv()


class AIUnavailable(Exception):
    """The AI is not set up, busy, or could not be reached."""


def is_configured() -> bool:
    return bool(os.getenv("AI_API_KEY") and os.getenv("AI_MODEL"))


def complete(
    system: str,
    user: str,
    *,
    json_mode: bool = False,
    max_tokens: int = 600,
    temperature: float = 0.2,
) -> str:
    if not is_configured():
        raise AIUnavailable("AI is not set up. Add AI_API_KEY and AI_MODEL to backend/.env")

    base = (os.getenv("AI_BASE_URL") or "https://api.groq.com/openai/v1").rstrip("/")
    body = {
        "model": os.getenv("AI_MODEL"),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    try:
        response = httpx.post(
            f"{base}/chat/completions",
            headers={"Authorization": "Bearer " + os.getenv("AI_API_KEY", "")},
            json=body,
            timeout=45,
        )
    except httpx.HTTPError as exc:
        raise AIUnavailable("Could not reach the AI service. Check your internet connection.") from exc

    if response.status_code == 429:
        raise AIUnavailable("The AI service is busy (free limit reached). Try again in a minute.")
    if response.status_code in (401, 403):
        raise AIUnavailable("The AI key was refused. Check AI_API_KEY in backend/.env.")
    if response.status_code == 404:
        raise AIUnavailable("The AI model name was not found. Check AI_MODEL in backend/.env.")
    if response.status_code >= 400:
        raise AIUnavailable(f"The AI service returned an error ({response.status_code}).")

    data = response.json()
    return (data["choices"][0]["message"]["content"] or "").strip()