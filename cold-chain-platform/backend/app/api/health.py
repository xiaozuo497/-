import os
import shutil
import socket

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.services.backup_service import create_backup, list_backups

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/diagnostics")
def diagnostics(db: Session = Depends(get_db)):
    checks = {
        "api": "ok",
        "environment": settings.app_env,
        "database": "unknown",
        "docker_hint": "compose" if os.path.exists("docker-compose.yml") else "external",
        "hostname": socket.gethostname(),
        "backup_dir": settings.backup_dir,
        "document_renderer": "available" if shutil.which("soffice") or shutil.which("libreoffice") else "missing",
    }
    try:
        db.execute(text("select 1"))
        checks["database"] = "ok"
        checks["order_count"] = db.scalar(text("select count(*) from orders"))
        checks["vehicle_count"] = db.scalar(text("select count(*) from vehicles"))
        checks["available_vehicle_count"] = db.scalar(text("select count(*) from vehicles where status = 'available'"))
        checks["pending_order_count"] = db.scalar(text("select count(*) from orders where status in ('pending', 'draft')"))
        checks["exception_order_count"] = db.scalar(text("select count(*) from orders where status = 'exception'"))
    except Exception as exc:
        checks["database"] = f"error: {exc.__class__.__name__}"
    backups = list_backups()
    checks["backup_count"] = len(backups)
    checks["latest_backup"] = backups[0] if backups else None
    return checks


@router.get("/backups")
def get_backups():
    return list_backups()


@router.post("/backups")
def post_backup(db: Session = Depends(get_db)):
    return create_backup(db)
