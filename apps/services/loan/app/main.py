from fastapi import FastAPI

app = FastAPI(title="loan-service")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "loan"}
