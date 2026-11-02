from fastapi import FastAPI

from .routers.telemetry import router as telemetry_router
from .routers.sos import router as sos_router

app = FastAPI(
    title="WEGOTCHU Backend",
    version="0.1.0",
)

app.include_router(telemetry_router)
app.include_router(sos_router)


@app.get("/api/v1/status")
async def status():
    return {"status": "ok"}
