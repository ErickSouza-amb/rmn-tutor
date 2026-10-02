import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.store.models import MessageRow, RateEventRow, SessionRow, StructureCheckRow


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_aware(dt: datetime | None) -> datetime | None:
    if dt is None or dt.tzinfo is not None:
        return dt
    return dt.replace(tzinfo=UTC)


@dataclass
class NewMessage:
    role: str
    content: list | str
    display_text: str | None = None
    mode: str | None = None
    usage: dict | None = None


async def create_session(
    db: AsyncSession,
    *,
    owner_uid: str,
    title: str,
    experiment: str,
    metadata: dict,
    peaks: list,
    exercise_id: str | None,
    chem_state: dict,
) -> SessionRow:
    row = SessionRow(
        owner_uid=owner_uid,
        title=title,
        experiment=experiment,
        meta=metadata,
        peaks=peaks,
        exercise_id=exercise_id,
        chem_state=chem_state,
        assist_mode="tutor",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_session(db: AsyncSession, session_id: uuid.UUID) -> SessionRow | None:
    return await db.get(SessionRow, session_id)


async def list_sessions(db: AsyncSession, owner_uid: str, limit: int = 50) -> list[SessionRow]:
    stmt = (
        select(SessionRow)
        .where(SessionRow.owner_uid == owner_uid)
        .order_by(SessionRow.updated_at.desc())
        .limit(limit)
    )
    return list((await db.scalars(stmt)).all())


async def save(db: AsyncSession, row: SessionRow) -> SessionRow:
    row.updated_at = utcnow()
    await db.commit()
    await db.refresh(row)
    return row


async def list_messages(db: AsyncSession, session_id: uuid.UUID) -> list[MessageRow]:
    stmt = select(MessageRow).where(MessageRow.session_id == session_id).order_by(MessageRow.seq)
    return list((await db.scalars(stmt)).all())


async def add_messages(
    db: AsyncSession, session_id: uuid.UUID, items: list[NewMessage], commit: bool = True
) -> list[MessageRow]:
    current = await db.scalar(select(func.max(MessageRow.seq)).where(MessageRow.session_id == session_id))
    seq = current or 0
    rows = []
    for item in items:
        seq += 1
        rows.append(
            MessageRow(
                session_id=session_id,
                seq=seq,
                role=item.role,
                content=item.content,
                display_text=item.display_text,
                mode=item.mode,
                usage=item.usage,
            )
        )
    db.add_all(rows)
    if commit:
        await db.commit()
    return rows


async def count_messages(db: AsyncSession, session_id: uuid.UUID) -> int:
    return await db.scalar(select(func.count()).select_from(MessageRow).where(MessageRow.session_id == session_id)) or 0


async def add_structure_check(
    db: AsyncSession, session_id: uuid.UUID, smiles: str, result: dict, commit: bool = True
) -> StructureCheckRow:
    row = StructureCheckRow(session_id=session_id, smiles=smiles, result=result)
    db.add(row)
    if commit:
        await db.commit()
    else:
        await db.flush()
    return row


async def record_rate_event(db: AsyncSession, key: str) -> None:
    db.add(RateEventRow(key=key))
    await db.commit()


async def count_rate_events(db: AsyncSession, key: str, since: datetime) -> int:
    stmt = select(func.count()).select_from(RateEventRow).where(RateEventRow.key == key, RateEventRow.created_at >= since)
    return await db.scalar(stmt) or 0


async def purge_rate_events(db: AsyncSession, cutoff: datetime) -> int:
    res = await db.execute(delete(RateEventRow).where(RateEventRow.created_at < cutoff))
    await db.commit()
    return res.rowcount or 0


async def acquire_turn_lock(db: AsyncSession, session_id: uuid.UUID, seconds: int) -> bool:
    now = utcnow()
    res = await db.execute(
        update(SessionRow)
        .where(
            SessionRow.id == session_id,
            or_(SessionRow.turn_lock_until.is_(None), SessionRow.turn_lock_until < now),
        )
        .values(turn_lock_until=now + timedelta(seconds=seconds))
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return res.rowcount == 1


async def release_turn_lock(db: AsyncSession, session_id: uuid.UUID) -> None:
    await db.execute(
        update(SessionRow)
        .where(SessionRow.id == session_id)
        .values(turn_lock_until=None)
        .execution_options(synchronize_session=False)
    )
    await db.commit()


def _usage_tokens(usage: dict | None) -> int:
    if not usage:
        return 0
    return sum(
        int(usage.get(k) or 0)
        for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    )


async def session_input_tokens(db: AsyncSession, session_id: uuid.UUID) -> int:
    rows = (await db.scalars(select(MessageRow.usage).where(MessageRow.session_id == session_id))).all()
    return sum(_usage_tokens(u) for u in rows)


async def delete_session(db: AsyncSession, session_id: uuid.UUID) -> SessionRow | None:
    row = await db.get(SessionRow, session_id)
    if row is None:
        return None
    await db.execute(delete(MessageRow).where(MessageRow.session_id == session_id))
    await db.execute(delete(StructureCheckRow).where(StructureCheckRow.session_id == session_id))
    await db.delete(row)
    await db.commit()
    return row


async def list_sessions_older_than(
    db: AsyncSession, cutoff: datetime, exercise_id: str | None = None
) -> list[SessionRow]:
    stmt = select(SessionRow).where(SessionRow.updated_at < cutoff)
    if exercise_id:
        stmt = stmt.where(SessionRow.exercise_id == exercise_id)
    return list((await db.scalars(stmt.order_by(SessionRow.updated_at))).all())


async def list_all_sessions(db: AsyncSession, limit: int = 1000) -> list[SessionRow]:
    stmt = select(SessionRow).order_by(SessionRow.updated_at.desc()).limit(limit)
    return list((await db.scalars(stmt)).all())


async def stats(db: AsyncSession) -> dict:
    sessions = await db.scalar(select(func.count()).select_from(SessionRow)) or 0
    messages = await db.scalar(select(func.count()).select_from(MessageRow)) or 0
    checks = await db.scalar(select(func.count()).select_from(StructureCheckRow)) or 0
    usages = (await db.scalars(select(MessageRow.usage))).all()
    oldest = await db.scalar(select(func.min(SessionRow.created_at)))
    newest = await db.scalar(select(func.max(SessionRow.created_at)))
    return {
        "sessions": sessions,
        "messages": messages,
        "structure_checks": checks,
        "input_tokens": sum(_usage_tokens(u) for u in usages),
        "oldest": as_aware(oldest),
        "newest": as_aware(newest),
    }
