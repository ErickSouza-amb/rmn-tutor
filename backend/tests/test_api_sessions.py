import io
import uuid

import httpx
from PIL import Image

from app.main import create_app


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 20), (0, 0, 0)).save(buf, "PNG")
    return buf.getvalue()


async def _exercise_session(client, exercise_id="ex02") -> str:
    res = await client.post("/api/sessions", json={"exercise_id": exercise_id})
    assert res.status_code == 201, res.text
    return res.json()["id"]


async def test_health_and_exercises(client):
    h = (await client.get("/api/health")).json()
    assert h["status"] == "ok" and h["db"] == "ok"
    ex = (await client.get("/api/exercises")).json()
    assert [e["id"] for e in ex] == ["ex01", "ex02", "ex03", "ex04", "ex05"]
    assert all("answer_smiles" not in e and "answer_name" not in e for e in ex)


async def test_create_exercise_session_and_get(client):
    sid = await _exercise_session(client)
    assert "rmn_uid" in client.cookies
    s = (await client.get(f"/api/sessions/{sid}")).json()
    assert s["exercise"] == {"id": "ex02", "title": "Exercício 2 — C₄H₈O₂", "reviewed": False, "notes": s["exercise"]["notes"]}
    assert [p["id"] for p in s["peaks"]] == ["P1", "P2", "P3"]
    assert s["metadata"]["molecular_formula"] == "C4H8O2"
    assert s["has_image"] is True and s["messages"] == [] and s["chem_state"]["stage"] == "observe"
    assert s["assist_mode"] == "tutor"


async def test_listing_is_per_cookie_but_link_works_anywhere(client):
    sid = await _exercise_session(client)
    listed = (await client.get("/api/sessions")).json()
    assert [x["id"] for x in listed] == [sid]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app()), base_url="http://test") as other:
        assert (await other.get("/api/sessions")).json() == []
        assert (await other.get(f"/api/sessions/{sid}")).status_code == 200


async def test_create_custom_session_renumbers(client):
    body = {
        "metadata": {"frequency_mhz": 300, "solvent": "CDCl3", "molecular_formula": "C2H6O"},
        "peaks": [{"id": "P1", "ppm": 1.2, "integral": 3}, {"id": "P2", "ppm": 3.7, "integral": 2}],
    }
    sid = (await client.post("/api/sessions", json=body)).json()["id"]
    s = (await client.get(f"/api/sessions/{sid}")).json()
    assert [(p["id"], p["ppm"]) for p in s["peaks"]] == [("P1", 3.7), ("P2", 1.2)]
    assert s["exercise"] is None and s["has_image"] is False


async def test_create_validation(client):
    r = await client.post("/api/sessions", json={"metadata": {"molecular_formula": "c2h6o"}})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    r = await client.post("/api/sessions", json={"experiment": "13C"})
    assert r.status_code == 422
    r = await client.post("/api/sessions", json={"exercise_id": "nope"})
    assert r.status_code == 404 and r.json()["error"]["code"] == "exercise_not_found"


async def test_unknown_session(client):
    r = await client.get(f"/api/sessions/{uuid.uuid4()}")
    assert r.status_code == 404 and r.json()["error"]["code"] == "session_not_found"
    assert (await client.get("/api/sessions/not-a-uuid")).status_code == 422


async def test_patch_session(client):
    sid = (await client.post("/api/sessions", json={})).json()["id"]
    r = await client.patch(f"/api/sessions/{sid}", json={"peaks": [{"id": "P1", "ppm": 1.0}, {"id": "P2", "ppm": 2.0}], "assist_mode": "hint", "title": "Meu espectro"})
    assert r.status_code == 200
    s = r.json()
    assert [p["ppm"] for p in s["peaks"]] == [2.0, 1.0] and s["assist_mode"] == "hint" and s["title"] == "Meu espectro"
    ex_sid = await _exercise_session(client)
    r = await client.patch(f"/api/sessions/{ex_sid}", json={"peaks": []})
    assert r.status_code == 409 and r.json()["error"]["code"] == "exercise_read_only"
    r = await client.patch(f"/api/sessions/{ex_sid}", json={"assist_mode": "verify"})
    assert r.status_code == 200


