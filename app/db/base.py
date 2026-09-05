import logging

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import (
    SQLALCHEMY_DATABASE_URL,
    SQLALCHEMY_POOL_SIZE,
    SQLIALCHEMY_MAX_OVERFLOW,
)

logger = logging.getLogger(__name__)


def _normalize_url(raw: str):
    """Parse the configured URL and pick a sane default driver.

    A bare ``postgresql://`` URL makes SQLAlchemy reach for psycopg2, while the
    dependency we ship is psycopg 3, so the driver is filled in explicitly. An
    URL that already names a driver is left untouched.
    """

    try:
        url = make_url(raw)
    except Exception:  # pragma: no cover - malformed URL, let the engine complain
        return raw, raw.split("://", 1)[0].split("+", 1)[0]

    backend = url.get_backend_name()
    scheme = raw.split("://", 1)[0]
    if backend == "postgresql" and "+" not in scheme:
        url = url.set(drivername="postgresql+psycopg")
    return url, backend


DATABASE_URL, DATABASE_BACKEND = _normalize_url(SQLALCHEMY_DATABASE_URL)

# Full URL as a string, credentials included. Alembic needs it in this form.
DATABASE_URI = (
    DATABASE_URL
    if isinstance(DATABASE_URL, str)
    else DATABASE_URL.render_as_string(hide_password=False)
)

IS_SQLITE = DATABASE_BACKEND == "sqlite"
IS_MYSQL = DATABASE_BACKEND == "mysql"
IS_POSTGRES = DATABASE_BACKEND == "postgresql"

if IS_SQLITE:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=SQLALCHEMY_POOL_SIZE,
        max_overflow=SQLIALCHEMY_MAX_OVERFLOW,
        pool_recycle=3600,
        pool_timeout=10,
        pool_pre_ping=True,
        connect_args={"application_name": "marzban"} if IS_POSTGRES else {},
    )


if IS_POSTGRES:

    @event.listens_for(engine, "first_connect")
    def _ensure_citext(dbapi_connection, connection_record):
        """CITEXT backs the case-insensitive username and node name columns.

        Creating the extension needs elevated privileges, so a failure is only
        logged: it surfaces later as a clear error from the schema bootstrap.
        """

        try:
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS citext")
            finally:
                cursor.close()
            dbapi_connection.commit()
        except Exception as exc:
            logger.warning("Could not ensure the citext extension: %s", exc)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass
