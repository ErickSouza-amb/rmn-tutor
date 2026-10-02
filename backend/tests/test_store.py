from datetime import timedelta

from app.store import repo
from app.store.db import normalize_db_url


def test_normalize_db_url():
    assert normalize_db_url("postgres://u:p@h/db?sslmode=require") == "postgresql+psycopg://u:p@h/db?sslmode=require"
    assert normalize_db_url("postgresql://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert normalize_db_url("sqlite+aiosqlite:///x.db") == "sqlite+aiosqlite:///x.db"


async def _new_session(db, owner="u1"):
    return await repo.create_session(
        db,
        owner_uid=owner,
        title="Teste",
        experiment="1H",
        metadata={"solvent": "CDCl3"},
        peaks=[{"id": "P1", "ppm": 1.0}],
        exercise_id=None,
        chem_state={"schema_version": 1},
    )


async def test_create_get_list_sessions(db):
    s1 = await _new_session(db)
    await _new_session(db, owner="other")
    got = await repo.get_session(db, s1.id)
    assert got.meta == {"solvent": "CDCl3"} and got.assist_mode == "tutor"
    listed = await repo.list_sessions(db, "u1")
    assert [s.id for s in listed] == [s1.id]


async def test_messages_get_consecutive_seq(db):
    s = await _new_session(db)
    await repo.add_messages(db, s.id, [repo.NewMessage("user", [{"type": "text", "text": "oi"}], "oi")])
    await repo.add_messages(
        db,
        s.id,
        [
            repo.NewMessage("system", "contexto"),
            repo.NewMessage("assistant", [{"type": "text", "text": "olá"}], "olá", usage={"input_tokens": 10, "output_tokens": 2}),
        ],
    )
    msgs = await repo.list_messages(db, s.id)
    assert [(m.seq, m.role) for m in msgs] == [(1, "user"), (2, "system"), (3, "assistant")]
    assert msgs[1].content == "contexto"
    assert await repo.count_messages(db, s.id) == 3


async def test_session_input_tokens(db):
    s = await _new_session(db)
    await repo.add_messages(
        db,
        s.id,
        [
            repo.NewMessage("assistant", [], usage={"input_tokens": 100, "cache_read_input_tokens": 50}),
            repo.NewMessage("assistant", [], usage={"input_tokens": 10, "cache_creation_input_tokens": 5}),
            repo.NewMessage("user", []),
        ],
    )
    assert await repo.session_input_tokens(db, s.id) == 165


async def test_turn_lock(db):
    s = await _new_session(db)
    assert await repo.acquire_turn_lock(db, s.id, 60) is True
    assert await repo.acquire_turn_lock(db, s.id, 60) is False
    await repo.release_turn_lock(db, s.id)
    assert await repo.acquire_turn_lock(db, s.id, 60) is True


async def test_rate_events(db):
    since = repo.utcnow() - timedelta(hours=1)
    await repo.record_rate_event(db, "uid:a")
    await repo.record_rate_event(db, "uid:a")
    await repo.record_rate_event(db, "uid:b")
    assert await repo.count_rate_events(db, "uid:a", since) == 2
    assert await repo.purge_rate_events(db, repo.utcnow() + timedelta(seconds=1)) == 3


async def test_delete_session_cascades(db):
    s = await _new_session(db)
    await repo.add_messages(db, s.id, [repo.NewMessage("user", [])])
    await repo.add_structure_check(db, s.id, "CCO", {"checks": []})
    deleted = await repo.delete_session(db, s.id)
    assert deleted.id == s.id
    assert await repo.get_session(db, s.id) is None
    assert await repo.list_messages(db, s.id) == []
    assert await repo.delete_session(db, s.id) is None


async def test_older_than_and_stats(db):
    s = await _new_session(db)
    old = await repo.list_sessions_older_than(db, repo.utcnow() + timedelta(days=1))
    assert [r.id for r in old] == [s.id]
    assert await repo.list_sessions_older_than(db, repo.utcnow() - timedelta(days=1)) == []
    st = await repo.stats(db)
    assert st["sessions"] == 1 and st["messages"] == 0
