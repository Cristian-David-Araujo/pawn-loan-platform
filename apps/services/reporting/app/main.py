from fastapi import FastAPI

app = FastAPI(title="reporting-service")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "reporting"}
