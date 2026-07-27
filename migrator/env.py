"""Alembic environment script.

Runs migrations synchronously using psycopg (psycopg3 sync driver).
DATABASE_URL is read from the environment; the scheme is normalised to
``postgresql+psycopg://`` so SQLAlchemy picks the right dialect.
"""

import os

from alembic import context
from models import Base
from sqlalchemy import NullPool, engine_from_config

config = context.config

target_metadata = Base.metadata


def _get_url() -> str:
    url = os.environ["DATABASE_URL"]
    # Normalise scheme for SQLAlchemy's psycopg3 dialect.
    return url.replace("postgresql://", "postgresql+psycopg://", 1)


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a live DB connection (--sql mode)."""
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live DB connection."""
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = _get_url()

    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
