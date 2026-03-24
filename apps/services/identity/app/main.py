from fastapi import FastAPI

app = FastAPI(title="identity-service")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "identity"}
