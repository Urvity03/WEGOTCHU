import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from .database import SessionLocal
from .repositories.trip_repository import TripRepository
from .routers.telemetry import router as telemetry_router
from .routers.sos import router as sos_router

logger = logging.getLogger(__name__)

SAFETY_TIMER_RECONCILIATION_INTERVAL_SECONDS = 30


def _run_safety_timer_reconciliation() -> int:
    with SessionLocal() as db:
        repository = TripRepository(db)
        return repository.expire_due_safety_timers()


async def _safety_timer_reconciliation_loop() -> None:
    while True:
        try:
            expired_count = await asyncio.to_thread(
                _run_safety_timer_reconciliation
            )
            if expired_count:
                logger.info(
                    "Automatically expired %s overdue safety timer(s).",
                    expired_count,
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Safety timer reconciliation failed.")

        await asyncio.sleep(
            SAFETY_TIMER_RECONCILIATION_INTERVAL_SECONDS
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_safety_timer_reconciliation_loop())
    logger.info("Safety timer reconciliation scheduler started.")

    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        logger.info("Safety timer reconciliation scheduler stopped.")


app = FastAPI(
    title="WEGOTCHU Backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(telemetry_router)
app.include_router(sos_router)


@app.get("/api/v1/status")
async def status():
    return {"status": "ok"}
