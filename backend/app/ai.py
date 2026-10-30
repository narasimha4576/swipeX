import json
import os
import re

import httpx
from dotenv import load_dotenv

load_dotenv()


class AIUnavailable(Exception):
    """The AI is not set up, busy, or could not be reached."""


def is_configured() -> bool:
    return bool(os.getenv("AI_API_KEY") and os.getenv("AI_MODEL"))


def extract_json(text: str) -> dict | None:
    text = (text or "").strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.S)
    if fenced:
        text = fenced.group(1)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return data if isinstance(data, dict) else None


def _provider_message(response: httpx.Response) -> str:
    try:
        error = response.json().get("error")
        message = error.get("message") if isinstance(error, dict) else str(error or "")
    except Exception:
        message = response.text
    return (message or "").strip().replace("\n", " ")[:200]


def _post(base: str, body: dict) -> httpx.Response:
    return httpx.post(
        f"{base}/chat/completions",
        headers={"Authorization": "Bearer " + os.getenv("AI_API_KEY", "")},
        json=body,
        timeout=60,
    )


def complete(
    system: str,
    user: str | None = None,
    *,
    messages: list[dict] | None = None,
    json_mode: bool = False,
    max_tokens: int = 700,
    temperature: float = 0.2,
) -> str:
    if not is_configured():
        raise AIUnavailable("AI is not set up. Add AI_API_KEY and AI_MODEL to backend/.env")

    base = (os.getenv("AI_BASE_URL") or "https://api.groq.com/openai/v1").rstrip("/")
    model = os.getenv("AI_MODEL", "")
    chat = [{"role": "system", "content": system}] + (
        messages or [{"role": "user", "content": user or ""}]
    )
    plain = {"model": model, "messages": chat, "temperature": temperature, "max_tokens": max_tokens}
    body = dict(plain)
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    if "gpt-oss" in model.lower():
        body["reasoning_effort"] = "low"

    try:
        response = _post(base, body)
        if response.status_code == 400 and body != plain:
            response = _post(base, plain)
    except httpx.HTTPError as exc:
        raise AIUnavailable("Could not reach the AI service. Check your internet connection.") from exc

    status = response.status_code
    if status == 429:
        raise AIUnavailable("The AI service is busy (free limit reached). Try again in a minute.")
    if status in (401, 403):
        raise AIUnavailable("The AI key was refused. Check AI_API_KEY in backend/.env, then restart the backend.")
    if status == 404:
        raise AIUnavailable("The AI model name was not found. Run python backend\\pick_ai_model.py, then restart the backend.")
    if status >= 400:
        raise AIUnavailable(f"The AI service returned an error ({status}): {_provider_message(response)}")

    try:
        content = response.json()["choices"][0]["message"].get("content") or ""
    except (KeyError, IndexError, ValueError) as exc:
        raise AIUnavailable("The AI service sent an answer SwipeX could not read.") from exc
    if not content.strip():
        raise AIUnavailable("The AI returned an empty answer. Try again.")
    return content.strip()