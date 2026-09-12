from fastapi import FastAPI

from app.routers.telemetry import router as telemetry_router

app = FastAPI(
    title="WEGOTCHU Backend",
    version="0.1.0",
)

app.include_router(telemetry_router)


@app.get("/api/v1/status")
async def status():
    return {"status": "ok"}
