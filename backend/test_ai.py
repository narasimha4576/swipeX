from app.ai import AIUnavailable, complete, is_configured


def main() -> None:
    if not is_configured():
        print("AI is not set up yet. Put your key after AI_API_KEY= in backend/.env and save.")
        return
    try:
        reply = complete(
            "You are a friendly assistant. Answer in one short sentence.",
            "Say hello to a job seeker who uses the SwipeX app.",
        )
        print("AI replied:", reply)
    except AIUnavailable as exc:
        print("AI problem:", exc)


if __name__ == "__main__":
    main()