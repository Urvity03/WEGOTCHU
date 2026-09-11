# Module: Backend Services (`backend/`)

## Purpose & Scope
Provides backend API services for user authentication, trusted contacts registry, telemetry ingestion, safety policy evaluation, and emergency dispatch integration.

## Primary Owner
* **Lead:** Member 3 (Mobile & Backend Engineer)

## Tech Stack
* **Framework:** FastAPI (Python 3.11+)
* **Validation:** Pydantic v2
* **Database:** PostgreSQL (with SQLAlchemy / Alembic migrations)
* **Server:** Uvicorn / Gunicorn
* **Containerization:** Docker & Docker Compose

## Key Interfaces
* `POST /api/v1/telemetry`: Ingests windowed feature vectors from connected mobile clients.
* `POST /api/v1/sos/trigger`: Inviolable immediate manual SOS endpoint ($< 100$ ms SLA).
* `POST /api/v1/contacts`: Manage verified trusted contacts.
* `GET /api/v1/status`: Health check and system status.
