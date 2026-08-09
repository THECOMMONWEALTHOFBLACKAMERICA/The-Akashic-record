from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Model modules historically performed development schema bootstrapping at import
# time. Alembic must discover mappings without mutating the database first.
os.environ["TAR_MIGRATION_CONTEXT"] = "1"

from backend.app.settings import settings  # noqa: E402
from backend.app.memory import Base  # noqa: E402

_original_create_all = Base.metadata.create_all
Base.metadata.create_all = lambda *args, **kwargs: None  # type: ignore[method-assign]
try:
    from backend.app import artifacts as _artifacts  # noqa: F401,E402
    from backend.app import autonomy as _autonomy  # noqa: F401,E402
    from backend.app import commission as _commission  # noqa: F401,E402
    from backend.app import control as _control  # noqa: F401,E402
    from backend.app import ingestion as _ingestion  # noqa: F401,E402
    from backend.app import jobs as _jobs  # noqa: F401,E402
    from backend.app import library as _library  # noqa: F401,E402
    from backend.app import publications as _publications  # noqa: F401,E402
finally:
    Base.metadata.create_all = _original_create_all  # type: ignore[method-assign]

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
