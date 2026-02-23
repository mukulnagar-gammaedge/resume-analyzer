from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from dotenv import load_dotenv

# ---------------------------------------------------------
# Ensure project root is in sys.path BEFORE importing app.*
# /app/alembic/env.py -> project root is /app
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Load env vars
load_dotenv()

# Alembic Config object
config = context.config

# Configure Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# ---------------------------------------------------------
# Import Base + models (this must populate Base.metadata)
# ---------------------------------------------------------
from app.db.base import Base  # noqa: E402
from app.models.job import Job  # noqa: F401,E402  (force registration)

target_metadata = Base.metadata


def get_sync_db_url() -> str:
    url = os.getenv("SYNC_DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "SYNC_DATABASE_URL is not set. Add it in .env "
            "(use postgresql://... not postgresql+asyncpg://...)"
        )
    return url


def run_migrations_offline() -> None:
    url = get_sync_db_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_sync_db_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()