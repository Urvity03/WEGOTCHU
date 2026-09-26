import os
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from alembic import context


# Load environment variables from backend/.env
load_dotenv()


# Alembic Config object
config = context.config


# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# Import SQLAlchemy Base and models
from app.database import Base
from app.models.telemetry_record import TelemetryRecord


# Metadata used by Alembic for autogenerate
target_metadata = Base.metadata


def get_database_url() -> str:
    """
    Get the PostgreSQL database URL from the DATABASE_URL
    environment variable.

    The actual password must never be stored in alembic.ini
    or committed to Git.
    """
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set"
        )

    return database_url


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""

    url = get_database_url()

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode."""

    database_url = get_database_url()

    connectable = engine_from_config(
        {
            "sqlalchemy.url": database_url,
        },
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()