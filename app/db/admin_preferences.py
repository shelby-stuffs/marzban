from sqlalchemy import Column, String

from app.db.base import Base


class AdminPreference(Base):
    """Dashboard preferences keyed by login, including env-defined sudoers."""

    __tablename__ = "admin_preferences"

    username = Column(String(34), primary_key=True)
    dashboard_theme = Column(String(32), nullable=False, default="glamour-pink")
