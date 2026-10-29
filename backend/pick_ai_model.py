# Finds a chat model that your AI key can use today and saves it in backend/.env.
import os
import re
from pathlib import Path

import httpx
from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_FILE)

# Models that are not for chat (speech, safety filters, embeddings, tool systems)
SKIP = re.compile(r"whisper|tts|playai|guard|safeguard|embed|orpheus|compound|moderation", re.I)
# Roughly the order we would like to try them in
PREFER = ["llama-3.3-70b", "gpt-oss-120b", "llama-4", "gpt-oss-20b", "qwen", "llama-3.1-8b", "gemma", "llama"]


def rank(model_id: str) -> int:
    lowered = model_id.lower()
    for position, word in enumerate(PREFER):
        if word in lowered:
            return position
    return len(PREFER)


def works(base: str, headers: dict, model: str) -> bool:
    try:
        response = httpx.post(
            base + "/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Say hi in two words."}],
                "max_tokens": 16,
            },
            timeout=30,
        )
    except httpx.HTTPError:
        return False
    # 429 means the name is valid but the free limit is busy right now
    return response.status_code in (200, 429)


def save_model(model: str) -> None:
    text = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
    if re.search(r"(?m)^AI_MODEL=.*$", text):
        text = re.sub(r"(?m)^AI_MODEL=.*$", "AI_MODEL=" + model, text)
    else:
        text += "\nAI_MODEL=" + model + "\n"
    ENV_FILE.write_text(text, encoding="utf-8")


def main() -> None:
    key = os.getenv("AI_API_KEY")
    base = (os.getenv("AI_BASE_URL") or "https://api.groq.com/openai/v1").rstrip("/")
    if not key:
        print("Put your key right after AI_API_KEY= in backend/.env, save, and run this again.")
        return

    headers = {"Authorization": "Bearer " + key}
    try:
        response = httpx.get(base + "/models", headers=headers, timeout=30)
    except httpx.HTTPError as exc:
        print("Could not reach the AI service:", exc)
        return
    if response.status_code in (401, 403):
        print("The key was refused. Check AI_API_KEY in backend/.env (no spaces or quotes).")
        return
    response.raise_for_status()

    models = sorted({m["id"] for m in response.json().get("data", []) if not SKIP.search(m["id"])})
    if not models:
        print("The service returned no chat models for this key.")
        return

    print("Chat models your key can use right now:")
    for model in models:
        print("  " + model)

    print("\nTrying the best ones...")
    for model in sorted(models, key=rank)[:6]:
        if works(base, headers, model):
            save_model(model)
            print(f"\n{model} works. Saved AI_MODEL={model} in backend/.env")
            print("Now run:  python backend\\test_ai.py")
            return
        print(f"  {model} did not work")

    print("\nNone of the first six worked. Copy a name from the list above into AI_MODEL= by hand.")


if __name__ == "__main__":
    main()