async def test_parse_and_spectrum(client):
    r = (await client.post("/api/peaks/parse", json={"text": "4,12 (q, J = 7,1 Hz, 2H)\nlixo"})).json()
    assert r["peaks"][0]["ppm"] == 4.12 and r["errors"][0]["line"] == 2
    sid = await _exercise_session(client)
    sp = (await client.get(f"/api/sessions/{sid}/spectrum")).json()
    assert len(sp["x"]) == len(sp["y"]) > 100 and max(sp["y"]) == 1.0


async def test_image_upload_and_fetch(client):
    sid = (await client.post("/api/sessions", json={})).json()["id"]
    r = await client.post(f"/api/sessions/{sid}/image", files={"file": ("e.png", _png(), "image/png")})
    assert r.status_code == 200 and r.json()["media_type"] == "image/png"
    img = await client.get(f"/api/sessions/{sid}/image")
    assert img.status_code == 200 and img.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert (await client.get(f"/api/sessions/{sid}")).json()["has_image"] is True
    bad = await client.post(f"/api/sessions/{sid}/image", files={"file": ("x.png", b"not an image", "image/png")})
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "invalid_image"


async def test_exercise_image_and_upload_forbidden(client):
    sid = await _exercise_session(client)
    img = await client.get(f"/api/sessions/{sid}/image")
    assert img.status_code == 200 and img.headers["content-type"] == "image/png"
    r = await client.post(f"/api/sessions/{sid}/image", files={"file": ("e.png", _png(), "image/png")})
    assert r.status_code == 409
    sid2 = (await client.post("/api/sessions", json={})).json()["id"]
    assert (await client.get(f"/api/sessions/{sid2}/image")).status_code == 404


async def test_structure_check(client):
    sid = await _exercise_session(client)
    r = (await client.post(f"/api/sessions/{sid}/structure-check", json={"smiles": "CCOC(C)=O"})).json()
    assert r["formula"] == "C4H8O2" and "matches_answer" not in r and r["check_id"]
    await client.patch(f"/api/sessions/{sid}", json={"assist_mode": "verify"})
    r2 = (await client.post(f"/api/sessions/{sid}/structure-check", json={"smiles": "CCOC(C)=O"})).json()
    assert r2["matches_answer"] is True
    bad = await client.post(f"/api/sessions/{sid}/structure-check", json={"smiles": "C1CC"})
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "invalid_smiles"
    s = (await client.get(f"/api/sessions/{sid}")).json()
    assert [p["smiles"] for p in s["chem_state"]["proposed_structures"]] == ["CCOC(C)=O", "CCOC(C)=O"]


async def test_patch_keeps_existing_peak_ids(client):
    sid = (await client.post("/api/sessions", json={"peaks": [{"id": "P1", "ppm": 4.12}, {"id": "P2", "ppm": 1.26}]})).json()["id"]
    body = {"peaks": [{"id": "P1", "ppm": 4.12}, {"id": "P2", "ppm": 1.26}, {"id": "P3", "ppm": 7.26}]}
    s = (await client.patch(f"/api/sessions/{sid}", json=body)).json()
    assert {(p["id"], p["ppm"]) for p in s["peaks"]} == {("P1", 4.12), ("P2", 1.26), ("P3", 7.26)}
    dup = await client.patch(f"/api/sessions/{sid}", json={"peaks": [{"id": "P1", "ppm": 1.0}, {"id": "P1", "ppm": 2.0}]})
    assert dup.status_code == 422


async def test_image_replace_rejected_after_conversation_and_put_before_delete(client, monkeypatch):
    sid = (await client.post("/api/sessions", json={})).json()["id"]
    assert (await client.post(f"/api/sessions/{sid}/image", files={"file": ("a.png", _png(), "image/png")})).status_code == 200
    from app.store.blob import get_blob_store

    store = get_blob_store()
    before = dict(store.objects)

    async def failing_put(*a, **k):
        raise RuntimeError("blob down")

    monkeypatch.setattr(store, "put", failing_put)
    r = await client.post(f"/api/sessions/{sid}/image", files={"file": ("b.png", _png(), "image/png")})
    assert r.status_code == 502 and r.json()["error"]["code"] == "storage_unavailable"
    assert store.objects == before  # old image untouched when the new put fails
    monkeypatch.undo()
    assert (await client.get(f"/api/sessions/{sid}/image")).status_code == 200
    await client.post(f"/api/sessions/{sid}/messages", json={"text": "Oi"})
    r = await client.post(f"/api/sessions/{sid}/image", files={"file": ("c.png", _png(), "image/png")})
    assert r.status_code == 409 and r.json()["error"]["code"] == "image_locked"
