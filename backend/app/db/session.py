from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.app.config import settings

engine = create_engine(
    settings.db_url,
    connect_args={"check_same_thread": False},  # SQLite only
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables() -> None:
    from backend.app.db import models  # noqa: F401 — triggers model registration

    Base.metadata.create_all(bind=engine)
    _apply_migrations()


def _apply_migrations() -> None:
    """Add columns that exist in models but are missing from the live DB (safe, additive only)."""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    with engine.connect() as conn:
        for table in Base.metadata.sorted_tables:
            if not insp.has_table(table.name):
                continue
            existing = {col["name"] for col in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name not in existing:
                    # Build a minimal ALTER TABLE ADD COLUMN statement
                    col_type = col.type.compile(engine.dialect)
                    nullable_clause = "" if col.nullable else " NOT NULL"
                    default_clause = ""
                    if col.default is not None and col.default.is_scalar:
                        val = col.default.arg
                        if isinstance(val, str):
                            default_clause = f" DEFAULT '{val}'"
                        elif isinstance(val, bool):
                            default_clause = f" DEFAULT {int(val)}"
                        elif val is not None:
                            default_clause = f" DEFAULT {val}"
                    # SQLite requires nullable or a DEFAULT when adding columns
                    if not col.nullable and not default_clause:
                        default_clause = " DEFAULT ''"
                    sql = f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type}{default_clause}{nullable_clause if default_clause else ''}"
                    conn.execute(text(sql))
                    conn.commit()
