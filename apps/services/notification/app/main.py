from fastapi import FastAPI

app = FastAPI(title="notification-service")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "notification"}
