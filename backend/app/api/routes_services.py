from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models import Service, ServiceStatus

router = APIRouter(prefix="/services", tags=["services"])


# ---------- Schemas ----------

class ServiceBase(BaseModel):
    name: str
    slug: str
    kind: str = Field(..., description="HTTP or TCP")
    target: str = Field(..., description="URL for HTTP, host:port for TCP")

    check_interval_sec: int = 60
    timeout_sec: int = 5

    enabled: bool = True
    alert_on_down: bool = True
    alert_on_recovery: bool = True

    @validator("kind")
    def validate_kind(cls, v):
        v = v.upper()
        if v not in ("HTTP", "TCP"):
            raise ValueError("kind must be 'HTTP' or 'TCP'")
        return v


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    kind: Optional[str] = None
    target: Optional[str] = None
    check_interval_sec: Optional[int] = None
    timeout_sec: Optional[int] = None
    enabled: Optional[bool] = None
    alert_on_down: Optional[bool] = None
    alert_on_recovery: Optional[bool] = None


class ServiceOut(ServiceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------- CRUD ENDPOINTS ----------


@router.get("", response_model=List[ServiceOut])
def list_services(db: Session = Depends(get_db)):
    services = db.query(Service).all()
    return services


@router.get("/{service_id}", response_model=ServiceOut)
def get_service(service_id: int, db: Session = Depends(get_db)):
    s = db.query(Service).filter(Service.id == service_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Service not found")
    return s


@router.post("", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
def create_service(payload: ServiceCreate, db: Session = Depends(get_db)):
    # Ensure slug uniqueness
    exists = db.query(Service).filter(Service.slug == payload.slug).first()
    if exists:
        raise HTTPException(status_code=400, detail="Slug already exists")

    s = Service(
        name=payload.name,
        slug=payload.slug,
        kind=payload.kind.upper(),
        target=payload.target,
        check_interval_sec=payload.check_interval_sec,
        timeout_sec=payload.timeout_sec,
        enabled=payload.enabled,
        alert_on_down=payload.alert_on_down,
        alert_on_recovery=payload.alert_on_recovery,
    )

    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.patch("/{service_id}", response_model=ServiceOut)
def update_service(service_id: int, payload: ServiceUpdate, db: Session = Depends(get_db)):
    s = db.query(Service).filter(Service.id == service_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Service not found")

    data = payload.dict(exclude_unset=True)

    if "name" in data:
        s.name = data["name"]
    if "slug" in data:
        existing = db.query(Service).filter(Service.slug == data["slug"]).first()
        if existing and existing.id != s.id:
            raise HTTPException(status_code=400, detail="Slug already in use")
        s.slug = data["slug"]
    if "kind" in data:
        s.kind = data["kind"].upper()
    if "target" in data:
        s.target = data["target"]
    if "check_interval_sec" in data:
        s.check_interval_sec = data["check_interval_sec"]
    if "timeout_sec" in data:
        s.timeout_sec = data["timeout_sec"]
    if "enabled" in data:
        s.enabled = data["enabled"]
    if "alert_on_down" in data:
        s.alert_on_down = data["alert_on_down"]
    if "alert_on_recovery" in data:
        s.alert_on_recovery = data["alert_on_recovery"]

    s.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(s)
    return s


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(service_id: int, db: Session = Depends(get_db)):
    s = db.query(Service).filter(Service.id == service_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Service not found")

    # Delete status first because of foreign key
    if s.status:
        db.delete(s.status)

    db.delete(s)
    db.commit()
    return
