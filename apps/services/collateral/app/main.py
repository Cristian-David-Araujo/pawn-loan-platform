from fastapi import FastAPI

app = FastAPI(title="collateral-service")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "collateral"}
