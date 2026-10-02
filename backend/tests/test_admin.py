from datetime import timedelta

import pytest

from app.admin import main, parse_duration
from app.nmr_tools.state_ops import ChemState
from app.store import repo
from app.store.blob import get_blob_store, reset_blob_store
from app.store.db import create_all, get_sessionmaker


def test_parse_duration():
    assert parse_duration("30d") == timedelta(days=30)
    assert parse_duration("12h") == timedelta(hours=12)
    assert parse_duration("45m") == timedelta(minutes=45)
    with pytest.raises(ValueError):
        parse_duration("abc")


async def _make_sessions():
    await create_all()
    reset_blob_store()
    store = get_blob_store()
    async with get_sessionmaker()() as db:
        ids = []
        for i in range(2):
            row = await repo.create_session(
                db, owner_uid="u", title=f"s{i}", experiment="1H", metadata={}, peaks=[],
                exercise_id=None, chem_state=ChemState().model_dump(),
            )
            row.image_blob = await store.put(f"sessions/{row.id}/spectrum.png", b"x", "image/png")
            await repo.save(db, row)
            await repo.add_messages(db, row.id, [repo.NewMessage("user", [], "oi")])
            ids.append(row.id)
        return ids


async def _count():
    async with get_sessionmaker()() as db:
        return (await repo.stats(db))["sessions"]


def test_list_stats_delete_purge(capsys):
    import asyncio

    ids = asyncio.run(_make_sessions())
    assert main(["list"]) == 0
    assert str(ids[0]) in capsys.readouterr().out
    assert main(["stats"]) == 0
    assert "sessions: 2" in capsys.readouterr().out

    assert main(["delete", "--session", str(ids[0])], input_fn=lambda _: "n") == 1
    assert asyncio.run(_count()) == 2
    assert main(["delete", "--session", str(ids[0]), "--yes"]) == 0
    assert asyncio.run(_count()) == 1
    assert f"sessions/{ids[0]}/spectrum.png" not in get_blob_store().objects

    assert main(["purge", "--older-than", "1d"]) == 1  # nothing that old
    assert main(["purge", "--older-than", "0m", "--dry-run"]) == 0
    assert asyncio.run(_count()) == 1
    assert main(["purge", "--older-than", "0m"], input_fn=lambda _: "s") == 0
    assert asyncio.run(_count()) == 0
    assert main(["delete", "--session", str(ids[1]), "--yes"]) == 1  # already gone


def test_usage_errors():
    with pytest.raises(SystemExit) as exc:
        main(["purge"])
    assert exc.value.code == 2
