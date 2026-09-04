from __future__ import annotations

from sqlalchemy import JSON, Column

from app.db import crud
from app.db.models import ProxyHost

_installed = False


def install_xhttp_host_storage() -> None:
    """Attach the optional JSON column and preserve it in host replacements."""
    global _installed
    if _installed:
        return

    if "xhttp_settings" not in ProxyHost.__table__.c:
        ProxyHost.xhttp_settings = Column(JSON, nullable=True)

    original_add_host = crud.add_host
    original_update_hosts = crud.update_hosts

    def add_host(db, inbound_tag, host):
        rows = original_add_host(db, inbound_tag, host)
        if rows:
            rows[-1].xhttp_settings = host.xhttp_settings
            db.commit()
            db.refresh(rows[-1])
        return rows

    def update_hosts(db, inbound_tag, modified_hosts):
        rows = original_update_hosts(db, inbound_tag, modified_hosts)
        for row, modified in zip(rows, modified_hosts):
            row.xhttp_settings = modified.xhttp_settings
        db.commit()
        for row in rows:
            db.refresh(row)
        return rows

    crud.add_host = add_host
    crud.update_hosts = update_hosts
    _installed = True
