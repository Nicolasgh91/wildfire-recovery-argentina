import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure repository root (parent of `app/`) is on sys.path so we can import `app.*`
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

from app.core.config import settings  # type: ignore  # noqa: E402


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# For now we don't rely on autogenerate, migrations are hand-written,
# so we can keep target_metadata = None. If in the future you want
# autogeneration, import your SQLAlchemy Base metadata here.
target_metadata = None


def _get_database_url() -> str:
    """
    Resolve the database URL from app settings.

    We prefer settings.DATABASE_URL, which is already assembled from
    DB_* variables in .env. If it's missing, we fail fast so the
    developer fixes configuration instead of Alembic guessing.
    """
    db_url = settings.DATABASE_URL
    if not db_url:
        raise RuntimeError("DATABASE_URL is not configured in app.core.config.settings")
    # Alembic expects sqlalchemy-style URLs. settings already normalizes
    # postgres vs postgresql if needed.
    return db_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = _get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

