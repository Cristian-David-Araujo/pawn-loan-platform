from fastapi import FastAPI

app = FastAPI(title="customer-service")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "customer"}
