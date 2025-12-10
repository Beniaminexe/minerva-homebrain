from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from ..core.database import Base


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)

    # "HTTP" or "TCP" for now
    kind = Column(String, nullable=False)
    target = Column(String, nullable=False)  # URL or "host:port"

    check_interval_sec = Column(Integer, default=60)
    timeout_sec = Column(Integer, default=5)

    enabled = Column(Boolean, default=True)
    alert_on_down = Column(Boolean, default=True)
    alert_on_recovery = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    # One-to-one with ServiceStatus
    status = relationship(
        "ServiceStatus",
        back_populates="service",
        uselist=False,
        cascade="all, delete-orphan",
    )


class ServiceStatus(Base):
    __tablename__ = "service_status"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id"), unique=True)

    is_up = Column(Boolean, default=False)
    latency_ms = Column(Float, nullable=True)
    last_checked_at = Column(DateTime, nullable=True)

    consecutive_failures = Column(Integer, default=0)
    last_change_at = Column(DateTime, nullable=True)

    service = relationship("Service", back_populates="status")
