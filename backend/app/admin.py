"""Manual maintenance CLI.  Usage (from backend/):  python -m app.admin --help

Production: pull env first (`vercel env pull .env.production.local`) and export DATABASE_URL,
BLOB_BACKEND=vercel and BLOB_READ_WRITE_TOKEN in the shell before running.
"""
import argparse
import asyncio
import re
import sys
import uuid
from datetime import timedelta
from pathlib import Path

from app.store import repo
from app.store.blob import get_blob_store
from app.store.db import get_sessionmaker

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

_DURATION = re.compile(r"^(\d+)([dhm])$")
CONFIRM = {"s", "sim", "y", "yes"}


def parse_duration(text: str) -> timedelta:
    m = _DURATION.match(text.strip().lower())
    if not m:
        raise ValueError(f"duração inválida: {text!r} (use 30d, 12h ou 45m)")
    n, unit = int(m.group(1)), m.group(2)
    return {"d": timedelta(days=n), "h": timedelta(hours=n), "m": timedelta(minutes=n)}[unit]


def _fmt_row(row, n_messages: int) -> str:
    updated = repo.as_aware(row.updated_at).strftime("%Y-%m-%d %H:%M")
    return f"{row.id}  {updated}  {row.exercise_id or '-':6}  {n_messages:4} msgs  {row.title}"


async def _delete_one(db, session_id: uuid.UUID) -> bool:
    row = await repo.delete_session(db, session_id)
    if row is None:
        return False
    if row.image_blob:
        try:
            await get_blob_store().delete(row.image_blob)
        except Exception as exc:  # blob already gone or store unreachable: report, keep going
            print(f"  aviso: não foi possível apagar a imagem {row.image_blob}: {exc}")
    return True


async def _run(args, input_fn) -> int:
    async with get_sessionmaker()() as db:
        if args.command == "stats":
            st = await repo.stats(db)
            for key, value in st.items():
                print(f"{key}: {value}")
            return 0

        if args.command == "list":
            if args.older_than:
                rows = await repo.list_sessions_older_than(db, repo.utcnow() - parse_duration(args.older_than), args.exercise)
            else:
                rows = await repo.list_all_sessions(db, args.limit)
                if args.exercise:
                    rows = [r for r in rows if r.exercise_id == args.exercise]
            for r in rows[: args.limit]:
                print(_fmt_row(r, await repo.count_messages(db, r.id)))
            print(f"{len(rows[: args.limit])} sessão(ões).")
            return 0

        if args.command == "delete":
            sid = uuid.UUID(args.session)
            row = await repo.get_session(db, sid)
            if row is None:
                print("Sessão não encontrada.")
                return 1
            print(_fmt_row(row, await repo.count_messages(db, sid)))
            if not args.yes and input_fn("Apagar esta sessão? [s/N] ").strip().lower() not in CONFIRM:
                print("Cancelado.")
                return 1
            await _delete_one(db, sid)
            print("Apagada.")
            return 0

        if args.command == "purge":
            cutoff = repo.utcnow() - parse_duration(args.older_than)
            rows = await repo.list_sessions_older_than(db, cutoff, args.exercise)
            if not rows:
                print("Nenhuma sessão para apagar.")
                return 1
            for r in rows:
                print(_fmt_row(r, await repo.count_messages(db, r.id)))
            print(f"{len(rows)} sessão(ões) seriam apagadas.")
            if args.dry_run:
                return 0
            if not args.yes and input_fn("Confirmar exclusão? [s/N] ").strip().lower() not in CONFIRM:
                print("Cancelado.")
                return 1
            ids = [r.id for r in rows]
            for sid in ids:
                await _delete_one(db, sid)
            purged = await repo.purge_rate_events(db, repo.utcnow() - timedelta(days=2))
            print(f"{len(ids)} sessão(ões) apagadas; {purged} eventos de rate limit removidos.")
            return 0
    return 2


def _migrate() -> int:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(cfg, "head")
    print("Migrações aplicadas.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m app.admin", description="Manutenção do RMN Tutor")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate", help="aplica as migrações do banco (alembic upgrade head)")
    sub.add_parser("stats", help="contagens e tokens acumulados")
    lp = sub.add_parser("list", help="lista sessões")
    lp.add_argument("--older-than")
    lp.add_argument("--exercise")
    lp.add_argument("--limit", type=int, default=200)
    dp = sub.add_parser("delete", help="apaga uma sessão")
    dp.add_argument("--session", required=True)
    dp.add_argument("--yes", action="store_true")
    pp = sub.add_parser("purge", help="apaga sessões antigas em lote")
    pp.add_argument("--older-than", required=True)
    pp.add_argument("--exercise")
    pp.add_argument("--dry-run", action="store_true")
    pp.add_argument("--yes", action="store_true")
    return p


def main(argv: list[str] | None = None, *, input_fn=input) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "migrate":
        return _migrate()
    try:
        return asyncio.run(_run(args, input_fn))
    except ValueError as exc:
        print(f"Erro: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
