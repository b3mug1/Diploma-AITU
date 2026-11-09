"""Bounded, create-only CSV imports with whole-file validation and atomic writes."""

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.audit import record_change
from app.database import get_db
from app.models import Locker, Student, User
from app.schemas import LockerCreate, StudentCreate
from app.security import admin_user

router = APIRouter()
MAX_BYTES = 1024 * 1024
MAX_ROWS = 1000


class ImportResult(BaseModel):
    created: int


class ImportRowError(BaseModel):
    row: int
    field: str
    message: str


class ImportErrorDetail(BaseModel):
    message: str
    errors: list[ImportRowError]


class ImportFailure(BaseModel):
    detail: ImportErrorDetail


CSV_BODY = {
    "requestBody": {
        "required": True,
        "content": {"text/csv": {"schema": {"type": "string", "format": "binary"}}},
    }
}
RESPONSES = {
    422: {"model": ImportFailure, "description": "CSV validation failed; no rows saved"},
    409: {"model": ImportFailure, "description": "Concurrent duplicate; no rows saved"},
    413: {"description": "File exceeds 1 MiB or 1000 data rows"},
    415: {"description": "Use Content-Type: text/csv"},
}


def fail(errors, code=422):
    raise HTTPException(code, {"message": "Import rejected; no rows saved.", "errors": errors})


async def read_csv(request):
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "text/csv":
        raise HTTPException(415, "Use Content-Type: text/csv.")
    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > MAX_BYTES:
            raise HTTPException(413, "CSV must not exceed 1 MiB.")
        content.extend(chunk)
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        fail([{"row": 1, "field": "file", "message": "Use UTF-8 encoding."}])


def import_records(content, model, schema, key, db, actor):
    reader = csv.reader(io.StringIO(content, newline=""), strict=True)
    errors, records, seen = [], [], set()
    try:
        header = next(reader, [])
        required = {key, "full_name"} if model is Student else {key}
        allowed = required if model is Student else required | {"location"}
        if (
            not required.issubset(header)
            or not set(header).issubset(allowed)
            or len(header) != len(set(header))
        ):
            fail(
                [
                    {
                        "row": 1,
                        "field": "header",
                        "message": (
                            f"Expected unique columns: {', '.join(sorted(required))}; "
                            f"optional: {', '.join(sorted(allowed - required)) or 'none'}."
                        ),
                    }
                ]
            )
        count = 0
        for values in reader:
            count += 1
            if count > MAX_ROWS:
                raise HTTPException(413, "CSV must not exceed 1000 data rows.")
            line = reader.line_num
            if len(values) != len(header):
                errors.append(
                    {"row": line, "field": "row", "message": "Column count differs from header."}
                )
                continue
            data = dict(zip(header, values))
            if model is Locker and not data.get("location", "").strip():
                data["location"] = None
            try:
                payload = schema.model_validate(data)
            except ValidationError as exc:
                errors.extend(
                    {"row": line, "field": str(error["loc"][0]), "message": error["msg"]}
                    for error in exc.errors()
                )
                continue
            identifier = getattr(payload, key)
            if identifier in seen:
                errors.append(
                    {"row": line, "field": key, "message": "Duplicate identifier in CSV."}
                )
            seen.add(identifier)
            records.append((line, payload.model_dump()))
    except csv.Error:
        fail(
            errors
            + [{"row": max(1, reader.line_num), "field": "file", "message": "Malformed CSV."}]
        )
    if count == 0:
        errors.append({"row": 2, "field": "file", "message": "Provide at least one data row."})

    # Chunk lookups to stay within database parameter limits.
    keys = list(seen)
    existing = set()
    for offset in range(0, len(keys), 200):
        existing.update(
            db.scalars(
                select(getattr(model, key)).where(
                    getattr(model, key).in_(keys[offset : offset + 200])
                )
            )
        )
    for line, data in records:
        if data[key] in existing:
            errors.append(
                {"row": line, "field": key, "message": "Identifier already exists in registry."}
            )
    if errors:
        fail(errors)

    line = 1
    try:
        for line, data in records:
            record = model(**data)
            db.add(record)
            db.flush()
            record_change(db, actor, record, "import")
        db.commit()
    except IntegrityError:
        db.rollback()
        fail(
            [
                {
                    "row": line,
                    "field": key,
                    "message": "Concurrent data conflict; refresh and retry.",
                }
            ],
            409,
        )
    return ImportResult(created=len(records))


@router.post(
    "/students/import",
    response_model=ImportResult,
    status_code=201,
    tags=["students"],
    openapi_extra=CSV_BODY,
    responses=RESPONSES,
)
async def import_students(
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_user),
):
    """Create students from UTF-8 CSV (student_code,full_name); all rows succeed or none do."""
    return await run_in_threadpool(
        import_records, await read_csv(request), Student, StudentCreate, "student_code", db, actor
    )


@router.post(
    "/lockers/import",
    response_model=ImportResult,
    status_code=201,
    tags=["lockers"],
    openapi_extra=CSV_BODY,
    responses=RESPONSES,
)
async def import_lockers(
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_user),
):
    """Create available lockers from UTF-8 CSV (locker_number, optional location); atomic."""
    return await run_in_threadpool(
        import_records, await read_csv(request), Locker, LockerCreate, "locker_number", db, actor
    )
