from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.optimization import OptimizationSolution, OptimizationTask, PackingPlan
from app.models.order import DeliveryRecord, DispatchAssignment, OperationException, Order
from app.models.reference import BoxType, User, Vehicle


EXPORT_MODELS = (
    User,
    BoxType,
    Vehicle,
    Order,
    OptimizationTask,
    OptimizationSolution,
    PackingPlan,
    DispatchAssignment,
    DeliveryRecord,
    OperationException,
)


def backup_dir() -> Path:
    path = Path(settings.backup_dir)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, UUID)):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    return value


def _row_dict(row: Any) -> dict[str, Any]:
    return {column.name: _json_value(getattr(row, column.name)) for column in row.__table__.columns}


def create_backup(db: Session | None = None) -> dict[str, Any]:
    owns_session = db is None
    session = db or SessionLocal()
    try:
        exported: dict[str, list[dict[str, Any]]] = {}
        for model in EXPORT_MODELS:
            rows = session.scalars(select(model)).all()
            exported[model.__tablename__] = [_row_dict(row) for row in rows]

        created_at = datetime.now(timezone.utc)
        payload = {
            "created_at": created_at.isoformat(),
            "tables": exported,
        }
        file_path = backup_dir() / f"cold_chain_backup_{created_at.strftime('%Y%m%d_%H%M%S')}.json"
        file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return backup_file_info(file_path)
    finally:
        if owns_session:
            session.close()


def backup_file_info(file_path: Path) -> dict[str, Any]:
    stat = file_path.stat()
    return {
        "name": file_path.name,
        "path": str(file_path),
        "size": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
    }


def list_backups() -> list[dict[str, Any]]:
    return sorted(
        [backup_file_info(path) for path in backup_dir().glob("cold_chain_backup_*.json")],
        key=lambda item: item["modified_at"],
        reverse=True,
    )
