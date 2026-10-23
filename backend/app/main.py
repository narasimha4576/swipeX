from fastapi import FastAPI

app = FastAPI(title="SwipeX API")


@app.get("/health")
def health():
    return {"status": "ok", "service": "swipex-api"}