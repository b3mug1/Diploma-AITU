"""Versioned schema migrations using the application's database configuration."""

from alembic import context
from app import models  # noqa: F401
from app.database import Base, engine

metadata = Base.metadata
if context.is_offline_mode():
    context.configure(url=engine.url, target_metadata=metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
