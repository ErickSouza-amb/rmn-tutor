# RMN Tutor MVP — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship to Vercel a pt-BR educational site where a student opens a curated ¹H NMR exercise or uploads a spectrum (image + peak list) and solves the structure with a Socratic Claude tutor that uses deterministic tools and RDKit checks.

**Architecture:** One Vercel project with two Services: `frontend/` (Next.js 16 App Router, TypeScript, Tailwind 4) and `backend/` (FastAPI, Python 3.12). `/api/*` is rewritten to the backend. The backend holds pure deterministic layers (`nmr_engine`, `chem`), a tool registry (`nmr_tools`) that is Claude's only door to data, a tutor orchestrator (`tutor`) doing an append-only, streaming tool-use loop with the Anthropic SDK, and persistence (`store`: Postgres via SQLAlchemy async + Vercel Blob private).

**Tech Stack:** Python 3.12, FastAPI 0.142.2, anthropic 1.11.0, rdkit 2026.3.6, numpy 2.5.3, pillow 12.3.0, SQLAlchemy 2.1.2 (asyncio), psycopg 3.3.6, alembic 1.20.0, vercel (Python SDK) 0.11.4, pytest 9.1.1 / pytest-asyncio 1.4.0 / aiosqlite 0.22.1; Next.js 16.3.x, React 19, Tailwind 4, plotly.js-dist-min 4.1.1, react-markdown 10.1.0, Vitest 5, Testing Library 16, Playwright 1.63.

**Spec:** `docs/superpowers/specs/2026-10-02-rmn-tutor-mvp-design.md` (read it before starting any task).

## Global Constraints

- UI language: Brazilian Portuguese (pt-BR) for every user-visible string, error message and tutor output.
- Experiment in the MVP: `1H` only; the `Experiment` enum must also declare `13C`, `DEPT`, `COSY`, `HSQC`, `HMBC` but the API rejects them.
- Secrets (`ANTHROPIC_API_KEY`, `DATABASE_URL`, `BLOB_READ_WRITE_TOKEN`, `SESSION_SECRET`) live only in backend env / Vercel env; never in frontend code, never in logs. The agent never reads or writes `ANTHROPIC_API_KEY` values; the user enters it.
- Upload: PNG/JPEG/WebP detected by magic bytes, ≤ 4 MB at the server (Vercel Functions cap request bodies at 4.5 MB; the browser downsizes larger images to ≤ 2048 px before upload), re-encoded with Pillow (EXIF stripped), long edge ≤ 2048 px.
- Peaks: ≤ 200 per session; ppm ∈ [-2, 16]; integral > 0; J ∈ (0, 30] Hz, ≤ 4 values per peak; multiplicities `s d t q quint sext sept m dd dt td ddd br_s`.
- SMILES ≤ 300 characters, ≤ 150 heavy atoms; never executed as code (RDKit parse only; the spec's "timeout" is satisfied by these size limits since RDKit parsing of bounded input is fast and C code cannot be interrupted).
- Student message ≤ 4000 characters; rate limit 30 messages/hour and 200/day per uid and per IP; session cap 400 000 accumulated input tokens (all configurable via env).
- Every tool result uses the envelope `{ok, tool, version: "1", data | error, warnings[], limitations[]}`; missing data is explicit (`data.status == "not_available"`). No tool queries external databases.
- Exercise answer SMILES/name never reach the frontend nor the Claude context. `check_against_answer` only answers `{same_structure: bool}` and only in `verify`/`solution` modes.
- Conversation history sent to Claude is append-only: exactly the persisted `messages` rows, never edited, summarized locally or deleted. Per-turn volatile context goes in a persisted mid-conversation `role: "system"` message after the user message. Long conversations use server-side compaction (beta `compact-2026-01-12`).
- Session link (UUID v4) is the access credential; `owner_uid` cookie only lists "Minhas sessões" and keys rate limits.
- Model: `TUTOR_MODEL` env (default `claude-sonnet-5-5`), `TUTOR_EFFORT` (default `medium`), `TUTOR_MAX_TOKENS` (default 16000), refusal fallback `fallbacks="default"` (beta `server-side-fallback-2026-07-01`).
- Exercises are flagged `reviewed: false`; UI shows the badge "dados não revisados"; `docs/exercises/REVIEW.md` holds the review checklist.
- Session cleanup is manual, via `python -m app.admin` (list / delete / purge / stats / migrate), always asking confirmation unless `--yes`.
- Deploy: GitHub repo + Vercel Git Integration (push to `main` → production; branches/PRs → preview). Vercel team `erick-0f6f`, project `rmn-tutor`.
- Commit messages end with the line `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. Peak lists typed the Brazilian way (`4,12`, `7,30–7,10 (m, 5H)`, `J = 7,1 Hz`, `;` separators) must parse to the same numbers as `4.12` etc. → tests in Task 3.
2. A student double-clicking "Enviar" (two concurrent turns on one session) must get a clear "turno em andamento" (409) on the second request and leave history intact → test in Task 13.
3. The Claude API failing mid-turn (or the browser disconnecting) must not persist a partial assistant/system sequence; the next turn must still produce a valid request → tests in Task 12.
4. Uploading the image after the conversation already started must attach it to the next user message without editing earlier rows → test in Task 12.
5. A session with an image but no peak list must make every numeric tool answer `not_available` and the turn context must say there is no table → tests in Task 10 and Task 12.

## File Map

```text
vercel.json                         Services + rewrites
.github/workflows/ci.yml            backend tests, frontend lint/test/build, e2e
CLAUDE.md                           project rules (root copy) + commands
README.md                           how to run, test, deploy
docs/exercises/REVIEW.md            generated checklist for human review
docs/operations/limpeza-de-sessoes.md
.claude/skills/{nmr-spectroscopy,nmr-tutor,project-development}/
backend/
  main.py                           `from app.main import app` (Vercel entrypoint main:app)
  requirements.txt / requirements-dev.txt / .python-version / pytest.ini / alembic.ini
  migrations/{env.py,script.py.mako,versions/0001_initial.py}
  app/main.py                       create_app()
  app/config.py                     Settings (pydantic-settings)
  app/logging.py                    JSON logs + request-id ASGI middleware
  app/errors.py                     ApiError + handlers → {"error":{code,message}}
  app/nmr_engine/models.py          Peak, Multiplicity, renumber
  app/nmr_engine/parser.py          parse_peak_text
  app/nmr_engine/queries.py         region/peak/integration/delta/J
  app/nmr_engine/simulate.py        first-order multiplets + Lorentzian curve
  app/chem/formula.py               formula parsing, H count, DBE (pure, no RDKit)
  app/chem/rdkit_tools.py           SMILES validation, formula, mass, InChIKey
  app/chem/environments.py          H environments by canonical symmetry + class
  app/chem/compare.py               compare_structure_with_data, same_structure
  app/exercises/catalog.py          YAML loader; data/ex01..ex05.yaml; images/*.png
  app/store/db.py                   async engine/sessionmaker, Base, URL normalization
  app/store/models.py               ORM tables
  app/store/repo.py                 data access functions
  app/store/blob.py                 BlobStore (Vercel private / memory)
  app/store/images.py               upload validation + re-encode
  app/api/deps.py                   db session, identity cookie, rate limit, lookup
  app/api/schemas.py                request/response models
  app/api/routes_misc.py            health, exercises, peaks/parse
  app/api/routes_sessions.py        sessions CRUD, image, spectrum, structure-check
  app/api/routes_messages.py        POST messages → SSE
  app/nmr_tools/envelope.py         ok / not_available / error
  app/nmr_tools/state_ops.py        ChemState + typed operations
  app/nmr_tools/registry.py         tool specs, schemas, execute_tool
  app/tutor/prompts.py              system prompt, mode instructions, turn context
  app/tutor/context.py              persisted rows → API messages (image injection)
  app/tutor/llm.py                  LLMClient protocol, AnthropicLLM, FakeLLM
  app/tutor/turn.py                 run_turn async generator
  app/admin.py                      cleanup CLI
  scripts/render_exercise_images.py scripts/build_review_doc.py scripts/tutor_eval.py
  tests/…
frontend/
  next.config.ts vitest.config.ts playwright.config.ts
  src/lib/{types.ts,api.ts,sse.ts}
  src/app/{layout.tsx,globals.css,page.tsx,sessoes/nova/page.tsx,sessoes/[id]/page.tsx}
  src/components/{MetadataForm,PeakTableEditor,ImageDrop,ImageViewer,SpectrumPlot,
                  SpectrumPanel,ChatPanel,ModeSelector,StatePanel,StructureCheckBox,
                  UnreviewedBadge,PrivacyNotice}.tsx
  e2e/tutor.spec.ts
```

## Task Order

1. Repo skeleton + Vercel/GitHub deployment spike (validates risks R1/R2)
2. Backend foundation: config, JSON logging, error envelope
3. `nmr_engine`: Peak model + peak-list parser
4. `nmr_engine`: queries (region, peak, integration, Δ, J) + `chem.formula`
5. `nmr_engine`: spectrum simulation
6. `chem`: RDKit tools, H environments, structure comparison
7. Exercise catalog (YAML ×5, images, REVIEW.md)
8. `store`: models, migration, repository
9. `store`: images + blob
10. `nmr_tools`: envelope, ChemState ops, registry
11. API: identity, sessions, exercises, parse, spectrum, image, structure-check
12. `tutor`: prompts, context builder, LLM clients, turn loop
13. API: messages SSE endpoint + rate limit + turn lock
14. Admin cleanup CLI + operations doc
15. Frontend foundation: API client, SSE parser, layout, home
16. Frontend: new-session page (metadata, peak editor, image upload)
17. Frontend: session page (spectrum panel, chat, modes, state, SMILES check)
18. E2E tests (Playwright, FAKE_LLM) + CI workflow
19. Project skills: `nmr-spectroscopy` (researched), `nmr-tutor`, `project-development`
20. Tutor eval script (real Claude) + README/CLAUDE.md
21. Provision Neon + Blob + env, migrate, preview verification, production

---

### Task 1: Repo skeleton + Vercel/GitHub deployment spike

Validates risks R1 (RDKit + numpy package/cold start on Vercel Python) and R2 (SSE streaming through Vercel Services) before any feature work. Also checks whether the backend receives the `/api` prefix in the path (expected: yes; routes are declared with `/api`).

**Files:**
- Create: `vercel.json`, `backend/main.py`, `backend/requirements.txt`, `backend/requirements-dev.txt`, `backend/.python-version`, `backend/pytest.ini`, `backend/tests/__init__.py`, `backend/tests/test_spike.py`
- Create (generated): `frontend/` via create-next-app
- Modify: `.gitignore`

**Interfaces:**
- Produces: `GET /api/health` → `{"status":"ok","version":"0.1.0","rdkit":"<ver>"}`; `GET /api/spike/sse` → SSE events `tick` (removed in Task 10).

- [ ] **Step 1: Create backend dependency files**

`backend/.python-version`:
```text
3.12
```

`backend/requirements.txt`:
```text
fastapi==0.142.2
pydantic==2.13.5
pydantic-settings==2.15.0
anthropic==1.11.0
rdkit==2026.3.6
numpy==2.5.3
pillow==12.3.0
sqlalchemy[asyncio]==2.1.2
psycopg[binary]==3.3.6
alembic==1.20.0
itsdangerous==2.2.0
pyyaml==6.0.3
python-multipart==0.0.32
vercel==0.11.4
```

`backend/requirements-dev.txt`:
```text
-r requirements.txt
uvicorn==0.54.0
aiosqlite==0.22.1
pytest==9.1.1
pytest-asyncio==1.4.0
httpx==0.28.1
matplotlib==3.11.2
ruff==0.16.10
```

`backend/pytest.ini`:
```ini
[pytest]
testpaths = tests
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
filterwarnings =
    ignore::DeprecationWarning
```

- [ ] **Step 2: Create venv and install**

Run (Git Bash, from repo root):
```bash
cd backend && python -m venv .venv && .venv/Scripts/python -m pip install -q --upgrade pip && .venv/Scripts/python -m pip install -q -r requirements-dev.txt && .venv/Scripts/python -c "import rdkit, fastapi, anthropic; print(rdkit.__version__)"
```
Expected: prints the RDKit version. On Linux/macOS use `.venv/bin/python`. All later backend commands assume the working directory `backend/` and the venv python (written below as `python`; activate with `source .venv/Scripts/activate`).

- [ ] **Step 3: Write the failing spike test**

`backend/tests/__init__.py`: empty file.

`backend/tests/test_spike.py`:
```python
from fastapi.testclient import TestClient

from main import app


def test_health_reports_rdkit():
    client = TestClient(app)
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["rdkit"]


def test_spike_sse_streams_ticks():
    client = TestClient(app)
    with client.stream("GET", "/api/spike/sse?n=3&delay=0") as res:
        assert res.headers["content-type"].startswith("text/event-stream")
        text = "".join(res.iter_text())
    assert text.count("event: tick") == 3
```

- [ ] **Step 4: Run test to verify it fails**

Run: `python -m pytest tests/test_spike.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'main'`).

- [ ] **Step 5: Write minimal backend**

`backend/main.py`:
```python
import asyncio
import json

import rdkit
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI(title="RMN Tutor API (spike)")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": "0.1.0", "rdkit": rdkit.__version__}


@app.get("/api/spike/sse")
async def spike_sse(n: int = 5, delay: float = 1.0) -> StreamingResponse:
    async def gen():
        for i in range(max(1, min(n, 20))):
            yield f"event: tick\ndata: {json.dumps({'i': i})}\n\n".encode()
            await asyncio.sleep(max(0.0, min(delay, 2.0)))

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/test_spike.py -v`
Expected: 2 passed.

- [ ] **Step 7: Scaffold the frontend**

Run from repo root:
```bash
npx --yes create-next-app@16.3.8 frontend --ts --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm --yes
```
If it created `frontend/.git`, remove it: `rm -rf frontend/.git`. Keep the generated `frontend/AGENTS.md` and `frontend/CLAUDE.md` (Next 16 agent rules: read the bundled docs in `frontend/node_modules/next/dist/docs/` before writing Next code). Replace `frontend/src/app/page.tsx` with:
```tsx
export default function Home() {
  return (
    <main className="p-8">
      <h1 className="text-2xl font-semibold">RMN Tutor</h1>
      <p>Em construção.</p>
    </main>
  );
}
```
Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 8: Create `vercel.json` at repo root and extend `.gitignore`**

`vercel.json`:
```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "services": {
    "frontend": { "root": "frontend/" },
    "backend": { "root": "backend/", "entrypoint": "main:app" }
  },
  "rewrites": [
    { "source": "/api/(.*)", "destination": { "service": "backend" } },
    { "source": "/(.*)", "destination": { "service": "frontend" } }
  ]
}
```

Append to `.gitignore`:
```text
# local databases / env
*.db
backend/.env*
frontend/.env*
!backend/.env.example

# local tooling output
.playwright-mcp/
```

- [ ] **Step 9: Commit**

```bash
git add vercel.json .gitignore backend frontend
git commit -m "chore: repo skeleton with FastAPI spike and Next.js app

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 10: GitHub repository (user interaction required)**

Ask the user to run, in the Claude Code prompt:
```text
! winget install --id GitHub.cli -e
! gh auth login
```
Ask the user (AskUserQuestion) whether the repository is **public** or **private** (note: `docs/exercises/REVIEW.md` will contain the exercise answers), then run:
```bash
gh repo create rmn-tutor --private --source . --remote origin --push
```
(use `--public` if chosen). Expected: repo URL printed; `git remote -v` shows `origin`.

- [ ] **Step 11: Vercel project linked to GitHub (user interaction required)**

Ask the user to run:
```text
! npm i -g vercel
! vercel login
```
Then:
```bash
vercel link --yes --project rmn-tutor --scope erick-0f6f
vercel git connect --yes
```
Expected: `.vercel/project.json` created (already git-ignored) and the project shows the GitHub repository connected (check with the Vercel MCP `get_project`).

- [ ] **Step 12: Deploy a preview from a branch and verify the spike**

```bash
git checkout -b spike/deploy
git commit --allow-empty -m "chore: trigger preview

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin spike/deploy
```
Find the preview URL (Vercel MCP `list_deployments` for project `rmn-tutor`). Wait until READY. If the preview answers 401 / a Vercel login page, load the `vercel:access-protected-vercel-deployment` skill and use `vercel curl`.

Verify:
```bash
time vercel curl /api/health --deployment <preview-url>
vercel curl "/api/spike/sse?n=5&delay=1" --deployment <preview-url>
```
Expected: health JSON with `rdkit`; the 5 `event: tick` blocks arrive progressively (about one per second), not all at once after 5 s. Opening `<preview-url>/` shows "RMN Tutor".

Create `docs/superpowers/plans/spike-notes.md` recording: build duration, backend bundle size (deployment build logs via `get_deployment` / `list_deployment_events`), cold-start time of the first `/api/health`, and whether SSE streamed progressively. If the build fails on the `vercel.json` schema, load the `vercel:vercel-services` skill, fix per the error (e.g. add `"framework": "fastapi"` / `"framework": "nextjs"` to the services) and push again. If SSE is buffered, STOP and tell the user: Task 13 must switch to the non-streaming fallback.

- [ ] **Step 13: Merge spike branch**

```bash
git add docs/superpowers/plans/spike-notes.md
git commit -m "docs: record deployment spike results

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git checkout main && git merge --ff-only spike/deploy && git push origin main
```
Expected: production deployment of the skeleton succeeds.

From here on, work on a feature branch (`git checkout -b feat/mvp`) and push it periodically; previews are built automatically.

---

### Task 2: Backend foundation — config, JSON logging, error envelope

**Files:**
- Create: `backend/app/__init__.py`, `backend/app/config.py`, `backend/app/logging.py`, `backend/app/errors.py`, `backend/app/main.py`, `backend/app/api/__init__.py`, `backend/app/api/routes_misc.py`, `backend/.env.example`
- Modify: `backend/main.py` (becomes a one-line entrypoint)
- Test: `backend/tests/conftest.py`, `backend/tests/test_foundation.py`, `backend/tests/test_spike.py` (keep passing)

**Interfaces:**
- Produces:
  - `app.config.Settings` fields: `app_version: str`, `database_url: str`, `session_secret: str`, `cookie_secure: bool`, `anthropic_api_key: str | None`, `blob_backend: Literal["memory","vercel"]`, `blob_read_write_token: str | None`, `tutor_model: str`, `tutor_effort: str`, `tutor_max_tokens: int`, `tutor_max_tool_iterations: int`, `fake_llm: bool`, `rate_limit_per_hour: int`, `rate_limit_per_day: int`, `session_input_token_cap: int`, `max_upload_bytes: int`, `max_message_chars: int`, `turn_lock_seconds: int`.
  - `app.config.get_settings() -> Settings` (lru_cached; tests call `get_settings.cache_clear()`).
  - `app.logging.log_event(logger: logging.Logger, msg: str, **fields) -> None`, `app.logging.request_id_var: ContextVar[str]`, `RequestContextMiddleware`.
  - `app.errors.ApiError(status: int, code: str, message: str)`; `install_error_handlers(app)`. Error body: `{"error": {"code": str, "message": str}}` (+ `"details"` for validation).
  - `app.main.create_app() -> FastAPI`; module-level `app`.
  - `app.api.routes_misc.router` (APIRouter, mounted at `/api`), with `GET /health` (DB check added in Task 10) and the spike SSE route moved here.

- [ ] **Step 1: Write the failing tests**

`backend/tests/conftest.py`:
```python
import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def _test_env(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}")
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.setenv("FAKE_LLM", "true")
    monkeypatch.setenv("BLOB_BACKEND", "memory")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
```

`backend/tests/test_foundation.py`:
```python
import json
import logging

from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.config import get_settings
from app.errors import ApiError
from app.logging import JsonFormatter
from app.main import create_app


def _app_with_test_routes():
    app = create_app()
    router = APIRouter()

    class Body(BaseModel):
        n: int

    @router.get("/api/_t/api-error")
    def raise_api_error():
        raise ApiError(409, "conflict_x", "Conflito de teste")

    @router.get("/api/_t/boom")
    def boom():
        raise RuntimeError("segredo interno")

    @router.post("/api/_t/validate")
    def validate(body: Body):
        return {"n": body.n}

    app.include_router(router)
    return app


def test_settings_read_env(monkeypatch):
    monkeypatch.setenv("TUTOR_MODEL", "claude-opus-5-5")
    get_settings.cache_clear()
    s = get_settings()
    assert s.tutor_model == "claude-opus-5-5"
    assert s.rate_limit_per_hour == 30
    assert s.max_upload_bytes == 4 * 1024 * 1024


def test_api_error_envelope():
    client = TestClient(_app_with_test_routes())
    res = client.get("/api/_t/api-error")
    assert res.status_code == 409
    assert res.json() == {"error": {"code": "conflict_x", "message": "Conflito de teste"}}


def test_unhandled_error_hides_details():
    client = TestClient(_app_with_test_routes(), raise_server_exceptions=False)
    res = client.get("/api/_t/boom")
    assert res.status_code == 500
    body = res.json()
    assert body["error"]["code"] == "internal_error"
    assert "segredo" not in json.dumps(body)


def test_validation_error_envelope():
    client = TestClient(_app_with_test_routes())
    res = client.post("/api/_t/validate", json={"n": "abc"})
    assert res.status_code == 422
    body = res.json()
    assert body["error"]["code"] == "validation_error"
    assert isinstance(body["error"]["details"], list)


def test_request_id_header():
    client = TestClient(create_app())
    res = client.get("/api/health")
    assert res.status_code == 200
    assert len(res.headers["x-request-id"]) == 16


def test_json_formatter_includes_fields():
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "evento", None, None)
    record.fields = {"session_id": "abc", "tokens": 3}
    payload = json.loads(JsonFormatter().format(record))
    assert payload["msg"] == "evento"
    assert payload["session_id"] == "abc"
    assert payload["level"] == "INFO"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_foundation.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'app'`).

- [ ] **Step 3: Implement config, logging, errors**

`backend/app/__init__.py`: empty.

`backend/app/config.py`:
```python
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_version: str = "0.1.0"
    database_url: str = "sqlite+aiosqlite:///./dev.db"
    session_secret: str = "dev-insecure-secret-change-me"
    cookie_secure: bool = True

    anthropic_api_key: str | None = None
    tutor_model: str = "claude-sonnet-5-5"
    tutor_effort: str = "medium"
    tutor_max_tokens: int = 16000
    tutor_max_tool_iterations: int = 6
    fake_llm: bool = False

    blob_backend: Literal["memory", "vercel"] = "memory"
    blob_read_write_token: str | None = None

    rate_limit_per_hour: int = 30
    rate_limit_per_day: int = 200
    session_input_token_cap: int = 400_000
    max_upload_bytes: int = 4 * 1024 * 1024  # Vercel Functions cap request bodies at 4.5 MB
    max_message_chars: int = 4000
    turn_lock_seconds: int = 300


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

`backend/app/logging.py`:
```python
import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
logger = logging.getLogger("rmn")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update(fields)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger("rmn")
    if any(isinstance(h.formatter, JsonFormatter) for h in root.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False


def log_event(log: logging.Logger, msg: str, **fields) -> None:
    log.info(msg, extra={"fields": fields})


class RequestContextMiddleware:
    """Pure ASGI middleware (safe with streaming responses)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        rid = uuid.uuid4().hex[:16]
        token = request_id_var.set(rid)
        start = time.perf_counter()
        status = {"code": 500}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", rid.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            log_event(
                logger,
                "request",
                method=scope.get("method"),
                path=scope.get("path"),
                status=status["code"],
                ms=round((time.perf_counter() - start) * 1000, 1),
            )
            request_id_var.reset(token)
```

`backend/app/errors.py`:
```python
import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("rmn.errors")


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def error_body(code: str, message: str, details=None) -> dict:
    body = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return body


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return JSONResponse(error_body(exc.code, exc.message), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        details = jsonable_encoder(
            [
                {"loc": list(e.get("loc", ())), "msg": e.get("msg"), "type": e.get("type")}
                for e in exc.errors()
            ]
        )
        return JSONResponse(
            error_body("validation_error", "Dados inválidos na requisição.", details),
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        logger.exception("unhandled_error", exc_info=exc)
        return JSONResponse(
            error_body("internal_error", "Erro interno. Tente novamente em instantes."),
            status_code=500,
        )
```

- [ ] **Step 4: Implement routes and app factory**

`backend/app/api/__init__.py`: empty.

`backend/app/api/routes_misc.py`:
```python
import asyncio
import json

import rdkit
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.config import get_settings

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": get_settings().app_version, "rdkit": rdkit.__version__}


@router.get("/spike/sse")
async def spike_sse(n: int = 5, delay: float = 1.0) -> StreamingResponse:
    async def gen():
        for i in range(max(1, min(n, 20))):
            yield f"event: tick\ndata: {json.dumps({'i': i})}\n\n".encode()
            await asyncio.sleep(max(0.0, min(delay, 2.0)))

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )
```

`backend/app/main.py`:
```python
from fastapi import FastAPI

from app.api.routes_misc import router as misc_router
from app.config import get_settings
from app.errors import install_error_handlers
from app.logging import RequestContextMiddleware, configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    app = FastAPI(
        title="RMN Tutor API",
        version=settings.app_version,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.add_middleware(RequestContextMiddleware)
    install_error_handlers(app)
    app.include_router(misc_router, prefix="/api")
    return app


app = create_app()
```

`backend/main.py` (replace whole file):
```python
from app.main import app  # noqa: F401  (Vercel entrypoint main:app)
```

`backend/.env.example`:
```text
DATABASE_URL=sqlite+aiosqlite:///./dev.db
SESSION_SECRET=troque-isto
COOKIE_SECURE=false
FAKE_LLM=true
BLOB_BACKEND=memory
# ANTHROPIC_API_KEY=  (defina localmente só se for testar com o Claude real)
TUTOR_MODEL=claude-sonnet-5-5
TUTOR_EFFORT=medium
```

- [ ] **Step 5: Run all tests**

Run: `python -m pytest -v`
Expected: all tests in `test_foundation.py` and `test_spike.py` pass.

- [ ] **Step 6: Commit**

```bash
git add backend
git commit -m "feat(backend): settings, JSON logging, error envelope, app factory

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `nmr_engine` — Peak model + peak-list parser

**Files:**
- Create: `backend/app/nmr_engine/__init__.py`, `backend/app/nmr_engine/models.py`, `backend/app/nmr_engine/parser.py`
- Test: `backend/tests/test_nmr_models.py`, `backend/tests/test_nmr_parser.py`

**Interfaces:**
- Produces:
  - `Multiplicity` (StrEnum): `s d t q quint sext sept m dd dt td ddd br_s`.
  - `Experiment` (StrEnum): `1H 13C DEPT COSY HSQC HMBC` (attribute names `H1, C13, DEPT, COSY, HSQC, HMBC`).
  - `Peak(BaseModel)`: `id: str` (`^P\d{1,3}$`), `ppm: float` ∈ [-2,16], `integral: float | None` (>0, ≤1000), `multiplicity: Multiplicity | None`, `j_hz: list[float] | None` (≤4 values, each in (0,30]), `source: Literal["user","exercise","engine"] = "user"`, `note: str | None` (≤200 chars).
  - `PeakList(BaseModel)`: `peaks: list[Peak]` (≤200, unique ids).
  - `renumber(peaks: list[Peak]) -> list[Peak]` — sorted by ppm descending, ids `P1..Pn`.
  - Constants `PPM_MIN = -2.0`, `PPM_MAX = 16.0`, `MAX_PEAKS = 200`.
  - `parse_peak_text(text: str, source: str = "user") -> ParseResult`; `ParseResult(peaks: list[Peak], errors: list[ParseError])`; `ParseError(line: int, message: str)` (dataclasses). `line == 0` means a whole-input error.

Accepted input (one peak per line unless literature format lists several):
- Tabular: fields separated by `;`, tab, comma or spaces: `ppm [integral] [multiplicity] [J ...]`. Integral may be `2` or `2H`. J values may be preceded by `J`, `J=`, `=` and followed by `Hz`.
- Decimal comma: when the line uses `;`/tab separators, fields like `4,12` are decimals; otherwise, if the line contains a dot-decimal (`\d\.\d`) commas are separators, else a comma between digits is a decimal comma.
- Literature: `4.12 (q, J = 7.1 Hz, 2H)`, ranges `7.30–7.10 (m, 5H)` (ppm = midpoint, note `faixa a–b ppm`), several per line (`δ 4.12 (q, …), 2.05 (s, 3H)`), pt-BR decimal commas inside (`J = 7,1 Hz`). Inner terms are split on comma+space or `;`.
- Ignored: blank lines, `#` comments, header lines that start with a non-digit and mention `ppm|δ|delta|desloc|mult|integr`.

- [ ] **Step 1: Write the failing model tests**

`backend/tests/test_nmr_models.py`:
```python
import pytest
from pydantic import ValidationError

from app.nmr_engine.models import Experiment, Multiplicity, Peak, PeakList, renumber


def test_peak_accepts_minimal_fields():
    p = Peak(id="P1", ppm=4.12)
    assert p.integral is None and p.multiplicity is None and p.j_hz is None
    assert p.source == "user"


def test_peak_rejects_out_of_range_ppm():
    with pytest.raises(ValidationError):
        Peak(id="P1", ppm=17.0)


def test_peak_rejects_bad_j():
    with pytest.raises(ValidationError):
        Peak(id="P1", ppm=1.0, j_hz=[0.0])
    with pytest.raises(ValidationError):
        Peak(id="P1", ppm=1.0, j_hz=[1, 2, 3, 4, 5])


def test_peak_list_rejects_duplicate_ids():
    with pytest.raises(ValidationError):
        PeakList(peaks=[Peak(id="P1", ppm=1.0), Peak(id="P1", ppm=2.0)])


def test_renumber_sorts_descending():
    peaks = renumber([Peak(id="P1", ppm=1.26), Peak(id="P2", ppm=4.12), Peak(id="P3", ppm=2.05)])
    assert [(p.id, p.ppm) for p in peaks] == [("P1", 4.12), ("P2", 2.05), ("P3", 1.26)]


def test_enums():
    assert Multiplicity("br_s") is Multiplicity.br_s
    assert Experiment("1H") is Experiment.H1
    assert {e.value for e in Experiment} == {"1H", "13C", "DEPT", "COSY", "HSQC", "HMBC"}
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_nmr_models.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement models**

`backend/app/nmr_engine/__init__.py`: empty.

`backend/app/nmr_engine/models.py`:
```python
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

PPM_MIN = -2.0
PPM_MAX = 16.0
MAX_PEAKS = 200


class Multiplicity(StrEnum):
    s = "s"
    d = "d"
    t = "t"
    q = "q"
    quint = "quint"
    sext = "sext"
    sept = "sept"
    m = "m"
    dd = "dd"
    dt = "dt"
    td = "td"
    ddd = "ddd"
    br_s = "br_s"


class Experiment(StrEnum):
    H1 = "1H"
    C13 = "13C"
    DEPT = "DEPT"
    COSY = "COSY"
    HSQC = "HSQC"
    HMBC = "HMBC"


class Peak(BaseModel):
    id: str = Field(pattern=r"^P\d{1,3}$")
    ppm: float = Field(ge=PPM_MIN, le=PPM_MAX)
    integral: float | None = Field(default=None, gt=0, le=1000)
    multiplicity: Multiplicity | None = None
    j_hz: list[float] | None = None
    source: Literal["user", "exercise", "engine"] = "user"
    note: str | None = Field(default=None, max_length=200)

    @field_validator("j_hz")
    @classmethod
    def _check_j(cls, v: list[float] | None) -> list[float] | None:
        if v is None:
            return v
        if len(v) > 4:
            raise ValueError("no máximo 4 constantes J por pico")
        for j in v:
            if not (0 < j <= 30):
                raise ValueError("J deve estar entre 0 e 30 Hz")
        return v


class PeakList(BaseModel):
    peaks: list[Peak] = Field(default_factory=list, max_length=MAX_PEAKS)

    @model_validator(mode="after")
    def _unique_ids(self) -> "PeakList":
        ids = [p.id for p in self.peaks]
        if len(ids) != len(set(ids)):
            raise ValueError("IDs de pico duplicados")
        return self


def renumber(peaks: list[Peak]) -> list[Peak]:
    ordered = sorted(peaks, key=lambda p: -p.ppm)
    return [p.model_copy(update={"id": f"P{i + 1}"}) for i, p in enumerate(ordered)]
```

- [ ] **Step 4: Run model tests**

Run: `python -m pytest tests/test_nmr_models.py -v`
Expected: 6 passed.

- [ ] **Step 5: Write the failing parser tests**

`backend/tests/test_nmr_parser.py`:
```python
from app.nmr_engine.parser import parse_peak_text


def _tuples(result):
    return [(p.id, p.ppm, p.integral, p.multiplicity, p.j_hz) for p in result.peaks]


def test_csv_with_header_dot_decimal():
    r = parse_peak_text("ppm,integral,mult,J\n1.26,3,t,7.1\n4.12,2,q,7.1\n2.05,3,s")
    assert r.errors == []
    assert _tuples(r) == [
        ("P1", 4.12, 2.0, "q", [7.1]),
        ("P2", 2.05, 3.0, "s", None),
        ("P3", 1.26, 3.0, "t", [7.1]),
    ]


def test_semicolon_with_decimal_comma():
    r = parse_peak_text("4,12;2;q;7,1\n1,26;3;t;7,1")
    assert r.errors == []
    assert _tuples(r)[0] == ("P1", 4.12, 2.0, "q", [7.1])


def test_space_separated_decimal_comma():
    r = parse_peak_text("4,12 2 q 7,1")
    assert _tuples(r) == [("P1", 4.12, 2.0, "q", [7.1])]


def test_integral_with_h_suffix_and_j_marker():
    r = parse_peak_text("4.12 2H q J = 7.1 Hz")
    assert _tuples(r) == [("P1", 4.12, 2.0, "q", [7.1])]


def test_j_marker_without_integral_is_not_integral():
    r = parse_peak_text("4.12 J = 7.1")
    assert _tuples(r) == [("P1", 4.12, None, None, [7.1])]


def test_literature_single_line_ptbr():
    text = "RMN de 1H (400 MHz, CDCl3) δ 4,12 (q, J = 7,1 Hz, 2H), 2,05 (s, 3H), 1,26 (t, J = 7,1 Hz, 3H)."
    r = parse_peak_text(text)
    assert r.errors == []
    assert _tuples(r) == [
        ("P1", 4.12, 2.0, "q", [7.1]),
        ("P2", 2.05, 3.0, "s", None),
        ("P3", 1.26, 3.0, "t", [7.1]),
    ]


def test_literature_range_and_two_j():
    r = parse_peak_text("7,30–7,10 (m, 5H)\n7.94 (dd, J = 8.0, 2.0 Hz, 1H)")
    assert r.errors == []
    by_ppm = {p.ppm: p for p in r.peaks}
    assert by_ppm[7.2].multiplicity == "m"
    assert by_ppm[7.2].note == "faixa 7.1–7.3 ppm"
    assert by_ppm[7.94].j_hz == [8.0, 2.0]


def test_broad_singlet_aliases():
    r = parse_peak_text("2.00 (br s, 1H)\n1.90 1 s largo")
    assert [p.multiplicity for p in r.peaks] == ["br_s", "br_s"]


def test_bad_line_reports_line_number_and_keeps_others():
    r = parse_peak_text("4.12 2 q 7.1\nabc def\n18.0 1 s")
    assert len(r.peaks) == 1
    assert [e.line for e in r.errors] == [2, 3]
    assert "fora do intervalo" in r.errors[1].message


def test_comments_and_blank_lines_ignored():
    r = parse_peak_text("# meus picos\n\n4.12 2 q 7.1\n")
    assert len(r.peaks) == 1 and r.errors == []


def test_limit_of_200_peaks():
    text = "\n".join(f"{1 + i * 0.01:.2f} 1 s" for i in range(201))
    r = parse_peak_text(text)
    assert len(r.peaks) == 200
    assert r.errors[-1].line == 0


def test_source_is_propagated():
    r = parse_peak_text("1.0 3 s", source="exercise")
    assert r.peaks[0].source == "exercise"
```

- [ ] **Step 6: Run to verify failure**

Run: `python -m pytest tests/test_nmr_parser.py -v`
Expected: FAIL (module not found).

- [ ] **Step 7: Implement the parser**

`backend/app/nmr_engine/parser.py`:
```python
import re
from dataclasses import dataclass, field

from app.nmr_engine.models import MAX_PEAKS, PPM_MAX, PPM_MIN, Peak, renumber

_MULT_ALIASES = {
    "s": "s", "singlet": "s", "singleto": "s",
    "d": "d", "doublet": "d", "dubleto": "d", "dupleto": "d",
    "t": "t", "triplet": "t", "tripleto": "t",
    "q": "q", "quartet": "q", "quarteto": "q",
    "quint": "quint", "quintet": "quint", "quinteto": "quint", "p": "quint",
    "sext": "sext", "sextet": "sext", "sexteto": "sext",
    "sept": "sept", "septet": "sept", "septeto": "sept", "hept": "sept", "hepteto": "sept",
    "m": "m", "multiplet": "m", "multipleto": "m",
    "dd": "dd", "dt": "dt", "td": "td", "ddd": "ddd",
    "br_s": "br_s", "brs": "br_s", "bs": "br_s", "sl": "br_s",
}
_J_MARKERS = {"j", "j=", "j:", "=", "hz"}
_NUM = r"-?\d+(?:[.,]\d+)?"
_LIT_ITER = re.compile(
    rf"(?P<a>{_NUM})(?:\s*[-–—]\s*(?P<b>{_NUM}))?\s*(?:ppm)?\s*\((?P<inner>[^)]*)\)", re.I
)
_INTEGRAL_RE = re.compile(rf"^(?P<n>{_NUM})\s*H$", re.I)
_J_RE = re.compile(rf"^J\s*[=:]?\s*(?P<n>{_NUM})\s*(?:Hz)?$", re.I)
_BARE_J_RE = re.compile(rf"^(?P<n>{_NUM})\s*(?:Hz)?$", re.I)
_HEADER_RE = re.compile(r"ppm|δ|delta|desloc|mult|integr", re.I)


@dataclass
class ParseError:
    line: int
    message: str


@dataclass
class ParseResult:
    peaks: list[Peak] = field(default_factory=list)
    errors: list[ParseError] = field(default_factory=list)


def _num(s: str) -> float:
    return float(s.replace(",", "."))


def _try_num(s: str) -> float | None:
    return _num(s) if re.fullmatch(_NUM, s) else None


def _normalize_tokens(text: str) -> str:
    text = re.sub(r"\bbr\.?\s+s\b", "br_s", text, flags=re.I)
    return re.sub(r"\bs\s+(?:largo|br)\b", "br_s", text, flags=re.I)


def _parse_literature(m: re.Match) -> dict:
    a = _num(m["a"])
    note = None
    if m["b"] is not None:
        b = _num(m["b"])
        ppm = round((a + b) / 2, 3)
        note = f"faixa {min(a, b):g}–{max(a, b):g} ppm"
    else:
        ppm = a
    integral = None
    mult = None
    js: list[float] = []
    in_j = False
    for tok in re.split(r",\s+|;\s*", m["inner"].strip()):
        tok = tok.strip().rstrip(".")
        if not tok:
            continue
        key = tok.lower()
        if key in _MULT_ALIASES and mult is None:
            mult, in_j = _MULT_ALIASES[key], False
        elif im := _INTEGRAL_RE.match(tok):
            integral, in_j = _num(im["n"]), False
        elif jm := _J_RE.match(tok):
            js.append(_num(jm["n"]))
            in_j = True
        elif in_j and (bm := _BARE_J_RE.match(tok)):
            js.append(_num(bm["n"]))
        else:
            raise ValueError(f"termo não reconhecido: '{tok}'")
    return {"ppm": ppm, "integral": integral, "multiplicity": mult, "j_hz": js or None, "note": note}


def _split_fields(line: str) -> list[str]:
    if ";" in line or "\t" in line:
        fields = [f.strip() for f in re.split(r"[;\t]", line)]
        return [f.replace(",", ".") if re.fullmatch(r"-?\d+,\d+", f) else f for f in fields]
    if re.search(r"\d\.\d", line):
        return [f for f in re.split(r"[,\s]+", line.strip()) if f]
    line = re.sub(r"(?<=\d),(?=\d)", ".", line)
    return [f for f in re.split(r"[,\s]+", line.strip()) if f]


def _parse_fields(fields: list[str]) -> dict:
    fields = [f for f in fields if f not in ("", "-", "—")]
    if not fields:
        raise ValueError("linha vazia")
    ppm = _try_num(fields[0])
    if ppm is None:
        raise ValueError(f"δ (ppm) ausente ou inválido: '{fields[0]}'")
    integral = None
    mult = None
    js: list[float] = []
    saw_j = False
    for f in fields[1:]:
        key = f.lower()
        if key in _J_MARKERS:
            saw_j = True
            continue
        if key in _MULT_ALIASES and mult is None:
            mult = _MULT_ALIASES[key]
            continue
        if im := _INTEGRAL_RE.match(f):
            integral = _num(im["n"])
            continue
        if jm := _J_RE.match(f):
            js.append(_num(jm["n"]))
            continue
        v = _try_num(re.sub(r"(?i)hz$", "", f).strip())
        if v is not None:
            if not saw_j and integral is None and mult is None and not js:
                integral = v
            else:
                js.append(v)
            continue
        raise ValueError(f"termo não reconhecido: '{f}'")
    return {"ppm": ppm, "integral": integral, "multiplicity": mult, "j_hz": js or None, "note": None}


def _build_peak(d: dict, source: str, index: int) -> Peak:
    if not (PPM_MIN <= d["ppm"] <= PPM_MAX):
        raise ValueError(f"δ = {d['ppm']:g} fora do intervalo [-2, 16] ppm")
    if d["integral"] is not None and not (0 < d["integral"] <= 1000):
        raise ValueError("a integral deve ser maior que zero")
    if d["j_hz"]:
        if len(d["j_hz"]) > 4:
            raise ValueError("no máximo 4 constantes J por pico")
        if any(not (0 < j <= 30) for j in d["j_hz"]):
            raise ValueError("J deve estar entre 0 e 30 Hz")
    return Peak(
        id=f"P{index}",
        ppm=round(d["ppm"], 4),
        integral=d["integral"],
        multiplicity=d["multiplicity"],
        j_hz=d["j_hz"],
        source=source,
        note=d["note"],
    )


def parse_peak_text(text: str, source: str = "user") -> ParseResult:
    result = ParseResult()
    raw: list[Peak] = []
    for line_no, original in enumerate(text.splitlines(), start=1):
        line = _normalize_tokens(original.strip())
        if not line or line.startswith("#"):
            continue
        try:
            matches = list(_LIT_ITER.finditer(line))
            if matches:
                items = [_parse_literature(m) for m in matches]
            elif re.match(r"^[^\d\-]", line) and _HEADER_RE.search(line):
                continue
            else:
                items = [_parse_fields(_split_fields(line))]
            built = [_build_peak(d, source, len(raw) + i + 1) for i, d in enumerate(items)]
            raw.extend(built)
        except ValueError as exc:
            result.errors.append(ParseError(line_no, str(exc)))
    if len(raw) > MAX_PEAKS:
        result.errors.append(
            ParseError(0, f"limite de {MAX_PEAKS} picos excedido; apenas os {MAX_PEAKS} primeiros foram mantidos")
        )
        raw = raw[:MAX_PEAKS]
    result.peaks = renumber(raw)
    return result
```

- [ ] **Step 8: Run parser tests**

Run: `python -m pytest tests/test_nmr_parser.py tests/test_nmr_models.py -v`
Expected: all pass. If `test_literature_range_and_two_j` fails on the note text, check `:g` formatting (7.30 → `7.3`, 7.10 → `7.1`).

- [ ] **Step 9: Commit**

```bash
git add backend/app/nmr_engine backend/tests/test_nmr_models.py backend/tests/test_nmr_parser.py
git commit -m "feat(nmr_engine): Peak model and tolerant pt-BR peak-list parser

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: `nmr_engine` queries + `chem.formula`

**Files:**
- Create: `backend/app/chem/__init__.py`, `backend/app/chem/formula.py`, `backend/app/nmr_engine/queries.py`
- Test: `backend/tests/test_formula.py`, `backend/tests/test_nmr_queries.py`

**Interfaces:**
- Consumes: `Peak` (Task 3).
- Produces:
  - `chem.formula.parse_formula(formula: str) -> dict[str, int]` (raises `ValueError("fórmula inválida: …")`), `hydrogen_count(formula: str) -> int`, `degrees_of_unsaturation(formula: str) -> float`, `normalize_formula(formula: str) -> str` (Hill order: C, H, then alphabetical; counts of 1 omitted).
  - `nmr_engine.queries.peaks_in_region(peaks, ppm_start, ppm_end) -> list[Peak]` (inclusive, order of `peaks`, bounds may be given in any order).
  - `find_peak(peaks, *, peak_id: str | None = None, ppm: float | None = None, tolerance_ppm: float = 0.05) -> Peak | None` (closest within tolerance when by ppm).
  - `integrate_region(peaks, ppm_start, ppm_end, total_h: int | None) -> dict` with keys `peak_ids: list[str]`, `sum: float | None`, `missing_integrals: list[str]`, `normalized_h: float | None`, `scale_h_per_unit: float | None`.
  - `delta_between(a: Peak, b: Peak, frequency_mhz: float | None) -> dict` → `{"delta_ppm": float, "delta_hz": float | None}` (rounded to 4 and 2 decimals).

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_formula.py`:
```python
import pytest

from app.chem.formula import degrees_of_unsaturation, hydrogen_count, normalize_formula, parse_formula


def test_parse_formula():
    assert parse_formula("C4H8O2") == {"C": 4, "H": 8, "O": 2}
    assert parse_formula("CH3Cl") == {"C": 1, "H": 3, "Cl": 1}


@pytest.mark.parametrize("bad", ["", "c4h8", "C4H8O2)", "4CH"])
def test_parse_formula_rejects(bad):
    with pytest.raises(ValueError):
        parse_formula(bad)


def test_hydrogen_count():
    assert hydrogen_count("C7H8") == 8
    assert hydrogen_count("CCl4") == 0


@pytest.mark.parametrize(
    "formula,dbe",
    [("C2H6O", 0), ("C4H8O2", 1), ("C7H8", 4), ("C9H10O2", 5), ("C5H5N", 4), ("C2H5Br", 0)],
)
def test_degrees_of_unsaturation(formula, dbe):
    assert degrees_of_unsaturation(formula) == dbe


def test_normalize_formula_hill_order():
    assert normalize_formula("H8C4O2") == "C4H8O2"
    assert normalize_formula("OC2H6") == "C2H6O"
    assert normalize_formula("ClCH3") == "CH3Cl"
```

`backend/tests/test_nmr_queries.py`:
```python
from app.nmr_engine.models import Peak
from app.nmr_engine.queries import delta_between, find_peak, integrate_region, peaks_in_region

PEAKS = [
    Peak(id="P1", ppm=4.12, integral=2, multiplicity="q", j_hz=[7.1]),
    Peak(id="P2", ppm=2.05, integral=3, multiplicity="s"),
    Peak(id="P3", ppm=1.26, integral=3, multiplicity="t", j_hz=[7.1]),
]


def test_peaks_in_region_any_order_inclusive():
    assert [p.id for p in peaks_in_region(PEAKS, 4.12, 2.0)] == ["P1", "P2"]
    assert peaks_in_region(PEAKS, 6, 8) == []


def test_find_peak_by_id_and_ppm():
    assert find_peak(PEAKS, peak_id="P3").ppm == 1.26
    assert find_peak(PEAKS, ppm=2.03).id == "P2"
    assert find_peak(PEAKS, ppm=3.0) is None
    assert find_peak(PEAKS, peak_id="P9") is None


def test_integrate_region_normalized_by_formula():
    r = integrate_region(PEAKS, 0, 5, total_h=8)
    assert r["sum"] == 8.0
    assert r["scale_h_per_unit"] == 1.0
    assert r["normalized_h"] == 8.0
    r2 = integrate_region(PEAKS, 3.5, 4.5, total_h=16)
    assert r2["peak_ids"] == ["P1"] and r2["normalized_h"] == 4.0


def test_integrate_region_missing_integrals():
    peaks = PEAKS + [Peak(id="P4", ppm=7.0)]
    r = integrate_region(peaks, 6, 8, total_h=8)
    assert r["sum"] is None
    assert r["missing_integrals"] == ["P4"]
    r_all = integrate_region(peaks, 0, 5, total_h=8)
    assert r_all["sum"] == 8.0
    assert r_all["normalized_h"] is None  # P4 lacks integral → no global scale


def test_delta_between():
    assert delta_between(PEAKS[0], PEAKS[2], 400) == {"delta_ppm": 2.86, "delta_hz": 1144.0}
    assert delta_between(PEAKS[0], PEAKS[2], None)["delta_hz"] is None
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_formula.py tests/test_nmr_queries.py -v`
Expected: FAIL (modules not found).

- [ ] **Step 3: Implement**

`backend/app/chem/__init__.py`: empty.

`backend/app/chem/formula.py`:
```python
import re

_TOKEN = re.compile(r"([A-Z][a-z]?)(\d*)")
_FULL = re.compile(r"(?:[A-Z][a-z]?\d*)+")
HALOGENS = {"F", "Cl", "Br", "I"}


def parse_formula(formula: str) -> dict[str, int]:
    f = (formula or "").strip().replace(" ", "")
    if not f or not _FULL.fullmatch(f):
        raise ValueError(f"fórmula inválida: {formula!r}")
    counts: dict[str, int] = {}
    for element, n in _TOKEN.findall(f):
        counts[element] = counts.get(element, 0) + (int(n) if n else 1)
    return counts


def hydrogen_count(formula: str) -> int:
    return parse_formula(formula).get("H", 0)


def degrees_of_unsaturation(formula: str) -> float:
    c = parse_formula(formula)
    carbons = c.get("C", 0)
    hydrogens = c.get("H", 0)
    nitrogens = c.get("N", 0) + c.get("P", 0)
    halogens = sum(c.get(x, 0) for x in HALOGENS)
    return carbons - (hydrogens + halogens) / 2 + nitrogens / 2 + 1


def normalize_formula(formula: str) -> str:
    c = parse_formula(formula)
    order = [e for e in ("C", "H") if e in c] + sorted(e for e in c if e not in ("C", "H"))
    return "".join(f"{e}{c[e] if c[e] != 1 else ''}" for e in order)
```

`backend/app/nmr_engine/queries.py`:
```python
from app.nmr_engine.models import Peak


def peaks_in_region(peaks: list[Peak], ppm_start: float, ppm_end: float) -> list[Peak]:
    lo, hi = sorted((ppm_start, ppm_end))
    return [p for p in peaks if lo <= p.ppm <= hi]


def find_peak(
    peaks: list[Peak],
    *,
    peak_id: str | None = None,
    ppm: float | None = None,
    tolerance_ppm: float = 0.05,
) -> Peak | None:
    if peak_id is not None:
        return next((p for p in peaks if p.id == peak_id), None)
    if ppm is None:
        return None
    candidates = [p for p in peaks if abs(p.ppm - ppm) <= tolerance_ppm]
    return min(candidates, key=lambda p: abs(p.ppm - ppm), default=None)


def integrate_region(
    peaks: list[Peak], ppm_start: float, ppm_end: float, total_h: int | None
) -> dict:
    region = peaks_in_region(peaks, ppm_start, ppm_end)
    missing = [p.id for p in region if p.integral is None]
    region_sum = None if missing or not region else round(sum(p.integral for p in region), 4)
    scale = None
    normalized = None
    all_have = bool(peaks) and all(p.integral is not None for p in peaks)
    if total_h and all_have and region_sum is not None:
        scale = round(total_h / sum(p.integral for p in peaks), 6)
        normalized = round(region_sum * scale, 3)
    return {
        "peak_ids": [p.id for p in region],
        "sum": region_sum,
        "missing_integrals": missing,
        "normalized_h": normalized,
        "scale_h_per_unit": scale,
    }


def delta_between(a: Peak, b: Peak, frequency_mhz: float | None) -> dict:
    delta_ppm = round(abs(a.ppm - b.ppm), 4)
    delta_hz = round(delta_ppm * frequency_mhz, 2) if frequency_mhz else None
    return {"delta_ppm": delta_ppm, "delta_hz": delta_hz}
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_formula.py tests/test_nmr_queries.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/chem backend/app/nmr_engine/queries.py backend/tests/test_formula.py backend/tests/test_nmr_queries.py
git commit -m "feat(nmr_engine): region/peak/integration/delta queries and formula utils

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: `nmr_engine` — spectrum simulation

Draws a didactic 1H curve from the peak table: first-order splitting by the given J values (binomial intensities), Lorentzian lines, area ∝ integral. Used by `GET /spectrum` (plot) and to render exercise PNGs.

**Files:**
- Create: `backend/app/nmr_engine/simulate.py`
- Test: `backend/tests/test_nmr_simulate.py`

**Interfaces:**
- Consumes: `Peak` (Task 3).
- Produces:
  - `multiplet_lines(center_ppm: float, multiplicity: str | None, j_hz: list[float] | None, frequency_mhz: float) -> tuple[list[tuple[float, float]], bool]` — list of `(ppm, weight)` with weights summing to 1, plus `split_ok` (False when the multiplicity needs J values that are missing; then a single line is returned).
  - `simulate_spectrum(peaks: list[Peak], frequency_mhz: float | None) -> SimResult` with dataclass `SimResult(x: list[float], y: list[float], warnings: list[str])`; `x` ascending ppm, `y` normalized to max 1.0, ≤ 20 000 points.
  - Constants: `DEFAULT_FREQUENCY_MHZ = 400.0`, `DEFAULT_FWHM_HZ = 1.2`, `BROAD_FWHM_HZ = {"m": 8.0, "br_s": 12.0}`.

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_nmr_simulate.py`:
```python
import numpy as np
import pytest

from app.nmr_engine.models import Peak
from app.nmr_engine.simulate import multiplet_lines, simulate_spectrum


def test_singlet_single_line():
    lines, ok = multiplet_lines(2.0, "s", None, 400)
    assert lines == [(2.0, 1.0)] and ok


def test_quartet_binomial_pattern():
    lines, ok = multiplet_lines(4.0, "q", [8.0], 400)
    assert ok
    positions = [round(p, 4) for p, _ in lines]
    weights = [w for _, w in lines]
    assert positions == [3.97, 3.99, 4.01, 4.03]
    assert weights == pytest.approx([1 / 8, 3 / 8, 3 / 8, 1 / 8])


def test_dd_uses_two_couplings():
    lines, ok = multiplet_lines(7.0, "dd", [8.0, 2.0], 400)
    assert ok and len(lines) == 4
    assert sum(w for _, w in lines) == pytest.approx(1.0)


def test_missing_j_falls_back_to_single_line():
    lines, ok = multiplet_lines(1.0, "t", None, 400)
    assert lines == [(1.0, 1.0)] and not ok
    lines, ok = multiplet_lines(1.0, "dd", [7.0], 400)
    assert len(lines) == 1 and not ok


def _area(x, y, lo, hi):
    x = np.asarray(x)
    y = np.asarray(y)
    mask = (x >= lo) & (x <= hi)
    return np.trapezoid(y[mask], x[mask])


def test_area_proportional_to_integral():
    peaks = [Peak(id="P1", ppm=5.0, integral=3, multiplicity="s"), Peak(id="P2", ppm=2.0, integral=1, multiplicity="s")]
    sim = simulate_spectrum(peaks, 400)
    a1 = _area(sim.x, sim.y, 4.5, 5.5)
    a2 = _area(sim.x, sim.y, 1.5, 2.5)
    assert a1 / a2 == pytest.approx(3.0, rel=0.05)
    assert max(sim.y) == pytest.approx(1.0)
    assert sim.x == sorted(sim.x)
    assert len(sim.x) <= 20000


def test_warnings_for_missing_data():
    peaks = [Peak(id="P1", ppm=1.2, multiplicity="t")]
    sim = simulate_spectrum(peaks, None)
    text = " ".join(sim.warnings)
    assert "400 MHz" in text
    assert "P1" in text and "J" in text
    assert "integral" in text


def test_empty_peaks_gives_flat_baseline():
    sim = simulate_spectrum([], 400)
    assert len(sim.x) > 10 and max(sim.y) == 0.0
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_nmr_simulate.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement**

`backend/app/nmr_engine/simulate.py`:
```python
from dataclasses import dataclass, field
from math import comb

import numpy as np

from app.nmr_engine.models import Peak

DEFAULT_FREQUENCY_MHZ = 400.0
DEFAULT_FWHM_HZ = 1.2
BROAD_FWHM_HZ = {"m": 8.0, "br_s": 12.0}
SPLIT_COUNTS: dict[str, tuple[int, ...]] = {
    "s": (),
    "d": (1,),
    "t": (2,),
    "q": (3,),
    "quint": (4,),
    "sext": (5,),
    "sept": (6,),
    "dd": (1, 1),
    "dt": (1, 2),
    "td": (2, 1),
    "ddd": (1, 1, 1),
}


@dataclass
class SimResult:
    x: list[float]
    y: list[float]
    warnings: list[str] = field(default_factory=list)


def multiplet_lines(
    center_ppm: float, multiplicity: str | None, j_hz: list[float] | None, frequency_mhz: float
) -> tuple[list[tuple[float, float]], bool]:
    single = [(center_ppm, 1.0)]
    counts = SPLIT_COUNTS.get(str(multiplicity)) if multiplicity else None
    if not counts:
        return single, True
    js = j_hz or []
    if len(js) < len(counts):
        return single, False
    lines = single
    for n, j in zip(counts, js):
        new: list[tuple[float, float]] = []
        for pos, w in lines:
            for k in range(n + 1):
                offset_ppm = (k - n / 2) * j / frequency_mhz
                new.append((pos + offset_ppm, w * comb(n, k) / 2**n))
        lines = new
    return lines, True


def _lorentzian(x: np.ndarray, x0: float, fwhm: float) -> np.ndarray:
    g = fwhm / 2
    return (g / np.pi) / ((x - x0) ** 2 + g**2)


def simulate_spectrum(peaks: list[Peak], frequency_mhz: float | None) -> SimResult:
    warnings: list[str] = []
    freq = frequency_mhz or DEFAULT_FREQUENCY_MHZ
    if not frequency_mhz:
        warnings.append("Frequência não informada; simulação feita com 400 MHz.")
    if not peaks:
        x = np.linspace(0.0, 12.0, 241)
        return SimResult(x=[round(float(v), 5) for v in x], y=[0.0] * len(x), warnings=warnings)

    components: list[tuple[float, float, float]] = []
    missing_integral = False
    for p in peaks:
        area = p.integral if p.integral is not None else 1.0
        missing_integral |= p.integral is None
        mult = str(p.multiplicity) if p.multiplicity else None
        fwhm_ppm = BROAD_FWHM_HZ.get(mult or "", DEFAULT_FWHM_HZ) / freq
        lines, ok = multiplet_lines(p.ppm, mult, p.j_hz, freq)
        if not ok:
            warnings.append(f"{p.id}: multiplicidade '{mult}' sem J suficiente; desenhado como linha única.")
        components.extend((pos, area * w, fwhm_ppm) for pos, w in lines)
    if missing_integral:
        warnings.append("Há picos sem integral; foi usada integral 1 para desenhá-los.")

    positions = [c[0] for c in components]
    lo = min(min(positions) - 0.5, -0.2)
    hi = max(max(positions) + 0.5, 10.0)
    parts = [np.arange(lo, hi, 0.01)]
    for pos, _, fw in components:
        parts.append(np.arange(pos - 25 * fw, pos + 25 * fw, fw / 6))
    x = np.unique(np.round(np.concatenate(parts), 5))
    x = x[(x >= lo) & (x <= hi)]
    y = np.zeros_like(x)
    for pos, area, fw in components:
        y += area * _lorentzian(x, pos, fw)
    y = y / y.max()
    if len(x) > 20000:
        idx = np.linspace(0, len(x) - 1, 20000).astype(int)
        x, y = x[idx], y[idx]
    return SimResult(
        x=[float(v) for v in x],
        y=[round(float(v), 5) for v in y],
        warnings=warnings,
    )
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_nmr_simulate.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/nmr_engine/simulate.py backend/tests/test_nmr_simulate.py
git commit -m "feat(nmr_engine): first-order multiplet simulation with Lorentzian lines

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: `chem` — RDKit tools, H environments, structure comparison

**Files:**
- Create: `backend/app/chem/rdkit_tools.py`, `backend/app/chem/environments.py`, `backend/app/chem/compare.py`
- Test: `backend/tests/test_chem_rdkit.py`, `backend/tests/test_chem_compare.py`

**Interfaces:**
- Consumes: `Peak` (Task 3), `chem.formula` (Task 4).
- Produces:
  - `rdkit_tools.SmilesError(ValueError)`; `MAX_SMILES_LEN = 300`; `MAX_HEAVY_ATOMS = 150`.
  - `mol_from_smiles(smiles: str) -> Chem.Mol` (raises `SmilesError` with pt-BR message).
  - `validate_smiles(smiles: str) -> dict` → `{"valid": True, "canonical_smiles": str}` or `{"valid": False, "error": str}`.
  - `molecular_formula(smiles: str) -> dict` → `{"canonical_smiles", "formula", "mw", "exact_mass"}` (raises `SmilesError`).
  - `inchikey(smiles: str) -> str` (raises `SmilesError`).
  - `environments.HEnvironment(rank: int, count: int, h_class: str)` (frozen dataclass); `h_environments(mol) -> list[HEnvironment]`; `H_CLASS_RANGES: dict[str, tuple[float, float]]`; `H_CLASS_LABELS: dict[str, str]` (pt-BR labels).
  - `compare.compare_structure_with_data(smiles: str, peaks: list[Peak], molecular_formula: str | None) -> dict` → keys `canonical_smiles`, `formula`, `total_h`, `h_environments` (list of `{"count","h_class","label","expected_range_ppm"}`), `checks` (list of `{"name","status","detail","heuristic"}` with `status ∈ {"pass","fail","inconclusive"}`, names `formula`, `h_count`, `environment_count`, `environment_integrals`, `shift_ranges`), `limitations` (list[str]). Raises `SmilesError`.
  - `compare.same_structure(smiles_a: str, smiles_b: str) -> bool` (InChIKey equality; False if either is invalid).

- [ ] **Step 1: Write the failing RDKit tests**

`backend/tests/test_chem_rdkit.py`:
```python
import pytest

from app.chem.environments import h_environments
from app.chem.rdkit_tools import SmilesError, inchikey, mol_from_smiles, molecular_formula, validate_smiles


def test_validate_smiles_ok_and_canonical():
    r = validate_smiles("OCC")
    assert r == {"valid": True, "canonical_smiles": "CCO"}


@pytest.mark.parametrize("bad", ["", "C1CC", "C C", "X" * 301])
def test_validate_smiles_rejects(bad):
    r = validate_smiles(bad)
    assert r["valid"] is False and r["error"]


def test_too_many_atoms():
    with pytest.raises(SmilesError):
        mol_from_smiles("C" * 151)


def test_molecular_formula_ethyl_acetate():
    r = molecular_formula("CC(=O)OCC")
    assert r["formula"] == "C4H8O2"
    assert r["mw"] == pytest.approx(88.106, abs=0.01)
    assert r["exact_mass"] == pytest.approx(88.0524, abs=0.001)


def test_inchikey_same_for_equivalent_smiles():
    assert inchikey("CCO") == inchikey("OCC")


def _env_summary(smiles):
    return sorted((e.count, e.h_class) for e in h_environments(mol_from_smiles(smiles)))


def test_environments_ethanol():
    assert _env_summary("CCO") == [(1, "exchangeable"), (2, "alpha_heteroatom"), (3, "alkyl")]


def test_environments_toluene_four_groups():
    assert _env_summary("Cc1ccccc1") == [
        (1, "aromatic"),
        (2, "aromatic"),
        (2, "aromatic"),
        (3, "allylic_benzylic_alpha_carbonyl"),
    ]


def test_environments_classes_misc():
    assert ("aldehyde" in {e.h_class for e in h_environments(mol_from_smiles("CC=O"))})
    assert ("carboxylic_acid" in {e.h_class for e in h_environments(mol_from_smiles("CC(=O)O"))})
    assert ("vinylic" in {e.h_class for e in h_environments(mol_from_smiles("C=CC"))})
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_chem_rdkit.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement RDKit tools and environments**

`backend/app/chem/rdkit_tools.py`:
```python
from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors, rdMolDescriptors

RDLogger.DisableLog("rdApp.*")

MAX_SMILES_LEN = 300
MAX_HEAVY_ATOMS = 150


class SmilesError(ValueError):
    pass


def mol_from_smiles(smiles: str) -> Chem.Mol:
    s = (smiles or "").strip()
    if not s:
        raise SmilesError("SMILES vazio.")
    if len(s) > MAX_SMILES_LEN:
        raise SmilesError(f"SMILES longo demais (máx. {MAX_SMILES_LEN} caracteres).")
    if any(ch.isspace() for ch in s):
        raise SmilesError("SMILES não pode conter espaços.")
    mol = Chem.MolFromSmiles(s)
    if mol is None:
        raise SmilesError("SMILES inválido: não foi possível interpretar a estrutura.")
    if mol.GetNumAtoms() > MAX_HEAVY_ATOMS:
        raise SmilesError(f"Molécula grande demais para o tutor (máx. {MAX_HEAVY_ATOMS} átomos pesados).")
    return mol


def validate_smiles(smiles: str) -> dict:
    try:
        mol = mol_from_smiles(smiles)
    except SmilesError as exc:
        return {"valid": False, "error": str(exc)}
    return {"valid": True, "canonical_smiles": Chem.MolToSmiles(mol)}


def molecular_formula(smiles: str) -> dict:
    mol = mol_from_smiles(smiles)
    return {
        "canonical_smiles": Chem.MolToSmiles(mol),
        "formula": rdMolDescriptors.CalcMolFormula(mol),
        "mw": round(Descriptors.MolWt(mol), 3),
        "exact_mass": round(Descriptors.ExactMolWt(mol), 4),
    }


def inchikey(smiles: str) -> str:
    return Chem.MolToInchiKey(mol_from_smiles(smiles))
```

`backend/app/chem/environments.py`:
```python
from dataclasses import dataclass

from rdkit import Chem

# Approximate 1H shift windows in CDCl3 (heuristic, didactic).
H_CLASS_RANGES: dict[str, tuple[float, float]] = {
    "alkyl": (0.5, 2.0),
    "allylic_benzylic_alpha_carbonyl": (1.6, 2.9),
    "alkynyl": (1.7, 3.3),
    "alpha_heteroatom": (2.2, 4.8),
    "vinylic": (4.5, 7.0),
    "aromatic": (6.0, 8.8),
    "aldehyde": (9.0, 10.5),
    "carboxylic_acid": (9.5, 13.5),
    "exchangeable": (0.5, 6.0),
    "other": (-2.0, 16.0),
}
H_CLASS_LABELS: dict[str, str] = {
    "alkyl": "H alquílico",
    "allylic_benzylic_alpha_carbonyl": "H alílico/benzílico/α-carbonila",
    "alkynyl": "H acetilênico",
    "alpha_heteroatom": "H em carbono ligado a heteroátomo",
    "vinylic": "H vinílico",
    "aromatic": "H aromático",
    "aldehyde": "H de aldeído",
    "carboxylic_acid": "H de ácido carboxílico",
    "exchangeable": "H trocável (OH/NH/SH)",
    "other": "outro",
}
_HETERO = {"O", "N", "S", "F", "Cl", "Br", "I"}


@dataclass(frozen=True)
class HEnvironment:
    rank: int
    count: int
    h_class: str


def _double_bonded_to_o(atom: Chem.Atom) -> bool:
    return any(
        b.GetBondType() == Chem.BondType.DOUBLE and b.GetOtherAtom(atom).GetSymbol() == "O"
        for b in atom.GetBonds()
    )


def _is_sp2_carbon(atom: Chem.Atom) -> bool:
    return atom.GetSymbol() == "C" and (
        atom.GetIsAromatic() or atom.GetHybridization() == Chem.HybridizationType.SP2
    )


def classify_h(heavy: Chem.Atom) -> str:
    symbol = heavy.GetSymbol()
    if symbol in ("O", "N", "S"):
        if symbol == "O" and any(
            n.GetSymbol() == "C" and _double_bonded_to_o(n) for n in heavy.GetNeighbors()
        ):
            return "carboxylic_acid"
        return "exchangeable"
    if symbol != "C":
        return "other"
    if heavy.GetIsAromatic():
        return "aromatic"
    if _double_bonded_to_o(heavy):
        return "aldehyde"
    if any(
        b.GetBondType() == Chem.BondType.DOUBLE and b.GetOtherAtom(heavy).GetSymbol() == "C"
        for b in heavy.GetBonds()
    ):
        return "vinylic"
    if any(b.GetBondType() == Chem.BondType.TRIPLE for b in heavy.GetBonds()):
        return "alkynyl"
    neighbors = [n for n in heavy.GetNeighbors() if n.GetAtomicNum() != 1]
    if any(n.GetSymbol() in _HETERO for n in neighbors):
        return "alpha_heteroatom"
    if any(_is_sp2_carbon(n) or n.GetSymbol() == "C" and _double_bonded_to_o(n) for n in neighbors):
        return "allylic_benzylic_alpha_carbonyl"
    return "alkyl"


def h_environments(mol: Chem.Mol) -> list[HEnvironment]:
    molh = Chem.AddHs(mol)
    ranks = list(Chem.CanonicalRankAtoms(molh, breakTies=False))
    groups: dict[int, list[Chem.Atom]] = {}
    for atom in molh.GetAtoms():
        if atom.GetAtomicNum() != 1:
            continue
        heavy = atom.GetNeighbors()[0]
        groups.setdefault(ranks[atom.GetIdx()], []).append(heavy)
    return [
        HEnvironment(rank=rank, count=len(heavies), h_class=classify_h(heavies[0]))
        for rank, heavies in sorted(groups.items())
    ]
```

- [ ] **Step 4: Run RDKit tests**

Run: `python -m pytest tests/test_chem_rdkit.py -v`
Expected: all pass.

- [ ] **Step 5: Write the failing comparison tests**

`backend/tests/test_chem_compare.py`:
```python
import pytest

from app.chem.compare import compare_structure_with_data, same_structure
from app.chem.rdkit_tools import SmilesError
from app.nmr_engine.models import Peak

ETHYL_ACETATE = [
    Peak(id="P1", ppm=4.12, integral=2, multiplicity="q", j_hz=[7.1]),
    Peak(id="P2", ppm=2.05, integral=3, multiplicity="s"),
    Peak(id="P3", ppm=1.26, integral=3, multiplicity="t", j_hz=[7.1]),
]


def _status(result):
    return {c["name"]: c["status"] for c in result["checks"]}


def test_correct_structure_passes_all():
    r = compare_structure_with_data("CC(=O)OCC", ETHYL_ACETATE, "C4H8O2")
    assert _status(r) == {
        "formula": "pass",
        "h_count": "pass",
        "environment_count": "pass",
        "environment_integrals": "pass",
        "shift_ranges": "pass",
    }
    assert r["total_h"] == 8
    assert r["limitations"]


def test_wrong_formula_fails():
    r = compare_structure_with_data("CCC(C)=O", ETHYL_ACETATE, "C4H8O2")
    assert _status(r)["formula"] == "fail"


def test_isomer_with_same_checks_documents_limits():
    # methyl propanoate passes the coarse checks: the tutor must reason about shifts/multiplicity
    r = compare_structure_with_data("CCC(=O)OC", ETHYL_ACETATE, "C4H8O2")
    assert "fail" not in _status(r).values()


def test_missing_formula_and_integrals_are_inconclusive():
    peaks = [Peak(id="P1", ppm=1.0)]
    r = compare_structure_with_data("C", peaks, None)
    s = _status(r)
    assert s["formula"] == "inconclusive"
    assert s["h_count"] == "inconclusive"
    assert s["environment_integrals"] == "inconclusive"


def test_toluene_overlap_is_inconclusive_not_fail():
    peaks = [
        Peak(id="P1", ppm=7.25, integral=2, multiplicity="m"),
        Peak(id="P2", ppm=7.15, integral=3, multiplicity="m"),
        Peak(id="P3", ppm=2.36, integral=3, multiplicity="s"),
    ]
    s = _status(compare_structure_with_data("Cc1ccccc1", peaks, "C7H8"))
    assert s["environment_count"] == "inconclusive"
    assert s["h_count"] == "pass"
    assert s["shift_ranges"] == "pass"


def test_shift_range_fail_is_heuristic():
    peaks = [Peak(id="P1", ppm=1.0, integral=6, multiplicity="s")]
    r = compare_structure_with_data("c1ccccc1", peaks, "C6H6")
    check = next(c for c in r["checks"] if c["name"] == "shift_ranges")
    assert check["status"] == "fail" and check["heuristic"] is True


def test_invalid_smiles_raises():
    with pytest.raises(SmilesError):
        compare_structure_with_data("C1CC", ETHYL_ACETATE, None)


def test_same_structure():
    assert same_structure("CC(=O)OCC", "CCOC(C)=O")
    assert not same_structure("CC(=O)OCC", "CCC(=O)OC")
    assert not same_structure("C1CC", "CCO")
```

- [ ] **Step 6: Run to verify failure**

Run: `python -m pytest tests/test_chem_compare.py -v`
Expected: FAIL (module not found).

- [ ] **Step 7: Implement comparison**

`backend/app/chem/compare.py`:
```python
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors

from app.chem.environments import H_CLASS_LABELS, H_CLASS_RANGES, h_environments
from app.chem.formula import normalize_formula
from app.chem.rdkit_tools import SmilesError, inchikey, mol_from_smiles
from app.nmr_engine.models import Peak

LIMITATIONS = [
    "Ambientes de H contados por simetria topológica: não distingue H diastereotópicos nem considera troca rápida.",
    "Faixas de deslocamento são aproximadas (CDCl3) e heurísticas.",
    "Estas checagens não são um veredito de 'estrutura correta'; isômeros podem passar em todas.",
]
SHIFT_TOLERANCE = 0.2


def _check(name: str, status: str, detail: str, heuristic: bool = False) -> dict:
    return {"name": name, "status": status, "detail": detail, "heuristic": heuristic}


def compare_structure_with_data(smiles: str, peaks: list[Peak], molecular_formula: str | None) -> dict:
    mol = mol_from_smiles(smiles)
    formula = rdMolDescriptors.CalcMolFormula(mol)
    envs = h_environments(mol)
    total_h = sum(e.count for e in envs)
    checks: list[dict] = []

    if not molecular_formula:
        checks.append(_check("formula", "inconclusive", "Fórmula molecular não informada."))
    else:
        try:
            same = normalize_formula(molecular_formula) == normalize_formula(formula)
            checks.append(
                _check(
                    "formula",
                    "pass" if same else "fail",
                    f"Estrutura: {formula}; fórmula informada: {normalize_formula(molecular_formula)}.",
                )
            )
        except ValueError:
            checks.append(_check("formula", "inconclusive", "Não foi possível comparar as fórmulas."))

    integrals = [p.integral for p in peaks]
    scaled: list[float] | None = None
    if not peaks:
        checks.append(_check("h_count", "inconclusive", "Nenhum pico informado."))
    elif any(i is None for i in integrals):
        checks.append(_check("h_count", "inconclusive", "Há picos sem integral."))
    else:
        scale = total_h / sum(integrals)
        scaled = [i * scale for i in integrals]
        ok = all(abs(s - round(s)) <= 0.2 and round(s) >= 1 for s in scaled)
        shown = ", ".join(f"{s:.2f}" for s in scaled)
        checks.append(
            _check(
                "h_count",
                "pass" if ok else "fail",
                f"{total_h} H na estrutura; integrais reescaladas para esse total: [{shown}].",
            )
        )

    n_env, n_sig = len(envs), len(peaks)
    if n_env == n_sig:
        checks.append(
            _check("environment_count", "pass", f"{n_env} ambientes de H e {n_sig} sinais.", heuristic=True)
        )
    else:
        checks.append(
            _check(
                "environment_count",
                "inconclusive",
                f"{n_env} ambientes de H previstos e {n_sig} sinais; a diferença pode vir de sobreposição "
                "de sinais, H diastereotópicos, troca rápida ou de uma estrutura incompatível.",
                heuristic=True,
            )
        )

    if scaled is not None and n_env == n_sig:
        expected = sorted(e.count for e in envs)
        observed = sorted(round(s) for s in scaled)
        checks.append(
            _check(
                "environment_integrals",
                "pass" if expected == observed else "fail",
                f"H por ambiente previsto: {expected}; integrais observadas: {observed}.",
                heuristic=True,
            )
        )
    else:
        checks.append(
            _check(
                "environment_integrals",
                "inconclusive",
                "Comparação exige integrais em todos os picos e mesmo número de ambientes e sinais.",
                heuristic=True,
            )
        )

    if not peaks:
        checks.append(_check("shift_ranges", "inconclusive", "Nenhum pico informado.", heuristic=True))
    else:
        missing = []
        for cls in sorted({e.h_class for e in envs}):
            lo, hi = H_CLASS_RANGES[cls]
            if not any(lo - SHIFT_TOLERANCE <= p.ppm <= hi + SHIFT_TOLERANCE for p in peaks):
                missing.append(f"{H_CLASS_LABELS[cls]} ({lo:g}–{hi:g} ppm)")
        if missing:
            checks.append(
                _check(
                    "shift_ranges",
                    "fail",
                    "Nenhum sinal na faixa esperada para: " + "; ".join(missing) + ".",
                    heuristic=True,
                )
            )
        else:
            checks.append(
                _check(
                    "shift_ranges",
                    "pass",
                    "Todos os tipos de H previstos têm algum sinal na faixa aproximada esperada.",
                    heuristic=True,
                )
            )

    return {
        "canonical_smiles": Chem.MolToSmiles(mol),
        "formula": formula,
        "total_h": total_h,
        "h_environments": [
            {
                "count": e.count,
                "h_class": e.h_class,
                "label": H_CLASS_LABELS[e.h_class],
                "expected_range_ppm": list(H_CLASS_RANGES[e.h_class]),
            }
            for e in envs
        ],
        "checks": checks,
        "limitations": LIMITATIONS,
    }


def same_structure(smiles_a: str, smiles_b: str) -> bool:
    try:
        return inchikey(smiles_a) == inchikey(smiles_b)
    except SmilesError:
        return False
```

- [ ] **Step 8: Run tests**

Run: `python -m pytest tests/test_chem_rdkit.py tests/test_chem_compare.py -v`
Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add backend/app/chem backend/tests/test_chem_rdkit.py backend/tests/test_chem_compare.py
git commit -m "feat(chem): RDKit SMILES tools, H environments and structure-vs-data checks

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Exercise catalog (5 curated ¹H exercises, images, REVIEW.md)

Data are **didactic, simulated, not reviewed** (user decision). Values below are typical literature values in CDCl₃; the YAML says so and `reviewed: false`.

**Files:**
- Create: `backend/app/exercises/__init__.py`, `backend/app/exercises/catalog.py`, `backend/app/exercises/data/ex01.yaml` … `ex05.yaml`, `backend/scripts/render_exercise_images.py`, `backend/scripts/build_review_doc.py`
- Create (generated): `backend/app/exercises/images/ex01.png` … `ex05.png`, `docs/exercises/REVIEW.md`
- Test: `backend/tests/test_exercises.py`

**Interfaces:**
- Consumes: `Peak`, `renumber` (Task 3), `simulate_spectrum` (Task 5), `molecular_formula`, `compare_structure_with_data` (Task 6), `normalize_formula` (Task 4).
- Produces:
  - `Exercise(BaseModel)`: `id: str`, `title: str`, `difficulty: int`, `experiment: str`, `metadata: dict` (`frequency_mhz`, `solvent`, `molecular_formula`), `answer_smiles: str`, `answer_name: str`, `reviewed: bool`, `reviewed_by: str | None`, `sources: list[str]`, `notes: str | None`, `peaks: list[Peak]`; method `public_dict() -> dict` (keys `id,title,difficulty,experiment,metadata,reviewed,notes`; never `answer_*`).
  - `load_exercises() -> dict[str, Exercise]` (lru_cached, ordered by `(difficulty, id)`), `get_exercise(exercise_id: str) -> Exercise | None`, `exercise_image_path(exercise_id: str) -> Path`, `IMAGES_DIR: Path`.

- [ ] **Step 1: Write the YAML files**

`backend/app/exercises/data/ex01.yaml`:
```yaml
id: ex01
title: "Exercício 1 — C₂H₆O"
difficulty: 1
experiment: "1H"
metadata: {frequency_mhz: 400, solvent: CDCl3, molecular_formula: C2H6O}
answer_smiles: CCO
answer_name: etanol
reviewed: false
reviewed_by: null
sources: []
notes: "Dados didáticos simulados (valores típicos de literatura, não revisados). O sinal de OH varia com concentração e umidade."
peaks:
  - {ppm: 3.69, integral: 2, multiplicity: q, j_hz: [7.0]}
  - {ppm: 2.00, integral: 1, multiplicity: br_s, note: "posição variável"}
  - {ppm: 1.22, integral: 3, multiplicity: t, j_hz: [7.0]}
```

`backend/app/exercises/data/ex02.yaml`:
```yaml
id: ex02
title: "Exercício 2 — C₄H₈O₂"
difficulty: 2
experiment: "1H"
metadata: {frequency_mhz: 400, solvent: CDCl3, molecular_formula: C4H8O2}
answer_smiles: CCOC(C)=O
answer_name: acetato de etila
reviewed: false
reviewed_by: null
sources: []
notes: "Dados didáticos simulados (valores típicos de literatura, não revisados)."
peaks:
  - {ppm: 4.12, integral: 2, multiplicity: q, j_hz: [7.1]}
  - {ppm: 2.05, integral: 3, multiplicity: s}
  - {ppm: 1.26, integral: 3, multiplicity: t, j_hz: [7.1]}
```

`backend/app/exercises/data/ex03.yaml`:
```yaml
id: ex03
title: "Exercício 3 — C₄H₈O"
difficulty: 2
experiment: "1H"
metadata: {frequency_mhz: 400, solvent: CDCl3, molecular_formula: C4H8O}
answer_smiles: CCC(C)=O
answer_name: 2-butanona
reviewed: false
reviewed_by: null
sources: []
notes: "Dados didáticos simulados (valores típicos de literatura, não revisados)."
peaks:
  - {ppm: 2.44, integral: 2, multiplicity: q, j_hz: [7.3]}
  - {ppm: 2.14, integral: 3, multiplicity: s}
  - {ppm: 1.06, integral: 3, multiplicity: t, j_hz: [7.3]}
```

`backend/app/exercises/data/ex04.yaml`:
```yaml
id: ex04
title: "Exercício 4 — C₇H₈"
difficulty: 3
experiment: "1H"
metadata: {frequency_mhz: 400, solvent: CDCl3, molecular_formula: C7H8}
answer_smiles: Cc1ccccc1
answer_name: tolueno
reviewed: false
reviewed_by: null
sources: []
notes: "Dados didáticos simulados (valores típicos de literatura, não revisados). A região aromática aparece como multipletos sobrepostos."
peaks:
  - {ppm: 7.25, integral: 2, multiplicity: m}
  - {ppm: 7.15, integral: 3, multiplicity: m}
  - {ppm: 2.36, integral: 3, multiplicity: s}
```

`backend/app/exercises/data/ex05.yaml`:
```yaml
id: ex05
title: "Exercício 5 — C₉H₁₀O₂"
difficulty: 4
experiment: "1H"
metadata: {frequency_mhz: 400, solvent: CDCl3, molecular_formula: C9H10O2}
answer_smiles: COc1ccc(cc1)C(C)=O
answer_name: 4'-metoxiacetofenona
reviewed: false
reviewed_by: null
sources: []
notes: "Dados didáticos simulados (valores típicos de literatura, não revisados). Sistema aromático AA'BB' representado como dois dubletos."
peaks:
  - {ppm: 7.94, integral: 2, multiplicity: d, j_hz: [8.9]}
  - {ppm: 6.93, integral: 2, multiplicity: d, j_hz: [8.9]}
  - {ppm: 3.87, integral: 3, multiplicity: s}
  - {ppm: 2.56, integral: 3, multiplicity: s}
```

- [ ] **Step 2: Write the failing tests**

`backend/tests/test_exercises.py`:
```python
import pytest

from app.chem.compare import compare_structure_with_data
from app.chem.formula import normalize_formula
from app.chem.rdkit_tools import molecular_formula
from app.exercises.catalog import exercise_image_path, get_exercise, load_exercises

IDS = ["ex01", "ex02", "ex03", "ex04", "ex05"]


def test_catalog_loads_in_order():
    assert list(load_exercises()) == IDS


def test_public_dict_hides_answers():
    for ex in load_exercises().values():
        d = ex.public_dict()
        assert "answer_smiles" not in d and "answer_name" not in d
        assert ex.answer_name.lower() not in str(d).lower()
        assert d["reviewed"] is False


@pytest.mark.parametrize("exercise_id", IDS)
def test_answer_matches_formula_and_data(exercise_id):
    ex = get_exercise(exercise_id)
    formula = molecular_formula(ex.answer_smiles)["formula"]
    assert normalize_formula(formula) == normalize_formula(ex.metadata["molecular_formula"])
    result = compare_structure_with_data(ex.answer_smiles, ex.peaks, ex.metadata["molecular_formula"])
    assert all(c["status"] != "fail" for c in result["checks"]), result["checks"]


def test_peaks_are_numbered_and_marked_exercise():
    ex = get_exercise("ex02")
    assert [p.id for p in ex.peaks] == ["P1", "P2", "P3"]
    assert all(p.source == "exercise" for p in ex.peaks)


def test_unknown_exercise():
    assert get_exercise("nope") is None


@pytest.mark.parametrize("exercise_id", IDS)
def test_images_exist(exercise_id):
    path = exercise_image_path(exercise_id)
    assert path.exists() and path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
```

- [ ] **Step 3: Run to verify failure**

Run: `python -m pytest tests/test_exercises.py -v`
Expected: FAIL (module not found).

- [ ] **Step 4: Implement the catalog**

`backend/app/exercises/__init__.py`: empty.

`backend/app/exercises/catalog.py`:
```python
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from app.nmr_engine.models import Peak, renumber

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = BASE_DIR / "images"


class Exercise(BaseModel):
    id: str
    title: str
    difficulty: int
    experiment: str = "1H"
    metadata: dict
    answer_smiles: str
    answer_name: str
    reviewed: bool = False
    reviewed_by: str | None = None
    sources: list[str] = Field(default_factory=list)
    notes: str | None = None
    peaks: list[Peak]

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "difficulty": self.difficulty,
            "experiment": self.experiment,
            "metadata": self.metadata,
            "reviewed": self.reviewed,
            "notes": self.notes,
        }


def _load_file(path: Path) -> Exercise:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw_peaks = data.pop("peaks")
    peaks = [Peak(id=f"P{i + 1}", source="exercise", **p) for i, p in enumerate(raw_peaks)]
    return Exercise(peaks=renumber(peaks), **data)


@lru_cache
def load_exercises() -> dict[str, Exercise]:
    items = [_load_file(p) for p in sorted(DATA_DIR.glob("*.yaml"))]
    items.sort(key=lambda e: (e.difficulty, e.id))
    return {e.id: e for e in items}


def get_exercise(exercise_id: str) -> Exercise | None:
    return load_exercises().get(exercise_id)


def exercise_image_path(exercise_id: str) -> Path:
    return IMAGES_DIR / f"{exercise_id}.png"
```

- [ ] **Step 5: Write the image renderer and generate images**

`backend/scripts/render_exercise_images.py`:
```python
"""Render didactic PNGs for the exercise catalog (dev-only; needs matplotlib).

Run from backend/:  python scripts/render_exercise_images.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from app.exercises.catalog import IMAGES_DIR, load_exercises  # noqa: E402
from app.nmr_engine.simulate import multiplet_lines, simulate_spectrum  # noqa: E402

INK = "#1f2937"


def _style(ax) -> None:
    ax.set_yticks([])
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)


def render(exercise) -> Path:
    meta = exercise.metadata
    freq = meta.get("frequency_mhz") or 400
    sim = simulate_spectrum(exercise.peaks, freq)
    zoom = [p for p in exercise.peaks if p.multiplicity not in (None, "s", "br_s")]
    if zoom:
        fig = plt.figure(figsize=(10, 5.8), dpi=150)
        gs = fig.add_gridspec(2, len(zoom), height_ratios=[2.2, 1], hspace=0.45)
        ax = fig.add_subplot(gs[0, :])
    else:
        fig, ax = plt.subplots(figsize=(10, 4), dpi=150)
    ax.plot(sim.x, sim.y, color=INK, linewidth=0.8)
    ax.set_xlim(10.5, -0.3)
    ax.set_ylim(-0.03, 1.18)
    ax.set_xlabel("δ (ppm)")
    _style(ax)
    for p in exercise.peaks:
        if p.integral is not None:
            ax.annotate(f"{p.integral:g}H", (p.ppm, 1.08), ha="center", fontsize=8, color="#374151")
    ax.set_title(
        f"RMN de ¹H ({freq:g} MHz, {meta.get('solvent', '?')}) — {exercise.title} — dados simulados",
        fontsize=9,
    )
    for i, p in enumerate(zoom):
        lines, _ = multiplet_lines(p.ppm, str(p.multiplicity), p.j_hz, freq)
        span = max(pos for pos, _ in lines) - min(pos for pos, _ in lines)
        half = max(0.04, span / 2 + 0.025)
        zax = fig.add_subplot(gs[1, i])
        xs = [x for x in sim.x if p.ppm - half <= x <= p.ppm + half]
        ys = [y for x, y in zip(sim.x, sim.y) if p.ppm - half <= x <= p.ppm + half]
        zax.plot(xs, ys, color=INK, linewidth=0.8)
        zax.set_xlim(p.ppm + half, p.ppm - half)
        zax.tick_params(labelsize=7)
        zax.set_title(f"ampliação {p.ppm:.2f} ppm", fontsize=8)
        _style(zax)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    out = IMAGES_DIR / f"{exercise.id}.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


if __name__ == "__main__":
    for ex in load_exercises().values():
        print(render(ex))
```

Run: `python scripts/render_exercise_images.py`
Expected: prints 5 paths under `app/exercises/images/`. Open one PNG (Read tool) and check the spectrum looks like a ¹H spectrum with the expected multiplets and the integral labels.

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/test_exercises.py -v`
Expected: all pass.

- [ ] **Step 7: Write the review-doc generator and generate `docs/exercises/REVIEW.md`**

`backend/scripts/build_review_doc.py`:
```python
"""Generate docs/exercises/REVIEW.md (checklist for the human reviewer).

Run from backend/:  python scripts/build_review_doc.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.chem.rdkit_tools import molecular_formula  # noqa: E402
from app.exercises.catalog import load_exercises  # noqa: E402

OUT = ROOT.parent / "docs" / "exercises" / "REVIEW.md"
SKILL_FILES = [
    "SKILL.md",
    "proton-nmr.md",
    "carbon-nmr.md",
    "coupling.md",
    "2d-nmr.md",
    "structure-elucidation.md",
]


def main() -> None:
    lines = [
        "# Revisão dos dados químicos — RMN Tutor",
        "",
        "> **Contém as respostas dos exercícios.** Documento para o revisor (professor/autor).",
        "> Gerado por `backend/scripts/build_review_doc.py`; edite os YAML em",
        "> `backend/app/exercises/data/` e rode o script de novo.",
        "",
        "Ao concluir a revisão de um exercício: corrija o YAML se necessário, preencha",
        "`reviewed: true`, `reviewed_by: \"Nome\"`, `sources: [...]`, rode",
        "`python scripts/render_exercise_images.py` e este script, e faça commit.",
        "",
    ]
    for ex in load_exercises().values():
        info = molecular_formula(ex.answer_smiles)
        m = ex.metadata
        lines += [
            f"## {ex.id} — {ex.title}",
            "",
            f"- Resposta: **{ex.answer_name}** — `{ex.answer_smiles}` ({info['formula']}, MW {info['mw']})",
            f"- Condições: {m.get('frequency_mhz')} MHz, {m.get('solvent')}; fórmula informada {m.get('molecular_formula')}",
            f"- Status: reviewed = `{str(ex.reviewed).lower()}`, revisor = {ex.reviewed_by or '—'}",
            "",
            "| ID | δ (ppm) | Integral | Mult. | J (Hz) | Nota |",
            "|---|---|---|---|---|---|",
        ]
        for p in ex.peaks:
            j = ", ".join(f"{v:g}" for v in p.j_hz) if p.j_hz else "—"
            lines.append(
                f"| {p.id} | {p.ppm:g} | {p.integral if p.integral is not None else '—'} | "
                f"{p.multiplicity or '—'} | {j} | {p.note or ''} |"
            )
        lines += [
            "",
            f"![{ex.id}](../../backend/app/exercises/images/{ex.id}.png)",
            "",
            "- [ ] Deslocamentos químicos conferidos",
            "- [ ] Integrais conferidas",
            "- [ ] Multiplicidades conferidas",
            "- [ ] Constantes J conferidas",
            "- [ ] Solvente/frequência coerentes",
            "- [ ] Fonte bibliográfica registrada em `sources`",
            "",
        ]
    lines += [
        "## Skill `nmr-spectroscopy` (conteúdo químico)",
        "",
        "Arquivos em `.claude/skills/nmr-spectroscopy/`. Conferir definições, faixas e fontes citadas.",
        "",
    ]
    lines += [f"- [ ] `{name}`" for name in SKILL_FILES]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
```

Run: `python scripts/build_review_doc.py`
Expected: prints the path; `docs/exercises/REVIEW.md` contains 5 sections and the skill checklist.

- [ ] **Step 8: Commit**

```bash
git add backend/app/exercises backend/scripts backend/tests/test_exercises.py docs/exercises/REVIEW.md
git commit -m "feat(exercises): five unreviewed 1H exercises, rendered images and review checklist

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: `store` — models, migration, repository

**Files:**
- Create: `backend/app/store/__init__.py`, `backend/app/store/db.py`, `backend/app/store/models.py`, `backend/app/store/repo.py`, `backend/alembic.ini`, `backend/migrations/env.py`, `backend/migrations/script.py.mako`, `backend/migrations/versions/0001_initial.py`
- Test: `backend/tests/test_store.py`, `backend/tests/test_migrations.py`; modify `backend/tests/conftest.py` (add `db` fixture)

**Interfaces:**
- Consumes: `get_settings()` (Task 2).
- Produces:
  - `store.db`: `Base`, `normalize_db_url(url: str) -> str`, `get_engine() -> AsyncEngine`, `get_sessionmaker() -> async_sessionmaker[AsyncSession]`, `async create_all() -> None`. Engine is rebuilt when `DATABASE_URL` changes (tests).
  - `store.models`: `SessionRow` (attrs: `id: uuid.UUID`, `owner_uid`, `title`, `experiment`, `meta: dict` (column `metadata`), `exercise_id`, `image_blob`, `image_media_type`, `peaks: list`, `chem_state: dict`, `assist_mode`, `turn_lock_until`, `created_at`, `updated_at`), `MessageRow` (`id`, `session_id`, `seq`, `role`, `content: list | str`, `display_text`, `mode`, `usage: dict | None`, `created_at`), `StructureCheckRow` (`id`, `session_id`, `smiles`, `result: dict`, `created_at`), `RateEventRow` (`id`, `key`, `created_at`).
  - `store.repo`: `utcnow()`, `as_aware(dt)`, dataclass `NewMessage(role, content, display_text=None, mode=None, usage=None)`, and async functions:
    - `create_session(db, *, owner_uid, title, experiment, metadata, peaks, exercise_id, chem_state) -> SessionRow`
    - `get_session(db, session_id: uuid.UUID) -> SessionRow | None`
    - `list_sessions(db, owner_uid: str, limit: int = 50) -> list[SessionRow]`
    - `save(db, row: SessionRow) -> SessionRow` (bumps `updated_at`, commits)
    - `list_messages(db, session_id) -> list[MessageRow]` (by `seq`)
    - `add_messages(db, session_id, items: list[NewMessage], commit: bool = True) -> list[MessageRow]` (assigns consecutive `seq`)
    - `count_messages(db, session_id) -> int`
    - `add_structure_check(db, session_id, smiles: str, result: dict, commit: bool = True) -> StructureCheckRow`
    - `record_rate_event(db, key: str) -> None`, `count_rate_events(db, key: str, since: datetime) -> int`, `purge_rate_events(db, cutoff: datetime) -> int`
    - `acquire_turn_lock(db, session_id, seconds: int) -> bool`, `release_turn_lock(db, session_id) -> None`
    - `session_input_tokens(db, session_id) -> int` (sum of `input_tokens + cache_creation_input_tokens + cache_read_input_tokens` over `usage`)
    - `delete_session(db, session_id) -> SessionRow | None` (deletes messages, checks, session; returns the deleted row so callers can delete its blob)
    - `list_sessions_older_than(db, cutoff: datetime, exercise_id: str | None = None) -> list[SessionRow]`, `list_all_sessions(db, limit: int = 1000) -> list[SessionRow]`, `stats(db) -> dict` (`sessions`, `messages`, `structure_checks`, `input_tokens`, `oldest`, `newest`).

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/conftest.py`:
```python


@pytest.fixture
async def db():
    from app.store.db import create_all, get_sessionmaker

    await create_all()
    async with get_sessionmaker()() as session:
        yield session
```

`backend/tests/test_store.py`:
```python
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
```

`backend/tests/test_migrations.py`:
```python
import sqlite3

from alembic import command
from alembic.config import Config


def test_alembic_upgrade_creates_tables(tmp_path):
    path = tmp_path / "mig.db"
    cfg = Config("alembic.ini")
    cfg.attributes["database_url"] = f"sqlite+aiosqlite:///{path.as_posix()}"
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")
    con = sqlite3.connect(path)
    tables = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
    con.close()
    assert {"sessions", "messages", "structure_checks", "rate_events", "alembic_version"} <= tables


def test_migration_matches_models(tmp_path):
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from sqlalchemy import create_engine

    from app.store import models  # noqa: F401
    from app.store.db import Base

    path = tmp_path / "mig2.db"
    cfg = Config("alembic.ini")
    cfg.attributes["database_url"] = f"sqlite+aiosqlite:///{path.as_posix()}"
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    engine.dispose()
    assert diff == []
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_store.py tests/test_migrations.py -v`
Expected: FAIL (modules / alembic.ini not found).

- [ ] **Step 3: Implement db and models**

`backend/app/store/__init__.py`: empty.

`backend/app/store/db.py`:
```python
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def normalize_db_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None
_engine_url: str | None = None


def get_engine() -> AsyncEngine:
    global _engine, _sessionmaker, _engine_url
    url = normalize_db_url(get_settings().database_url)
    if _engine is None or url != _engine_url:
        if url.startswith("postgresql"):
            # NullPool + no server-side prepared statements: safe behind Neon's pgbouncer on serverless.
            _engine = create_async_engine(url, poolclass=NullPool, connect_args={"prepare_threshold": None})
        else:
            _engine = create_async_engine(url)
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
        _engine_url = url
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    get_engine()
    assert _sessionmaker is not None
    return _sessionmaker


async def create_all() -> None:
    from app.store import models  # noqa: F401

    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

`backend/app/store/models.py`:
```python
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.store.db import Base

JSONType = JSON().with_variant(JSONB(), "postgresql")


def _now() -> datetime:
    return datetime.now(UTC)


class SessionRow(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_uid: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(200))
    experiment: Mapped[str] = mapped_column(String(16), default="1H")
    meta: Mapped[dict] = mapped_column("metadata", JSONType, default=dict)
    exercise_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    image_blob: Mapped[str | None] = mapped_column(String(300), nullable=True)
    image_media_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    peaks: Mapped[list] = mapped_column(JSONType, default=list)
    chem_state: Mapped[dict] = mapped_column(JSONType, default=dict)
    assist_mode: Mapped[str] = mapped_column(String(16), default="tutor")
    turn_lock_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class MessageRow(Base):
    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("session_id", "seq", name="uq_messages_session_seq"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[list | str] = mapped_column(JSONType)
    display_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    usage: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class StructureCheckRow(Base):
    __tablename__ = "structure_checks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    smiles: Mapped[str] = mapped_column(String(300))
    result: Mapped[dict] = mapped_column(JSONType)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class RateEventRow(Base):
    __tablename__ = "rate_events"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(120), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
```

- [ ] **Step 4: Implement the repository**

`backend/app/store/repo.py`:
```python
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
```

- [ ] **Step 5: Alembic configuration and initial migration**

`backend/alembic.ini`:
```ini
[alembic]
script_location = %(here)s/migrations
prepend_sys_path = .
path_separator = os

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console
qualname =

[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

`backend/migrations/env.py`:
```python
import asyncio
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.store import models  # noqa: F401
from app.store.db import Base, normalize_db_url

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    return config.attributes.get("database_url") or normalize_db_url(get_settings().database_url)


def run_migrations_offline() -> None:
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    url = _url()
    kwargs = {"connect_args": {"prepare_threshold": None}} if url.startswith("postgresql") else {}
    engine = create_async_engine(url, poolclass=NullPool, **kwargs)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
```

`backend/migrations/script.py.mako`:
```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

`backend/migrations/versions/0001_initial.py`:
```python
"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-02
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _json():
    return sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_uid", sa.String(64), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("experiment", sa.String(16), nullable=False),
        sa.Column("metadata", _json(), nullable=False),
        sa.Column("exercise_id", sa.String(64), nullable=True),
        sa.Column("image_blob", sa.String(300), nullable=True),
        sa.Column("image_media_type", sa.String(40), nullable=True),
        sa.Column("peaks", _json(), nullable=False),
        sa.Column("chem_state", _json(), nullable=False),
        sa.Column("assist_mode", sa.String(16), nullable=False),
        sa.Column("turn_lock_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sessions_owner_uid", "sessions", ["owner_uid"])
    op.create_index("ix_sessions_updated_at", "sessions", ["updated_at"])
    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", _json(), nullable=False),
        sa.Column("display_text", sa.Text(), nullable=True),
        sa.Column("mode", sa.String(16), nullable=True),
        sa.Column("usage", _json(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "seq", name="uq_messages_session_seq"),
    )
    op.create_index("ix_messages_session_id", "messages", ["session_id"])
    op.create_table(
        "structure_checks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("smiles", sa.String(300), nullable=False),
        sa.Column("result", _json(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_structure_checks_session_id", "structure_checks", ["session_id"])
    op.create_table(
        "rate_events",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_rate_events_key", "rate_events", ["key"])
    op.create_index("ix_rate_events_created_at", "rate_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("rate_events")
    op.drop_table("structure_checks")
    op.drop_table("messages")
    op.drop_table("sessions")
```

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/test_store.py tests/test_migrations.py -v`
Expected: all pass. If `test_migration_matches_models` reports only type-variant noise (e.g. `JSON` vs `JSON().with_variant`) and no missing tables/columns/indexes, fix the model or migration so the diff is empty — do not delete the test.

- [ ] **Step 7: Commit**

```bash
git add backend/app/store backend/alembic.ini backend/migrations backend/tests
git commit -m "feat(store): async SQLAlchemy models, repository and initial Alembic migration

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: `store` — image validation + blob storage

**Files:**
- Create: `backend/app/store/images.py`, `backend/app/store/blob.py`
- Test: `backend/tests/test_images.py`, `backend/tests/test_blob.py`

**Interfaces:**
- Consumes: `get_settings()` (Task 2).
- Produces:
  - `images.ImageError(ValueError)`; `MAX_DIMENSION = 2048`; `sniff_media_type(data: bytes) -> str | None` (`image/png`, `image/jpeg`, `image/webp`); `normalize_image(data: bytes, max_bytes: int) -> tuple[bytes, str]` → re-encoded bytes and output media type (`image/jpeg` for JPEG input, `image/png` otherwise), EXIF removed, orientation applied, long edge ≤ 2048.
  - `blob.BlobStore` (Protocol): `async put(path: str, data: bytes, content_type: str) -> str` (returns stored pathname), `async get(path: str) -> bytes`, `async delete(path: str) -> None`.
  - `blob.MemoryBlobStore`, `blob.VercelBlobStore(token: str | None)` (private access; token None → SDK resolves from env/OIDC), `blob.get_blob_store() -> BlobStore` (singleton per backend kind; `BLOB_BACKEND=vercel` selects Vercel), `blob.reset_blob_store()` (tests).

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_images.py`:
```python
import io

import pytest
from PIL import Image

from app.store.images import MAX_DIMENSION, ImageError, normalize_image, sniff_media_type

MAX = 4 * 1024 * 1024


def _img_bytes(fmt: str, size=(64, 32), exif: bool = False) -> bytes:
    img = Image.new("RGB", size, (200, 10, 10))
    buf = io.BytesIO()
    kwargs = {}
    if exif:
        ex = Image.Exif()
        ex[0x010F] = "CameraMaker"  # Make
        kwargs["exif"] = ex.tobytes()
    img.save(buf, fmt, **kwargs)
    return buf.getvalue()


def test_sniff():
    assert sniff_media_type(_img_bytes("PNG")) == "image/png"
    assert sniff_media_type(_img_bytes("JPEG")) == "image/jpeg"
    assert sniff_media_type(_img_bytes("WEBP")) == "image/webp"
    assert sniff_media_type(b"%PDF-1.7 ...") is None


def test_png_roundtrip():
    out, media = normalize_image(_img_bytes("PNG"), MAX)
    assert media == "image/png"
    assert Image.open(io.BytesIO(out)).size == (64, 32)


def test_jpeg_exif_stripped():
    out, media = normalize_image(_img_bytes("JPEG", exif=True), MAX)
    assert media == "image/jpeg"
    assert dict(Image.open(io.BytesIO(out)).getexif()) == {}


def test_webp_becomes_png():
    _, media = normalize_image(_img_bytes("WEBP"), MAX)
    assert media == "image/png"


def test_large_image_is_downscaled():
    out, _ = normalize_image(_img_bytes("PNG", size=(5000, 1000)), MAX)
    assert max(Image.open(io.BytesIO(out)).size) == MAX_DIMENSION


def test_rejects_non_image_and_oversize():
    with pytest.raises(ImageError, match="(?i)formato"):
        normalize_image(b"<html>not an image</html>", MAX)
    with pytest.raises(ImageError, match="(?i)maior que"):
        normalize_image(b"\x89PNG\r\n\x1a\n" + b"0" * 100, 50)


def test_rejects_corrupt_png():
    with pytest.raises(ImageError, match="corrompid"):
        normalize_image(b"\x89PNG\r\n\x1a\n" + b"garbage" * 10, MAX)
```

`backend/tests/test_blob.py`:
```python
from app.store.blob import MemoryBlobStore, VercelBlobStore, get_blob_store, reset_blob_store


async def test_memory_blob_roundtrip():
    store = MemoryBlobStore()
    path = await store.put("sessions/abc/image.png", b"data", "image/png")
    assert await store.get(path) == b"data"
    await store.delete(path)
    assert path not in store.objects


def test_get_blob_store_selects_backend(monkeypatch):
    from app.config import get_settings

    reset_blob_store()
    assert isinstance(get_blob_store(), MemoryBlobStore)
    monkeypatch.setenv("BLOB_BACKEND", "vercel")
    get_settings.cache_clear()
    reset_blob_store()
    assert isinstance(get_blob_store(), VercelBlobStore)
    reset_blob_store()
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_images.py tests/test_blob.py -v`
Expected: FAIL (modules not found).

- [ ] **Step 3: Implement images**

`backend/app/store/images.py`:
```python
import io

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_DIMENSION = 2048
Image.MAX_IMAGE_PIXELS = 40_000_000  # decompression-bomb guard


class ImageError(ValueError):
    pass


def sniff_media_type(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def normalize_image(data: bytes, max_bytes: int) -> tuple[bytes, str]:
    if len(data) > max_bytes:
        raise ImageError(f"Arquivo maior que o limite de {max_bytes / (1024 * 1024):.0f} MB.")
    media = sniff_media_type(data)
    if media is None:
        raise ImageError("Formato não suportado. Envie PNG, JPEG ou WebP.")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError) as exc:
        raise ImageError("Imagem corrompida ou inválida.") from exc
    img = ImageOps.exif_transpose(img)
    if max(img.size) > MAX_DIMENSION:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
    out = io.BytesIO()
    if media == "image/jpeg":
        img.convert("RGB").save(out, "JPEG", quality=90)
        return out.getvalue(), "image/jpeg"
    if img.mode not in ("RGB", "RGBA", "L", "LA"):
        img = img.convert("RGBA")
    img.save(out, "PNG", optimize=True)
    return out.getvalue(), "image/png"
```

- [ ] **Step 4: Implement blob stores**

`backend/app/store/blob.py`:
```python
import logging
from typing import Protocol

from app.config import get_settings

logger = logging.getLogger("rmn.blob")


class BlobStore(Protocol):
    async def put(self, path: str, data: bytes, content_type: str) -> str: ...
    async def get(self, path: str) -> bytes: ...
    async def delete(self, path: str) -> None: ...


class MemoryBlobStore:
    """Development/test store. Data is lost on restart."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    async def put(self, path: str, data: bytes, content_type: str) -> str:
        self.objects[path] = (data, content_type)
        return path

    async def get(self, path: str) -> bytes:
        return self.objects[path][0]

    async def delete(self, path: str) -> None:
        self.objects.pop(path, None)


class VercelBlobStore:
    """Private Vercel Blob store (token from BLOB_READ_WRITE_TOKEN or OIDC via the SDK)."""

    def __init__(self, token: str | None) -> None:
        self.token = token

    async def put(self, path: str, data: bytes, content_type: str) -> str:
        from vercel.blob import put_async

        res = await put_async(
            path, data, access="private", content_type=content_type, add_random_suffix=True, token=self.token
        )
        return res.pathname

    async def get(self, path: str) -> bytes:
        from vercel.blob import get_async

        res = await get_async(path, access="private", token=self.token)
        return res.content

    async def delete(self, path: str) -> None:
        from vercel.blob import delete_async

        await delete_async(path, token=self.token)


_store: BlobStore | None = None


def get_blob_store() -> BlobStore:
    global _store
    if _store is None:
        settings = get_settings()
        if settings.blob_backend == "vercel":
            _store = VercelBlobStore(settings.blob_read_write_token)
        else:
            logger.warning("Using in-memory blob store (BLOB_BACKEND=memory)")
            _store = MemoryBlobStore()
    return _store


def reset_blob_store() -> None:
    global _store
    _store = None
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_images.py tests/test_blob.py -v`
Expected: all pass. (The real Vercel Blob is exercised in Task 21.)

- [ ] **Step 6: Commit**

```bash
git add backend/app/store/images.py backend/app/store/blob.py backend/tests/test_images.py backend/tests/test_blob.py
git commit -m "feat(store): image validation/re-encode and private blob storage

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: `nmr_tools` — envelope, ChemState operations, tool registry

The registry is Claude's only door to data. Tool list and schemas are fixed and deterministic (prompt-cache friendly); `check_against_answer` is always declared but refuses outside `verify`/`solution` exercise sessions.

**Files:**
- Create: `backend/app/nmr_tools/__init__.py`, `backend/app/nmr_tools/envelope.py`, `backend/app/nmr_tools/state_ops.py`, `backend/app/nmr_tools/registry.py`
- Test: `backend/tests/test_state_ops.py`, `backend/tests/test_nmr_tools.py`

**Interfaces:**
- Consumes: `Peak` (Task 3), queries + `chem.formula` (Task 4), `chem.rdkit_tools`, `chem.compare` (Task 6).
- Produces:
  - `envelope.TOOLS_VERSION = "1"`; `ok(tool, data, warnings=None, limitations=None) -> dict`; `not_available(tool, reason, limitations=None) -> dict` (ok=True, `data={"status":"not_available","reason":...}`); `error(tool, code, message) -> dict` (ok=False, `error={"code","message"}`).
  - `state_ops`: `ChemState`, `SignalNote`, `Hypothesis`, `ProposedStructure`, `StateOpError(ValueError)`, `apply_ops(state: ChemState, raw_ops: list, valid_peak_ids: set[str]) -> ChemState` (all-or-nothing; returns a new object).
  - `registry`: dataclasses `ToolContext(peaks: list[Peak], metadata: dict, chem_state: ChemState, assist_mode: str, has_image: bool, experiment: str = "1H", answer_smiles: str | None = None)`, `ToolOutcome(result: dict, new_state: ChemState | None = None, structure_check: dict | None = None)`; `TOOL_NAMES: list[str]`; `tool_definitions() -> list[dict]` (each `{"name","description","input_schema"}`); `execute_tool(name: str, raw_input, ctx: ToolContext) -> ToolOutcome` (never raises).
  - Tool names (in this order): `get_spectrum_metadata`, `get_peak_list`, `get_peaks_in_region`, `get_peak`, `get_integration`, `calculate_delta`, `calculate_j`, `validate_smiles`, `molecular_formula`, `degrees_of_unsaturation`, `compare_structure_with_data`, `update_session_state`, `check_against_answer`.

- [ ] **Step 1: Write the failing ChemState tests**

`backend/tests/test_state_ops.py`:
```python
import pytest

from app.nmr_tools.state_ops import ChemState, StateOpError, apply_ops

PEAKS = {"P1", "P2", "P3"}


def test_default_state():
    s = ChemState()
    assert s.stage == "observe" and s.hints_given == 0 and s.schema_version == 1


def test_apply_ops_sequence():
    s = apply_ops(
        ChemState(),
        [
            {"op": "set_stage", "stage": "hypothesis"},
            {"op": "add_signal_note", "peak_id": "P1", "interpretation": "CH2 ao lado de CH3"},
            {"op": "add_hypothesis", "text": "grupo etila ligado a O", "by": "student", "evidence": ["P1", "P3"]},
            {"op": "add_unresolved", "text": "singleto em 2,05"},
        ],
        PEAKS,
    )
    assert s.stage == "hypothesis"
    assert s.signal_notes[0].peak_id == "P1"
    assert s.hypotheses[0].id == "H1" and s.hypotheses[0].status == "open"
    assert s.unresolved == ["singleto em 2,05"]
    s2 = apply_ops(
        s,
        [
            {"op": "add_signal_note", "peak_id": "P1", "interpretation": "OCH2", "status": "supported"},
            {"op": "set_hypothesis_status", "hypothesis_id": "H1", "status": "supported"},
            {"op": "resolve_unresolved", "text": "singleto em 2,05"},
        ],
        PEAKS,
    )
    assert len(s2.signal_notes) == 1 and s2.signal_notes[0].interpretation == "OCH2"
    assert s2.hypotheses[0].status == "supported"
    assert s2.unresolved == []
    assert s.hypotheses[0].status == "open"  # original untouched


def test_all_or_nothing():
    s = ChemState()
    with pytest.raises(StateOpError, match="P9"):
        apply_ops(s, [{"op": "set_stage", "stage": "check"}, {"op": "add_signal_note", "peak_id": "P9", "interpretation": "x"}], PEAKS)
    assert s.stage == "observe"


@pytest.mark.parametrize(
    "ops,match",
    [
        ([], "não vazia"),
        ([{"op": "explode"}], "operação inválida"),
        ([{"op": "set_hypothesis_status", "hypothesis_id": "H7", "status": "rejected"}], "H7"),
        ([{"op": "resolve_unresolved", "text": "nada"}], "(?i)pendência"),
        ([{"op": "set_stage", "stage": "observe"}] * 21, "20"),
    ],
)
def test_invalid_ops(ops, match):
    with pytest.raises(StateOpError, match=match):
        apply_ops(ChemState(), ops, PEAKS)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_state_ops.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement envelope and state ops**

`backend/app/nmr_tools/__init__.py`: empty.

`backend/app/nmr_tools/envelope.py`:
```python
TOOLS_VERSION = "1"


def ok(tool: str, data, warnings: list[str] | None = None, limitations: list[str] | None = None) -> dict:
    return {
        "ok": True,
        "tool": tool,
        "version": TOOLS_VERSION,
        "data": data,
        "warnings": warnings or [],
        "limitations": limitations or [],
    }


def not_available(tool: str, reason: str, limitations: list[str] | None = None) -> dict:
    return ok(tool, {"status": "not_available", "reason": reason}, limitations=limitations)


def error(tool: str, code: str, message: str) -> dict:
    return {
        "ok": False,
        "tool": tool,
        "version": TOOLS_VERSION,
        "error": {"code": code, "message": message},
        "warnings": [],
        "limitations": [],
    }
```

`backend/app/nmr_tools/state_ops.py`:
```python
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter, ValidationError

Stage = Literal["observe", "evidence", "hypothesis", "confront", "assemble", "check"]
NoteStatus = Literal["proposed", "supported", "rejected"]
HypStatus = Literal["open", "supported", "rejected"]
MAX_OPS = 20
MAX_NOTES = 100
MAX_HYPOTHESES = 50
MAX_UNRESOLVED = 50


class SignalNote(BaseModel):
    peak_id: str
    interpretation: str = Field(max_length=300)
    status: NoteStatus = "proposed"


class Hypothesis(BaseModel):
    id: str
    text: str = Field(max_length=300)
    by: Literal["student", "tutor"]
    status: HypStatus = "open"
    evidence: list[str] = Field(default_factory=list)


class ProposedStructure(BaseModel):
    smiles: str
    check_id: str | None = None


class ChemState(BaseModel):
    schema_version: Literal[1] = 1
    stage: Stage = "observe"
    signal_notes: list[SignalNote] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)
    hints_given: int = 0
    proposed_structures: list[ProposedStructure] = Field(default_factory=list)


class SetStage(BaseModel):
    op: Literal["set_stage"]
    stage: Stage


class AddSignalNote(BaseModel):
    op: Literal["add_signal_note"]
    peak_id: str
    interpretation: str = Field(min_length=1, max_length=300)
    status: NoteStatus = "proposed"


class AddHypothesis(BaseModel):
    op: Literal["add_hypothesis"]
    text: str = Field(min_length=1, max_length=300)
    by: Literal["student", "tutor"]
    evidence: list[str] = Field(default_factory=list, max_length=20)


class SetHypothesisStatus(BaseModel):
    op: Literal["set_hypothesis_status"]
    hypothesis_id: str
    status: HypStatus


class AddUnresolved(BaseModel):
    op: Literal["add_unresolved"]
    text: str = Field(min_length=1, max_length=200)


class ResolveUnresolved(BaseModel):
    op: Literal["resolve_unresolved"]
    text: str


StateOp = Annotated[
    Union[SetStage, AddSignalNote, AddHypothesis, SetHypothesisStatus, AddUnresolved, ResolveUnresolved],
    Field(discriminator="op"),
]
_OPS = TypeAdapter(list[StateOp])


class StateOpError(ValueError):
    pass


def apply_ops(state: ChemState, raw_ops: list, valid_peak_ids: set[str]) -> ChemState:
    if not isinstance(raw_ops, list) or not raw_ops:
        raise StateOpError("Forneça uma lista 'ops' não vazia.")
    if len(raw_ops) > MAX_OPS:
        raise StateOpError(f"No máximo {MAX_OPS} operações por chamada.")
    try:
        ops = _OPS.validate_python(raw_ops)
    except ValidationError as exc:
        first = exc.errors()[0]
        raise StateOpError(f"operação inválida: {first['msg']} em {list(first['loc'])}") from exc

    new = state.model_copy(deep=True)
    for op in ops:
        if isinstance(op, SetStage):
            new.stage = op.stage
        elif isinstance(op, AddSignalNote):
            if op.peak_id not in valid_peak_ids:
                raise StateOpError(f"Pico desconhecido: {op.peak_id}.")
            new.signal_notes = [n for n in new.signal_notes if n.peak_id != op.peak_id]
            new.signal_notes.append(SignalNote(peak_id=op.peak_id, interpretation=op.interpretation, status=op.status))
        elif isinstance(op, AddHypothesis):
            unknown = [e for e in op.evidence if e not in valid_peak_ids]
            if unknown:
                raise StateOpError(f"Evidência cita picos desconhecidos: {', '.join(unknown)}.")
            if len(new.hypotheses) >= MAX_HYPOTHESES:
                raise StateOpError("Limite de hipóteses atingido.")
            new.hypotheses.append(
                Hypothesis(id=f"H{len(new.hypotheses) + 1}", text=op.text, by=op.by, evidence=op.evidence)
            )
        elif isinstance(op, SetHypothesisStatus):
            hyp = next((h for h in new.hypotheses if h.id == op.hypothesis_id), None)
            if hyp is None:
                raise StateOpError(f"Hipótese desconhecida: {op.hypothesis_id}.")
            hyp.status = op.status
        elif isinstance(op, AddUnresolved):
            if op.text not in new.unresolved:
                if len(new.unresolved) >= MAX_UNRESOLVED:
                    raise StateOpError("Limite de pendências atingido.")
                new.unresolved.append(op.text)
        elif isinstance(op, ResolveUnresolved):
            if op.text not in new.unresolved:
                raise StateOpError(f"Pendência não encontrada: {op.text}.")
            new.unresolved.remove(op.text)
    if len(new.signal_notes) > MAX_NOTES:
        raise StateOpError("Limite de notas de sinal atingido.")
    return new
```

- [ ] **Step 4: Run state tests**

Run: `python -m pytest tests/test_state_ops.py -v`
Expected: all pass.

- [ ] **Step 5: Write the failing registry tests**

`backend/tests/test_nmr_tools.py`:
```python
import json

from app.nmr_engine.models import Peak
from app.nmr_tools.registry import TOOL_NAMES, ToolContext, execute_tool, tool_definitions
from app.nmr_tools.state_ops import ChemState

PEAKS = [
    Peak(id="P1", ppm=4.12, integral=2, multiplicity="q", j_hz=[7.1], source="exercise"),
    Peak(id="P2", ppm=2.05, integral=3, multiplicity="s", source="exercise"),
    Peak(id="P3", ppm=1.26, integral=3, multiplicity="t", j_hz=[7.1], source="exercise"),
]
META = {"frequency_mhz": 400, "solvent": "CDCl3", "molecular_formula": "C4H8O2"}


def ctx(**kw):
    base = dict(peaks=PEAKS, metadata=META, chem_state=ChemState(), assist_mode="tutor", has_image=True)
    base.update(kw)
    return ToolContext(**base)


def _contains_key(obj, key):
    if isinstance(obj, dict):
        return key in obj or any(_contains_key(v, key) for v in obj.values())
    if isinstance(obj, list):
        return any(_contains_key(v, key) for v in obj)
    return False


def test_definitions_are_fixed_and_clean():
    defs = tool_definitions()
    assert [d["name"] for d in defs] == TOOL_NAMES
    assert len(TOOL_NAMES) == 13
    for d in defs:
        assert d["input_schema"]["type"] == "object"
        assert d["description"]
        assert not _contains_key(d["input_schema"], "title")
    assert json.dumps(defs, sort_keys=True) == json.dumps(tool_definitions(), sort_keys=True)


def test_envelope_shape():
    r = execute_tool("get_peak_list", {}, ctx()).result
    assert set(r) >= {"ok", "tool", "version", "data", "warnings", "limitations"}
    assert r["ok"] and r["version"] == "1" and len(r["data"]["peaks"]) == 3


def test_metadata_tool():
    r = execute_tool("get_spectrum_metadata", {}, ctx()).result
    assert r["data"]["degrees_of_unsaturation"] == 1
    assert r["data"]["image_available"] is True
    r2 = execute_tool("get_spectrum_metadata", {}, ctx(metadata={})).result
    assert "molecular_formula" in r2["warnings"][0]


def test_image_only_session_numeric_tools_not_available():
    c = ctx(peaks=[])
    for name, args in [
        ("get_peak_list", {}),
        ("get_peaks_in_region", {"ppm_start": 0, "ppm_end": 10}),
        ("get_peak", {"ppm": 2.0}),
        ("get_integration", {"ppm_start": 0, "ppm_end": 10}),
    ]:
        r = execute_tool(name, args, c).result
        assert r["ok"] and r["data"]["status"] == "not_available", name


def test_region_and_peak():
    r = execute_tool("get_peaks_in_region", {"ppm_start": 6, "ppm_end": 8}, ctx()).result
    assert r["data"]["peaks"] == [] and r["warnings"]
    r = execute_tool("get_peak", {"ppm": 2.07}, ctx()).result
    assert r["data"]["peak"]["id"] == "P2"
    r = execute_tool("get_peak", {"peak_id": "P1", "ppm": 4.1}, ctx()).result
    assert r["ok"] is False and r["error"]["code"] == "invalid_input"


def test_integration_normalized():
    r = execute_tool("get_integration", {"ppm_start": 3.5, "ppm_end": 4.5}, ctx()).result
    assert r["data"]["normalized_h"] == 2.0 and r["limitations"]
    no_int = [Peak(id="P1", ppm=4.0)]
    r2 = execute_tool("get_integration", {"ppm_start": 3, "ppm_end": 5}, ctx(peaks=no_int)).result
    assert r2["data"]["status"] == "not_available"


def test_delta_and_j():
    r = execute_tool("calculate_delta", {"peak_a": "P1", "peak_b": "P3"}, ctx()).result
    assert r["data"]["delta_ppm"] == 2.86 and r["data"]["delta_hz"] == 1144.0
    r = execute_tool("calculate_j", {"peak_id": "P1"}, ctx()).result
    assert r["data"]["j_hz"] == [7.1]
    r = execute_tool("calculate_j", {"peak_id": "P2"}, ctx()).result
    assert r["data"]["status"] == "not_available" and r["limitations"]
    r = execute_tool("calculate_delta", {"peak_a": "P1", "peak_b": "P9"}, ctx()).result
    assert r["ok"] is False and r["error"]["code"] == "unknown_peak"


def test_chem_tools():
    assert execute_tool("validate_smiles", {"smiles": "C1CC"}, ctx()).result["data"]["valid"] is False
    assert execute_tool("molecular_formula", {"smiles": "CCOC(C)=O"}, ctx()).result["data"]["formula"] == "C4H8O2"
    assert execute_tool("degrees_of_unsaturation", {}, ctx()).result["data"]["degrees_of_unsaturation"] == 1
    out = execute_tool("compare_structure_with_data", {"smiles": "CCOC(C)=O"}, ctx())
    assert out.result["ok"] and out.structure_check["formula"] == "C4H8O2"
    bad = execute_tool("molecular_formula", {"smiles": "C1CC"}, ctx()).result
    assert bad["ok"] is False and bad["error"]["code"] == "invalid_smiles"


def test_update_session_state():
    out = execute_tool(
        "update_session_state",
        {"ops": [{"op": "add_hypothesis", "text": "etila em éster", "by": "student", "evidence": ["P1"]}]},
        ctx(),
    )
    assert out.result["ok"] and out.new_state.hypotheses[0].id == "H1"
    bad = execute_tool("update_session_state", {"ops": [{"op": "add_signal_note", "peak_id": "P9", "interpretation": "x"}]}, ctx())
    assert bad.result["ok"] is False and bad.new_state is None


def test_check_against_answer_guarded():
    answer = "CCOC(C)=O"
    r = execute_tool("check_against_answer", {"smiles": answer}, ctx(answer_smiles=answer)).result
    assert r["error"]["code"] == "mode_not_allowed"
    r = execute_tool("check_against_answer", {"smiles": "CCC(=O)OC"}, ctx(answer_smiles=answer, assist_mode="verify")).result
    assert r["data"] == {"same_structure": False}
    r = execute_tool("check_against_answer", {"smiles": "CCOC(C)=O"}, ctx(answer_smiles=answer, assist_mode="solution")).result
    assert r["data"] == {"same_structure": True}
    r = execute_tool("check_against_answer", {"smiles": answer}, ctx(assist_mode="verify")).result
    assert r["error"]["code"] == "not_available_for_session"


def test_unknown_tool_and_bad_input():
    assert execute_tool("rm_rf", {}, ctx()).result["error"]["code"] == "unknown_tool"
    assert execute_tool("get_peaks_in_region", {"ppm_start": "x"}, ctx()).result["error"]["code"] == "invalid_input"
    assert execute_tool("get_peaks_in_region", "not a dict", ctx()).result["error"]["code"] == "invalid_input"
```

- [ ] **Step 6: Run to verify failure**

Run: `python -m pytest tests/test_nmr_tools.py -v`
Expected: FAIL (module not found).

- [ ] **Step 7: Implement the registry**

`backend/app/nmr_tools/registry.py`:
```python
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.chem.compare import compare_structure_with_data, same_structure
from app.chem.formula import degrees_of_unsaturation, hydrogen_count
from app.chem.rdkit_tools import SmilesError, molecular_formula, validate_smiles
from app.nmr_engine.models import Peak
from app.nmr_engine.queries import delta_between, find_peak, integrate_region, peaks_in_region
from app.nmr_tools.envelope import error, not_available, ok
from app.nmr_tools.state_ops import ChemState, StateOpError, apply_ops

logger = logging.getLogger("rmn.tools")

NO_PEAKS_REASON = (
    "Nenhuma lista de picos foi fornecida nesta sessão. Não estime valores numéricos a partir da imagem; "
    "peça ao aluno que digite a lista de picos se precisar de números."
)
INTEGRAL_LIMITATION = "Integrais vêm da tabela informada (usuário/exercício); não são medidas da imagem."
J_LIMITATION = "No MVP, J não é estimado a partir da imagem; só valores informados na tabela."


@dataclass
class ToolContext:
    peaks: list[Peak]
    metadata: dict
    chem_state: ChemState
    assist_mode: str
    has_image: bool
    experiment: str = "1H"
    answer_smiles: str | None = None


@dataclass
class ToolOutcome:
    result: dict
    new_state: ChemState | None = None
    structure_check: dict | None = None


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NoInput(_Strict):
    pass


class RegionInput(_Strict):
    ppm_start: float = Field(ge=-5, le=20, description="Limite da região em ppm.")
    ppm_end: float = Field(ge=-5, le=20, description="Outro limite da região em ppm (qualquer ordem).")


class PeakQueryInput(_Strict):
    peak_id: str | None = Field(default=None, description="ID do pico, ex. 'P2'.")
    ppm: float | None = Field(default=None, description="Deslocamento aproximado em ppm.")
    tolerance_ppm: float = Field(default=0.05, gt=0, le=1, description="Tolerância ao buscar por ppm.")

    @model_validator(mode="after")
    def _exactly_one(self) -> "PeakQueryInput":
        if (self.peak_id is None) == (self.ppm is None):
            raise ValueError("informe exatamente um entre peak_id e ppm")
        return self


class TwoPeaksInput(_Strict):
    peak_a: str = Field(description="ID do primeiro pico.")
    peak_b: str = Field(description="ID do segundo pico.")


class PeakIdInput(_Strict):
    peak_id: str = Field(description="ID do pico, ex. 'P1'.")


class SmilesInput(_Strict):
    smiles: str = Field(min_length=1, max_length=300, description="Estrutura em SMILES.")


class DbeInput(_Strict):
    formula: str | None = Field(default=None, description="Fórmula molecular, ex. 'C4H8O2'.")
    smiles: str | None = Field(default=None, description="Alternativamente, uma estrutura em SMILES.")


class StateInput(_Strict):
    ops: list[dict] = Field(
        min_length=1,
        max_length=20,
        description=(
            "Lista de operações aplicadas em ordem (todas ou nenhuma). Formatos: "
            "{op:'set_stage', stage:'observe|evidence|hypothesis|confront|assemble|check'}; "
            "{op:'add_signal_note', peak_id:'P1', interpretation:'...', status:'proposed|supported|rejected'}; "
            "{op:'add_hypothesis', text:'...', by:'student|tutor', evidence:['P1']}; "
            "{op:'set_hypothesis_status', hypothesis_id:'H1', status:'open|supported|rejected'}; "
            "{op:'add_unresolved', text:'...'}; {op:'resolve_unresolved', text:'...'}."
        ),
    )


def _peak_dict(p: Peak) -> dict:
    return {
        "id": p.id,
        "ppm": p.ppm,
        "integral": p.integral,
        "multiplicity": str(p.multiplicity) if p.multiplicity else None,
        "j_hz": p.j_hz,
        "note": p.note,
    }


def _formula_h(ctx: ToolContext) -> int | None:
    formula = (ctx.metadata or {}).get("molecular_formula")
    try:
        return hydrogen_count(formula) if formula else None
    except ValueError:
        return None


def _t_metadata(ctx: ToolContext, _: NoInput) -> ToolOutcome:
    m = ctx.metadata or {}
    formula = m.get("molecular_formula")
    try:
        dbe = degrees_of_unsaturation(formula) if formula else None
    except ValueError:
        dbe = None
    data = {
        "experiment": ctx.experiment,
        "frequency_mhz": m.get("frequency_mhz"),
        "solvent": m.get("solvent"),
        "molecular_formula": formula,
        "degrees_of_unsaturation": dbe,
        "n_peaks": len(ctx.peaks),
        "all_peaks_have_integrals": bool(ctx.peaks) and all(p.integral is not None for p in ctx.peaks),
        "image_available": ctx.has_image,
    }
    missing = [k for k in ("frequency_mhz", "solvent", "molecular_formula") if not m.get(k)]
    warnings = [f"Não informado: {', '.join(missing)}."] if missing else []
    return ToolOutcome(ok("get_spectrum_metadata", data, warnings))


def _t_peak_list(ctx: ToolContext, _: NoInput) -> ToolOutcome:
    if not ctx.peaks:
        return ToolOutcome(not_available("get_peak_list", NO_PEAKS_REASON))
    return ToolOutcome(ok("get_peak_list", {"peaks": [_peak_dict(p) for p in ctx.peaks]}))


def _t_region(ctx: ToolContext, inp: RegionInput) -> ToolOutcome:
    if not ctx.peaks:
        return ToolOutcome(not_available("get_peaks_in_region", NO_PEAKS_REASON))
    found = peaks_in_region(ctx.peaks, inp.ppm_start, inp.ppm_end)
    warnings = [] if found else ["Nenhum pico da tabela nesta região."]
    lo, hi = sorted((inp.ppm_start, inp.ppm_end))
    data = {"region_ppm": [lo, hi], "peaks": [_peak_dict(p) for p in found]}
    return ToolOutcome(ok("get_peaks_in_region", data, warnings))


def _t_peak(ctx: ToolContext, inp: PeakQueryInput) -> ToolOutcome:
    if not ctx.peaks:
        return ToolOutcome(not_available("get_peak", NO_PEAKS_REASON))
    p = find_peak(ctx.peaks, peak_id=inp.peak_id, ppm=inp.ppm, tolerance_ppm=inp.tolerance_ppm)
    if p is None:
        return ToolOutcome(not_available("get_peak", "Nenhum pico corresponde à consulta."))
    return ToolOutcome(ok("get_peak", {"peak": _peak_dict(p)}))


def _t_integration(ctx: ToolContext, inp: RegionInput) -> ToolOutcome:
    if not ctx.peaks:
        return ToolOutcome(not_available("get_integration", NO_PEAKS_REASON))
    r = integrate_region(ctx.peaks, inp.ppm_start, inp.ppm_end, _formula_h(ctx))
    if r["missing_integrals"]:
        return ToolOutcome(
            not_available(
                "get_integration",
                f"Picos sem integral na região: {', '.join(r['missing_integrals'])}.",
                [INTEGRAL_LIMITATION],
            )
        )
    warnings = [] if r["peak_ids"] else ["Nenhum pico da tabela nesta região."]
    if r["peak_ids"] and r["normalized_h"] is None:
        warnings.append("Sem normalização: falta fórmula molecular ou integral em algum pico do espectro.")
    return ToolOutcome(ok("get_integration", r, warnings, [INTEGRAL_LIMITATION]))


def _t_delta(ctx: ToolContext, inp: TwoPeaksInput) -> ToolOutcome:
    a = find_peak(ctx.peaks, peak_id=inp.peak_a)
    b = find_peak(ctx.peaks, peak_id=inp.peak_b)
    missing = [pid for pid, p in ((inp.peak_a, a), (inp.peak_b, b)) if p is None]
    if missing:
        return ToolOutcome(error("calculate_delta", "unknown_peak", f"Pico(s) desconhecido(s): {', '.join(missing)}."))
    freq = (ctx.metadata or {}).get("frequency_mhz")
    data = {"peak_a": inp.peak_a, "peak_b": inp.peak_b, **delta_between(a, b, freq)}
    warnings = [] if freq else ["Frequência não informada: Δ em Hz indisponível."]
    return ToolOutcome(ok("calculate_delta", data, warnings))


def _t_j(ctx: ToolContext, inp: PeakIdInput) -> ToolOutcome:
    p = find_peak(ctx.peaks, peak_id=inp.peak_id)
    if p is None:
        return ToolOutcome(error("calculate_j", "unknown_peak", f"Pico desconhecido: {inp.peak_id}."))
    if not p.j_hz:
        return ToolOutcome(not_available("calculate_j", f"J não informado para {p.id}.", [J_LIMITATION]))
    data = {"peak_id": p.id, "multiplicity": str(p.multiplicity) if p.multiplicity else None, "j_hz": p.j_hz}
    return ToolOutcome(ok("calculate_j", data, limitations=[J_LIMITATION]))


def _t_validate(ctx: ToolContext, inp: SmilesInput) -> ToolOutcome:
    return ToolOutcome(ok("validate_smiles", validate_smiles(inp.smiles)))


def _t_formula(ctx: ToolContext, inp: SmilesInput) -> ToolOutcome:
    try:
        return ToolOutcome(ok("molecular_formula", molecular_formula(inp.smiles)))
    except SmilesError as exc:
        return ToolOutcome(error("molecular_formula", "invalid_smiles", str(exc)))


def _t_dbe(ctx: ToolContext, inp: DbeInput) -> ToolOutcome:
    try:
        if inp.formula:
            formula = inp.formula
        elif inp.smiles:
            formula = molecular_formula(inp.smiles)["formula"]
        else:
            formula = (ctx.metadata or {}).get("molecular_formula")
        if not formula:
            return ToolOutcome(not_available("degrees_of_unsaturation", "Nenhuma fórmula disponível."))
        value = degrees_of_unsaturation(formula)
    except SmilesError as exc:
        return ToolOutcome(error("degrees_of_unsaturation", "invalid_smiles", str(exc)))
    except ValueError as exc:
        return ToolOutcome(error("degrees_of_unsaturation", "invalid_formula", str(exc)))
    return ToolOutcome(ok("degrees_of_unsaturation", {"formula": formula, "degrees_of_unsaturation": value}))


def _t_compare(ctx: ToolContext, inp: SmilesInput) -> ToolOutcome:
    try:
        result = compare_structure_with_data(inp.smiles, ctx.peaks, (ctx.metadata or {}).get("molecular_formula"))
    except SmilesError as exc:
        return ToolOutcome(error("compare_structure_with_data", "invalid_smiles", str(exc)))
    return ToolOutcome(
        ok("compare_structure_with_data", result, limitations=result["limitations"]),
        structure_check=result,
    )


def _t_state(ctx: ToolContext, inp: StateInput) -> ToolOutcome:
    try:
        new = apply_ops(ctx.chem_state, inp.ops, {p.id for p in ctx.peaks})
    except StateOpError as exc:
        return ToolOutcome(error("update_session_state", "invalid_state_op", str(exc)))
    return ToolOutcome(ok("update_session_state", {"chem_state": new.model_dump()}), new_state=new)


def _t_answer(ctx: ToolContext, inp: SmilesInput) -> ToolOutcome:
    name = "check_against_answer"
    if not ctx.answer_smiles:
        return ToolOutcome(error(name, "not_available_for_session", "Disponível apenas em sessões de exercício."))
    if ctx.assist_mode not in ("verify", "solution"):
        return ToolOutcome(error(name, "mode_not_allowed", "Disponível apenas nos modos Verificação ou Solução."))
    check = validate_smiles(inp.smiles)
    if not check["valid"]:
        return ToolOutcome(error(name, "invalid_smiles", check["error"]))
    return ToolOutcome(
        ok(
            name,
            {"same_structure": same_structure(inp.smiles, ctx.answer_smiles)},
            limitations=["Compara apenas identidade estrutural (InChIKey); não revela a resposta."],
        )
    )


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_model: type[BaseModel]
    handler: Callable[[ToolContext, BaseModel], ToolOutcome]


TOOLS: list[ToolSpec] = [
    ToolSpec("get_spectrum_metadata", "Metadados da sessão: experimento, frequência, solvente, fórmula molecular, IDH, número de picos e se há imagem.", NoInput, _t_metadata),
    ToolSpec("get_peak_list", "Lista oficial de picos (δ em ppm, integral, multiplicidade, J em Hz). Use estes valores, nunca estimativas da imagem.", NoInput, _t_peak_list),
    ToolSpec("get_peaks_in_region", "Picos da tabela dentro de uma região de deslocamento químico.", RegionInput, _t_region),
    ToolSpec("get_peak", "Um pico pelo ID ou pelo deslocamento aproximado.", PeakQueryInput, _t_peak),
    ToolSpec("get_integration", "Soma das integrais informadas numa região e, se houver fórmula, o número de H correspondente.", RegionInput, _t_integration),
    ToolSpec("calculate_delta", "Diferença de deslocamento entre dois picos, em ppm e Hz.", TwoPeaksInput, _t_delta),
    ToolSpec("calculate_j", "Constantes de acoplamento J informadas para um pico (não estima J da imagem).", PeakIdInput, _t_j),
    ToolSpec("validate_smiles", "Valida um SMILES e devolve a forma canônica.", SmilesInput, _t_validate),
    ToolSpec("molecular_formula", "Fórmula molecular, massa molar e massa exata de um SMILES.", SmilesInput, _t_formula),
    ToolSpec("degrees_of_unsaturation", "Índice de deficiência de hidrogênio (IDH) de uma fórmula, de um SMILES ou da fórmula da sessão.", DbeInput, _t_dbe),
    ToolSpec("compare_structure_with_data", "Checagens determinísticas de uma estrutura proposta contra os dados: fórmula, total de H, ambientes de H, integrais e faixas de δ (heurísticas). Não é veredito.", SmilesInput, _t_compare),
    ToolSpec("update_session_state", "Registra o estado do raciocínio: etapa, notas por sinal, hipóteses e pendências.", StateInput, _t_state),
    ToolSpec("check_against_answer", "Somente em exercícios, nos modos Verificação ou Solução: diz se o SMILES é a mesma estrutura da resposta, sem revelá-la.", SmilesInput, _t_answer),
]
TOOL_NAMES = [t.name for t in TOOLS]
_BY_NAME = {t.name: t for t in TOOLS}


def _strip_titles(obj):
    if isinstance(obj, dict):
        return {k: _strip_titles(v) for k, v in obj.items() if k != "title"}
    if isinstance(obj, list):
        return [_strip_titles(v) for v in obj]
    return obj


@lru_cache
def _definitions() -> tuple[dict, ...]:
    return tuple(
        {"name": t.name, "description": t.description, "input_schema": _strip_titles(t.input_model.model_json_schema())}
        for t in TOOLS
    )


def tool_definitions() -> list[dict]:
    return [dict(d) for d in _definitions()]


def execute_tool(name: str, raw_input, ctx: ToolContext) -> ToolOutcome:
    spec = _BY_NAME.get(name)
    if spec is None:
        return ToolOutcome(error(name, "unknown_tool", f"Ferramenta desconhecida: {name}."))
    try:
        inp = spec.input_model.model_validate(raw_input if isinstance(raw_input, dict) else None)
    except ValidationError as exc:
        first = exc.errors()[0]
        return ToolOutcome(error(name, "invalid_input", f"{first['msg']} em {list(first['loc'])}"))
    try:
        return spec.handler(ctx, inp)
    except Exception:
        logger.exception("tool_failed", extra={"fields": {"tool": name}})
        return ToolOutcome(error(name, "internal_error", "Falha interna ao executar a ferramenta."))
```

- [ ] **Step 8: Run tests**

Run: `python -m pytest tests/test_state_ops.py tests/test_nmr_tools.py -v`
Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add backend/app/nmr_tools backend/tests/test_state_ops.py backend/tests/test_nmr_tools.py
git commit -m "feat(nmr_tools): tool envelope, ChemState operations and deterministic tool registry

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: API — identity, sessions, exercises, parse, spectrum, image, structure-check

**Files:**
- Create: `backend/app/api/deps.py`, `backend/app/api/schemas.py`, `backend/app/api/routes_sessions.py`
- Modify: `backend/app/api/routes_misc.py` (replace whole file: health with DB check, exercises, peaks/parse; spike route removed), `backend/app/main.py` (replace whole file: lifespan + routers)
- Delete: `backend/tests/test_spike.py`
- Test: `backend/tests/test_api_sessions.py`; append `client` fixture to `backend/tests/conftest.py`

**Interfaces:**
- Consumes: Tasks 2–10 (`ApiError`, `Peak`, `renumber`, `parse_peak_text`, `simulate_spectrum`, `compare_structure_with_data`, `same_structure`, `SmilesError`, catalog functions, `repo`, `get_sessionmaker`, `create_all`, `get_blob_store`, `normalize_image`, `ImageError`, `ChemState`).
- Produces:
  - `deps.COOKIE_NAME = "rmn_uid"`; `get_db()` (async generator of `AsyncSession`); dataclass `Identity(uid: str, ip: str)`; `get_identity(request, response) -> Identity` (sets signed cookie when absent/invalid); `load_session(session_id: uuid.UUID, db) -> SessionRow` (404 `session_not_found`).
  - `schemas`: `SessionMetadata`, `CreateSessionIn`, `UpdateSessionIn`, `MessageOut`, `ExerciseInfo`, `SessionOut`, `SessionSummary`, `ParsePeaksIn`, `ParsePeaksOut`, `SpectrumOut`, `StructureCheckIn`, `AssistMode = Literal["tutor","hint","verify","solution"]`; helper `session_out(row: SessionRow, messages: list[MessageRow]) -> SessionOut`.
  - HTTP (all under `/api`): `GET /health` → `{"status","version","rdkit","db"}`; `GET /exercises`; `POST /peaks/parse`; `POST /sessions` (201 → `{"id"}`); `GET /sessions`; `GET /sessions/{id}`; `PATCH /sessions/{id}`; `POST /sessions/{id}/image`; `GET /sessions/{id}/image`; `GET /sessions/{id}/spectrum`; `POST /sessions/{id}/structure-check`.
  - Error codes used: `session_not_found` (404), `exercise_not_found` (404), `exercise_read_only` (409), `invalid_image` (422), `image_not_found` (404), `invalid_smiles` (422), `validation_error` (422).

- [ ] **Step 1: Write the failing API tests**

Append to `backend/tests/conftest.py`:
```python


@pytest.fixture
async def client():
    import httpx

    from app.main import create_app
    from app.store.blob import reset_blob_store
    from app.store.db import create_all

    reset_blob_store()
    await create_all()
    app = create_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c
    reset_blob_store()
```

`backend/tests/test_api_sessions.py`:
```python
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
```

Delete `backend/tests/test_spike.py` (`git rm backend/tests/test_spike.py`).

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_api_sessions.py -v`
Expected: FAIL (404s / import errors: routes not implemented).

- [ ] **Step 3: Implement deps and schemas**

`backend/app/api/deps.py`:
```python
import secrets
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

from fastapi import Depends, Request, Response
from itsdangerous import BadSignature, URLSafeSerializer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.errors import ApiError
from app.store import repo
from app.store.db import get_sessionmaker
from app.store.models import SessionRow

COOKIE_NAME = "rmn_uid"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(get_settings().session_secret, salt="rmn-uid")


async def get_db() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session


@dataclass
class Identity:
    uid: str
    ip: str


def get_identity(request: Request, response: Response) -> Identity:
    uid = None
    raw = request.cookies.get(COOKIE_NAME)
    if raw:
        try:
            value = _serializer().loads(raw)
            uid = value if isinstance(value, str) and 8 <= len(value) <= 64 else None
        except BadSignature:
            uid = None
    if uid is None:
        uid = secrets.token_urlsafe(16)
        response.set_cookie(
            COOKIE_NAME,
            _serializer().dumps(uid),
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            secure=get_settings().cookie_secure,
            samesite="lax",
            path="/",
        )
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")
    return Identity(uid=uid, ip=ip)


async def load_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> SessionRow:
    row = await repo.get_session(db, session_id)
    if row is None:
        raise ApiError(404, "session_not_found", "Sessão não encontrada.")
    return row
```

Note: `load_session` and the route handler must share the same `AsyncSession`; FastAPI caches `get_db` per request, so declaring `db: AsyncSession = Depends(get_db)` in the handler returns the same session object.

`backend/app/api/schemas.py`:
```python
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.chem.formula import parse_formula
from app.exercises.catalog import get_exercise
from app.nmr_engine.models import MAX_PEAKS, Peak
from app.store.models import MessageRow, SessionRow
from app.store.repo import as_aware

AssistMode = Literal["tutor", "hint", "verify", "solution"]
ExperimentIn = Literal["1H"]  # Experiment enum declares 13C/DEPT/COSY/HSQC/HMBC for later; MVP accepts only 1H


class SessionMetadata(BaseModel):
    frequency_mhz: float | None = Field(default=None, gt=0, le=2000)
    solvent: str | None = Field(default=None, max_length=40)
    molecular_formula: str | None = Field(default=None, max_length=60)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("molecular_formula")
    @classmethod
    def _formula(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        parse_formula(v)
        return v.strip()


class CreateSessionIn(BaseModel):
    experiment: ExperimentIn = "1H"
    metadata: SessionMetadata = Field(default_factory=SessionMetadata)
    peaks: list[Peak] = Field(default_factory=list, max_length=MAX_PEAKS)
    exercise_id: str | None = Field(default=None, max_length=64)
    title: str | None = Field(default=None, max_length=200)


class UpdateSessionIn(BaseModel):
    metadata: SessionMetadata | None = None
    peaks: list[Peak] | None = Field(default=None, max_length=MAX_PEAKS)
    assist_mode: AssistMode | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)


class MessageOut(BaseModel):
    seq: int
    role: Literal["user", "assistant"]
    text: str
    mode: str | None
    created_at: datetime


class ExerciseInfo(BaseModel):
    id: str
    title: str
    reviewed: bool
    notes: str | None


class SessionOut(BaseModel):
    id: uuid.UUID
    title: str
    experiment: str
    metadata: dict
    exercise: ExerciseInfo | None
    has_image: bool
    peaks: list[Peak]
    chem_state: dict
    assist_mode: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut]


class SessionSummary(BaseModel):
    id: uuid.UUID
    title: str
    exercise_id: str | None
    updated_at: datetime


class ParsePeaksIn(BaseModel):
    text: str = Field(max_length=20000)


class ParseErrorOut(BaseModel):
    line: int
    message: str


class ParsePeaksOut(BaseModel):
    peaks: list[Peak]
    errors: list[ParseErrorOut]


class SpectrumOut(BaseModel):
    x: list[float]
    y: list[float]
    warnings: list[str]


class StructureCheckIn(BaseModel):
    smiles: str = Field(min_length=1, max_length=300)


def session_out(row: SessionRow, messages: list[MessageRow]) -> SessionOut:
    exercise = get_exercise(row.exercise_id) if row.exercise_id else None
    return SessionOut(
        id=row.id,
        title=row.title,
        experiment=row.experiment,
        metadata=row.meta or {},
        exercise=ExerciseInfo(id=exercise.id, title=exercise.title, reviewed=exercise.reviewed, notes=exercise.notes)
        if exercise
        else None,
        has_image=bool(row.image_blob) or exercise is not None,
        peaks=[Peak.model_validate(p) for p in row.peaks or []],
        chem_state=row.chem_state or {},
        assist_mode=row.assist_mode,
        created_at=as_aware(row.created_at),
        updated_at=as_aware(row.updated_at),
        messages=[
            MessageOut(seq=m.seq, role=m.role, text=m.display_text, mode=m.mode, created_at=as_aware(m.created_at))
            for m in messages
            if m.display_text is not None and m.role in ("user", "assistant")
        ],
    )
```

- [ ] **Step 4: Implement routes**

`backend/app/api/routes_misc.py` (replace whole file):
```python
import rdkit
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.schemas import ParseErrorOut, ParsePeaksIn, ParsePeaksOut
from app.config import get_settings
from app.exercises.catalog import load_exercises
from app.nmr_engine.parser import parse_peak_text

router = APIRouter()


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict:
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {"status": "ok", "version": get_settings().app_version, "rdkit": rdkit.__version__, "db": db_status}


@router.get("/exercises")
async def exercises() -> list[dict]:
    return [ex.public_dict() for ex in load_exercises().values()]


@router.post("/peaks/parse")
async def parse_peaks(body: ParsePeaksIn) -> ParsePeaksOut:
    result = parse_peak_text(body.text)
    return ParsePeaksOut(
        peaks=result.peaks, errors=[ParseErrorOut(line=e.line, message=e.message) for e in result.errors]
    )
```

`backend/app/api/routes_sessions.py`:
```python
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Identity, get_db, get_identity, load_session
from app.api.schemas import (
    CreateSessionIn,
    SessionOut,
    SessionSummary,
    SpectrumOut,
    StructureCheckIn,
    UpdateSessionIn,
    session_out,
)
from app.chem.compare import compare_structure_with_data, same_structure
from app.chem.rdkit_tools import SmilesError
from app.config import get_settings
from app.errors import ApiError
from app.exercises.catalog import exercise_image_path, get_exercise
from app.nmr_engine.models import Peak, PeakList, renumber
from app.nmr_engine.simulate import simulate_spectrum
from app.nmr_tools.state_ops import ChemState, ProposedStructure
from app.store import repo
from app.store.blob import get_blob_store
from app.store.images import ImageError, normalize_image
from app.store.models import SessionRow
from app.store.repo import as_aware

router = APIRouter()


def _peaks_json(peaks: list[Peak]) -> list[dict]:
    return [p.model_dump(mode="json") for p in peaks]


@router.post("/sessions", status_code=201)
async def create_session(
    body: CreateSessionIn,
    identity: Identity = Depends(get_identity),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if body.exercise_id:
        exercise = get_exercise(body.exercise_id)
        if exercise is None:
            raise ApiError(404, "exercise_not_found", "Exercício não encontrado.")
        peaks = _peaks_json(exercise.peaks)
        metadata = dict(exercise.metadata)
        title = body.title or exercise.title
    else:
        PeakList(peaks=body.peaks)
        peaks = _peaks_json(renumber(body.peaks))
        metadata = body.metadata.model_dump(exclude_none=True)
        title = body.title or "Espectro de ¹H"
    row = await repo.create_session(
        db,
        owner_uid=identity.uid,
        title=title,
        experiment=body.experiment,
        metadata=metadata,
        peaks=peaks,
        exercise_id=body.exercise_id,
        chem_state=ChemState().model_dump(),
    )
    return {"id": str(row.id)}


@router.get("/sessions")
async def list_sessions(
    identity: Identity = Depends(get_identity), db: AsyncSession = Depends(get_db)
) -> list[SessionSummary]:
    rows = await repo.list_sessions(db, identity.uid)
    return [
        SessionSummary(id=r.id, title=r.title, exercise_id=r.exercise_id, updated_at=as_aware(r.updated_at))
        for r in rows
    ]


@router.get("/sessions/{session_id}")
async def get_session(row: SessionRow = Depends(load_session), db: AsyncSession = Depends(get_db)) -> SessionOut:
    return session_out(row, await repo.list_messages(db, row.id))


@router.patch("/sessions/{session_id}")
async def update_session(
    body: UpdateSessionIn, row: SessionRow = Depends(load_session), db: AsyncSession = Depends(get_db)
) -> SessionOut:
    if row.exercise_id and (body.peaks is not None or body.metadata is not None):
        raise ApiError(409, "exercise_read_only", "Picos e metadados de exercícios não podem ser alterados.")
    if body.peaks is not None:
        PeakList(peaks=body.peaks)
        row.peaks = _peaks_json(renumber(body.peaks))
    if body.metadata is not None:
        row.meta = body.metadata.model_dump(exclude_none=True)
    if body.assist_mode is not None:
        row.assist_mode = body.assist_mode
    if body.title is not None:
        row.title = body.title
    row = await repo.save(db, row)
    return session_out(row, await repo.list_messages(db, row.id))


@router.post("/sessions/{session_id}/image")
async def upload_image(
    file: UploadFile = File(...), row: SessionRow = Depends(load_session), db: AsyncSession = Depends(get_db)
) -> dict:
    if row.exercise_id:
        raise ApiError(409, "exercise_read_only", "Sessões de exercício já têm imagem.")
    settings = get_settings()
    data = await file.read(settings.max_upload_bytes + 1)
    try:
        normalized, media_type = normalize_image(data, settings.max_upload_bytes)
    except ImageError as exc:
        raise ApiError(422, "invalid_image", str(exc)) from exc
    store = get_blob_store()
    if row.image_blob:
        try:
            await store.delete(row.image_blob)
        except Exception:
            pass
    ext = "jpg" if media_type == "image/jpeg" else "png"
    row.image_blob = await store.put(f"sessions/{row.id}/spectrum.{ext}", normalized, media_type)
    row.image_media_type = media_type
    await repo.save(db, row)
    return {"ok": True, "media_type": media_type}


@router.get("/sessions/{session_id}/image")
async def get_image(row: SessionRow = Depends(load_session)):
    if row.exercise_id:
        return FileResponse(exercise_image_path(row.exercise_id), media_type="image/png")
    if not row.image_blob:
        raise ApiError(404, "image_not_found", "Esta sessão não tem imagem.")
    data = await get_blob_store().get(row.image_blob)
    return Response(
        content=data,
        media_type=row.image_media_type or "image/png",
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.get("/sessions/{session_id}/spectrum")
async def get_spectrum(row: SessionRow = Depends(load_session)) -> SpectrumOut:
    peaks = [Peak.model_validate(p) for p in row.peaks or []]
    sim = simulate_spectrum(peaks, (row.meta or {}).get("frequency_mhz"))
    return SpectrumOut(x=sim.x, y=sim.y, warnings=sim.warnings)


@router.post("/sessions/{session_id}/structure-check")
async def structure_check(
    body: StructureCheckIn, row: SessionRow = Depends(load_session), db: AsyncSession = Depends(get_db)
) -> dict:
    peaks = [Peak.model_validate(p) for p in row.peaks or []]
    try:
        result = compare_structure_with_data(body.smiles, peaks, (row.meta or {}).get("molecular_formula"))
    except SmilesError as exc:
        raise ApiError(422, "invalid_smiles", str(exc)) from exc
    exercise = get_exercise(row.exercise_id) if row.exercise_id else None
    if exercise and row.assist_mode in ("verify", "solution"):
        result["matches_answer"] = same_structure(body.smiles, exercise.answer_smiles)
    check = await repo.add_structure_check(db, row.id, body.smiles, result, commit=False)
    state = ChemState.model_validate(row.chem_state or {})
    state.proposed_structures.append(ProposedStructure(smiles=body.smiles, check_id=str(check.id)))
    row.chem_state = state.model_dump()
    await repo.save(db, row)
    return {**result, "check_id": str(check.id)}
```

`backend/app/main.py` (replace whole file):
```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes_misc import router as misc_router
from app.api.routes_sessions import router as sessions_router
from app.config import get_settings
from app.errors import install_error_handlers
from app.logging import RequestContextMiddleware, configure_logging
from app.store.db import create_all


@asynccontextmanager
async def lifespan(_: FastAPI):
    if get_settings().database_url.startswith("sqlite"):
        await create_all()  # local dev / e2e convenience; Postgres uses Alembic
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    app = FastAPI(
        title="RMN Tutor API",
        version=settings.app_version,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(RequestContextMiddleware)
    install_error_handlers(app)
    app.include_router(misc_router, prefix="/api")
    app.include_router(sessions_router, prefix="/api")
    return app


app = create_app()
```

- [ ] **Step 5: Run the whole backend suite**

Run: `python -m pytest -v`
Expected: all pass (the spike test file is gone; `test_foundation.py::test_request_id_header` still passes because `/api/health` only runs `SELECT 1`).

- [ ] **Step 6: Commit**

```bash
git add -A backend
git commit -m "feat(api): sessions, exercises, peak parsing, spectrum, image upload and structure checks

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: `tutor` — prompts, context builder, LLM clients, turn loop

The turn loop is append-only (see Global Constraints): the user message is persisted when it arrives; the turn's system-context message and all assistant/tool_result messages are persisted together only when the turn finishes successfully. Before starting, verify the SDK surface (the API changed in 2025–2026):

```bash
python -c "import inspect, anthropic; s=inspect.signature(anthropic.AsyncAnthropic(api_key='x').beta.messages.stream); print(all(k in s.parameters for k in ['fallbacks','cache_control','context_management','output_config','betas']))"
```
Expected: `True`. If `False`, read the `claude-api` skill (`python/claude-api/README.md`, `streaming.md`) and adapt `AnthropicLLM.stream` only.

**Files:**
- Create: `backend/app/tutor/__init__.py`, `backend/app/tutor/prompts.py`, `backend/app/tutor/context.py`, `backend/app/tutor/llm.py`, `backend/app/tutor/turn.py`
- Test: `backend/tests/test_tutor_context.py`, `backend/tests/test_tutor_turn.py`

**Interfaces:**
- Consumes: `Peak`, `ChemState`, `ToolContext`, `execute_tool`, `tool_definitions`, `repo`, `get_exercise`, `exercise_image_path`, `BlobStore`, `Settings`, `degrees_of_unsaturation`.
- Produces:
  - `prompts.SYSTEM_PROMPT: str`; `prompts.MODE_INSTRUCTIONS: dict[str, str]` (keys `tutor, hint, verify, solution`); `prompts.MODE_LABELS: dict[str, str]`; `prompts.build_turn_context(*, metadata: dict, peaks: list[Peak], chem_state: ChemState, mode: str, has_image: bool, is_exercise: bool) -> str`.
  - `context.IMAGE_MARKER = {"type": "rmn_image_ref"}`; `context.has_image_marker(content) -> bool`; `context.build_api_messages(rows: list[MessageRow], image: tuple[bytes, str] | None) -> list[dict]` (replaces the marker block with a base64 image block; rows with `role="system"` become `{"role":"system","content": <str>}`).
  - `llm.LLMEvent(type: Literal["text_delta","final"], text: str | None = None, message: dict | None = None)`; `llm.LLMError(Exception)`; `llm.LLMClient` (Protocol with `stream(*, system, tools, messages) -> AsyncIterator[LLMEvent]`); `llm.AnthropicLLM(settings)`; `llm.FakeLLM(script: list[dict] | None = None)` with attribute `calls: list[list[dict]]` (messages it received); `llm.get_llm(settings) -> LLMClient` (FakeLLM when `fake_llm` or no API key).
  - `turn.TurnEvent(event: str, data: dict)`; `turn.run_turn(*, session_id: uuid.UUID, user_text: str, mode: str | None, llm: LLMClient, blob: BlobStore, settings: Settings, sessionmaker) -> AsyncIterator[TurnEvent]`. Events: `text_delta {text}`, `tool_call {name, input}`, `tool_result {name, ok}`, `state_updated {chem_state}`, `done {text, chem_state, assist_mode}`, `error {code, message}`.
  - Final message dict shape (both clients): `{"content": list[dict], "stop_reason": str, "usage": dict}`.

- [ ] **Step 1: Write the failing context/prompt tests**

`backend/tests/test_tutor_context.py`:
```python
from types import SimpleNamespace

from app.nmr_engine.models import Peak
from app.nmr_tools.state_ops import ChemState
from app.tutor.context import IMAGE_MARKER, build_api_messages, has_image_marker
from app.tutor.prompts import MODE_INSTRUCTIONS, SYSTEM_PROMPT, build_turn_context

PEAKS = [Peak(id="P1", ppm=4.12, integral=2, multiplicity="q", j_hz=[7.1]), Peak(id="P2", ppm=2.05, integral=3, multiplicity="s")]


def test_system_prompt_is_stable_and_has_rules():
    assert "P1" in SYSTEM_PROMPT or "ID" in SYSTEM_PROMPT
    for phrase in ["não invente", "hipótese", "tabela"]:
        assert phrase in SYSTEM_PROMPT.lower()
    assert set(MODE_INSTRUCTIONS) == {"tutor", "hint", "verify", "solution"}


def test_turn_context_with_table():
    text = build_turn_context(
        metadata={"frequency_mhz": 400, "solvent": "CDCl3", "molecular_formula": "C4H8O2"},
        peaks=PEAKS,
        chem_state=ChemState(),
        mode="hint",
        has_image=True,
        is_exercise=True,
    )
    assert "| P1 | 4.12 | 2 | q | 7.1 |" in text
    assert "IDH = 1" in text
    assert MODE_INSTRUCTIONS["hint"] in text
    assert '"stage": "observe"' in text


def test_turn_context_without_peaks_says_so():
    text = build_turn_context(metadata={}, peaks=[], chem_state=ChemState(), mode="tutor", has_image=True, is_exercise=False)
    assert "Nenhuma lista de picos" in text
    assert "não informada" in text


def _row(role, content):
    return SimpleNamespace(role=role, content=content)


def test_build_api_messages_injects_image_once():
    rows = [
        _row("user", [IMAGE_MARKER, {"type": "text", "text": "oi"}]),
        _row("system", "ctx"),
        _row("assistant", [{"type": "text", "text": "olá"}]),
    ]
    msgs = build_api_messages(rows, (b"\x89PNGdata", "image/png"))
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"][0]["type"] == "image"
    assert msgs[0]["content"][0]["source"]["media_type"] == "image/png"
    assert msgs[1] == {"role": "system", "content": "ctx"}
    assert msgs[2]["content"] == [{"type": "text", "text": "olá"}]
    assert has_image_marker(rows[0].content) and not has_image_marker(rows[2].content)


def test_build_api_messages_drops_marker_without_image():
    msgs = build_api_messages([_row("user", [IMAGE_MARKER, {"type": "text", "text": "oi"}])], None)
    assert msgs[0]["content"] == [{"type": "text", "text": "oi"}]
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_tutor_context.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement prompts and context**

`backend/app/tutor/__init__.py`: empty.

`backend/app/tutor/prompts.py`:
```python
import json

from app.chem.formula import degrees_of_unsaturation
from app.nmr_engine.models import Peak
from app.nmr_tools.state_ops import ChemState

SYSTEM_PROMPT = """Você é o RMN Tutor, um professor particular de espectroscopia de RMN para estudantes de graduação em Química. Seu objetivo é ensinar o processo de elucidação estrutural, não entregar a estrutura.

Fluxo pedagógico (avance conforme o aluno avança):
A. Observação — pergunte o que o aluno observa no espectro.
B. Evidências — deslocamento químico, integração, multiplicidade, número de sinais, IDH.
C. Hipótese — peça que o aluno proponha grupo funcional, fragmento ou ambiente químico.
D. Confronto — verifique a hipótese contra os outros sinais e dados.
E. Montagem — monte os fragmentos progressivamente.
F. Checagem — verifique se a estrutura explica todos os dados (fórmula, número de sinais, integrais, multiplicidades, J, deslocamentos, simetria).

Escada de pistas (use o degrau mais baixo que funcione): 1) pergunta aberta; 2) pergunta direcionada; 3) pista conceitual; 4) pista sobre uma região do espectro; 5) hipótese parcial; 6) solução completa só quando o aluno pedir explicitamente (modo Solução) ou quando for pedagogicamente necessário.

Quando o aluno errar: indique qual observação não é compatível, evite dizer apenas "está errado", peça que ele revise o dado relevante e só explique depois que ele tiver uma oportunidade real de revisar.

Regras de dados (obrigatórias):
- A tabela de picos é a fonte oficial dos valores numéricos. Cite sinais pelo ID e deslocamento, por exemplo "P2 (2,05 ppm)".
- Use somente valores da tabela ou das ferramentas. Não invente picos, integrais, multiplicidades, constantes J ou fórmulas.
- Se um dado não existir, diga que ele não está disponível. Não trate uma imagem como medição precisa; se a imagem parecer divergir da tabela, avise o aluno e priorize a tabela.
- Toda hipótese é hipótese até ser confrontada com os dados. Use linguagem de incerteza: "uma possibilidade é...", "esse dado é compatível com...", "ainda não temos evidência suficiente para concluir...".
- Use as ferramentas para consultar dados e para checar estruturas propostas (compare_structure_with_data). As checagens são heurísticas e não são veredito.
- Registre o raciocínio com update_session_state: etapa atual, interpretação de sinais, hipóteses do aluno (by='student') ou suas (by='tutor'), hipóteses apoiadas/rejeitadas e pendências.
- Nunca use bancos de dados externos para descobrir a resposta. Em exercícios, você não conhece a resposta; check_against_answer só funciona nos modos Verificação e Solução e apenas diz se é a mesma estrutura.

Estilo: português do Brasil, frases curtas, no máximo uma ou duas perguntas por mensagem, tom encorajador e preciso. Use Markdown simples e notação como "CH₃", "¹H", "δ 4,12 ppm". Termine normalmente com uma pergunta que faça o aluno pensar.

A cada turno você recebe uma mensagem de sistema com o CONTEXTO DA SESSÃO (modo de assistência, metadados, tabela de picos e estado químico). Ela não é escrita pelo aluno e prevalece sobre contextos anteriores."""

MODE_LABELS = {"tutor": "Tutor", "hint": "Dica", "verify": "Verificação", "solution": "Solução completa"}

MODE_INSTRUCTIONS = {
    "tutor": "Conduza de forma socrática, passo a passo, seguindo a escada de pistas.",
    "hint": "O aluno pediu uma dica: dê UMA pista curta e localizada (uma região, um sinal ou um conceito) e devolva a pergunta. Não revele a estrutura.",
    "verify": "O aluno quer verificar uma hipótese ou estrutura. Se houver SMILES, rode compare_structure_with_data e confronte cada checagem com os dados; em exercícios você pode usar check_against_answer. Aponte o que é compatível e o que não é, sem dar a estrutura correta se ela estiver errada.",
    "solution": "O aluno pediu a solução completa: explique a elucidação inteira, sinal por sinal, justificando com os dados, e mostre a checagem final contra fórmula, integrais, multiplicidades e deslocamentos.",
}


def _fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def build_turn_context(
    *, metadata: dict, peaks: list[Peak], chem_state: ChemState, mode: str, has_image: bool, is_exercise: bool
) -> str:
    m = metadata or {}
    formula = m.get("molecular_formula")
    try:
        dbe = f" (IDH = {degrees_of_unsaturation(formula):g})" if formula else ""
    except ValueError:
        dbe = ""
    lines = [
        "[CONTEXTO DA SESSÃO — atualizado neste turno; não é mensagem do aluno]",
        f"Modo de assistência: {MODE_LABELS.get(mode, mode)} — {MODE_INSTRUCTIONS.get(mode, '')}",
        "Experimento: RMN de ¹H"
        f" | Frequência: {_fmt(m.get('frequency_mhz')) + ' MHz' if m.get('frequency_mhz') else 'não informada'}"
        f" | Solvente: {m.get('solvent') or 'não informado'}"
        f" | Fórmula molecular: {(formula + dbe) if formula else 'não informada'}",
        f"Tipo de sessão: {'exercício do catálogo (dados didáticos simulados)' if is_exercise else 'espectro enviado pelo aluno'}",
        f"Imagem do espectro: {'disponível (enviada no início da conversa)' if has_image else 'não disponível'}",
    ]
    if peaks:
        lines += [
            "Tabela de picos (dados oficiais):",
            "| ID | δ (ppm) | Integral | Mult. | J (Hz) |",
            "|---|---|---|---|---|",
        ]
        for p in peaks:
            j = ", ".join(f"{v:g}" for v in p.j_hz) if p.j_hz else "—"
            lines.append(f"| {p.id} | {p.ppm:g} | {_fmt(p.integral)} | {p.multiplicity or '—'} | {j} |")
    else:
        lines.append(
            "Nenhuma lista de picos foi fornecida. Não estime valores numéricos a partir da imagem; "
            "sugira ao aluno digitar a lista de picos na página da sessão."
        )
    lines.append("Estado químico atual (JSON): " + json.dumps(chem_state.model_dump(), ensure_ascii=False, sort_keys=True))
    return "\n".join(lines)
```

`backend/app/tutor/context.py`:
```python
import base64

IMAGE_MARKER = {"type": "rmn_image_ref"}


def has_image_marker(content) -> bool:
    return isinstance(content, list) and any(isinstance(b, dict) and b.get("type") == "rmn_image_ref" for b in content)


def build_api_messages(rows, image: tuple[bytes, str] | None) -> list[dict]:
    messages: list[dict] = []
    for row in rows:
        if row.role == "system":
            messages.append({"role": "system", "content": row.content})
            continue
        content = row.content
        if isinstance(content, list) and has_image_marker(content):
            blocks = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "rmn_image_ref":
                    if image is not None:
                        data, media_type = image
                        blocks.append(
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": base64.standard_b64encode(data).decode("ascii"),
                                },
                            }
                        )
                else:
                    blocks.append(block)
            content = blocks
        messages.append({"role": row.role, "content": content})
    return messages
```

- [ ] **Step 4: Run context tests**

Run: `python -m pytest tests/test_tutor_context.py -v`
Expected: all pass.

- [ ] **Step 5: Write the failing turn tests**

`backend/tests/test_tutor_turn.py`:
```python
import io

import pytest
from PIL import Image

from app.config import get_settings
from app.nmr_tools.state_ops import ChemState
from app.store import repo
from app.store.blob import MemoryBlobStore
from app.store.db import create_all, get_sessionmaker
from app.tutor.context import has_image_marker
from app.tutor.llm import FakeLLM, LLMError
from app.tutor.turn import run_turn


@pytest.fixture
async def sm():
    await create_all()
    return get_sessionmaker()


async def _session(sm, exercise_id="ex02", peaks=None):
    async with sm() as db:
        if exercise_id:
            from app.exercises.catalog import get_exercise

            ex = get_exercise(exercise_id)
            peaks = [p.model_dump(mode="json") for p in ex.peaks]
            meta = ex.metadata
        else:
            meta = {}
        row = await repo.create_session(
            db, owner_uid="u", title="t", experiment="1H", metadata=meta, peaks=peaks or [],
            exercise_id=exercise_id, chem_state=ChemState().model_dump(),
        )
        return row.id


async def _run(sm, sid, text, llm, mode=None, blob=None):
    events = []
    async for ev in run_turn(
        session_id=sid, user_text=text, mode=mode, llm=llm, blob=blob or MemoryBlobStore(),
        settings=get_settings(), sessionmaker=sm,
    ):
        events.append(ev)
    return events


async def _rows(sm, sid):
    async with sm() as db:
        return await repo.list_messages(db, sid)


async def test_default_fake_turn_uses_tool_and_persists_append_only(sm):
    sid = await _session(sm)
    llm = FakeLLM()
    events = await _run(sm, sid, "Vejo três sinais.", llm)
    kinds = [e.event for e in events]
    assert kinds[0] == "text_delta" and "tool_call" in kinds and kinds[-1] == "done"
    done = events[-1].data
    assert "P1" in done["text"]
    rows = await _rows(sm, sid)
    assert [r.role for r in rows] == ["user", "system", "assistant", "user", "assistant"]
    assert rows[0].content[0] == {"type": "rmn_image_ref"}  # exercise has an image
    assert rows[0].display_text == "Vejo três sinais."
    assert rows[-1].display_text == done["text"]
    first_call = llm.calls[0]
    assert first_call[0]["content"][0]["type"] == "image"
    assert first_call[-1]["role"] == "system" and "Tabela de picos" in first_call[-1]["content"]


async def test_second_turn_resends_identical_history(sm):
    sid = await _session(sm)
    llm = FakeLLM()
    await _run(sm, sid, "Primeira.", llm)
    await _run(sm, sid, "Segunda.", llm)
    first_turn_final = llm.calls[1]  # request after tool_result in turn 1
    second_turn = llm.calls[2]
    assert second_turn[: len(first_turn_final)] == first_turn_final
    rows = await _rows(sm, sid)
    assert sum(1 for r in rows if has_image_marker(r.content)) == 1


async def test_hint_mode_increments_counter_and_sets_mode(sm):
    sid = await _session(sm)
    await _run(sm, sid, "Me dá uma dica", FakeLLM(), mode="hint")
    async with sm() as db:
        row = await repo.get_session(db, sid)
    assert row.assist_mode == "hint" and row.chem_state["hints_given"] == 1


async def test_state_tool_updates_chem_state(sm):
    sid = await _session(sm)
    script = [
        {
            "content": [
                {"type": "tool_use", "id": "toolu_1", "name": "update_session_state",
                 "input": {"ops": [{"op": "add_hypothesis", "text": "etila", "by": "student", "evidence": ["P1"]}]}}
            ],
            "stop_reason": "tool_use",
            "usage": {"input_tokens": 10, "output_tokens": 5},
        },
        {"content": [{"type": "text", "text": "Anotei sua hipótese."}], "stop_reason": "end_turn", "usage": {"input_tokens": 12, "output_tokens": 4}},
    ]
    events = await _run(sm, sid, "Acho que é uma etila.", FakeLLM(script))
    assert any(e.event == "state_updated" for e in events)
    async with sm() as db:
        row = await repo.get_session(db, sid)
    assert row.chem_state["hypotheses"][0]["text"] == "etila"


async def test_structure_check_from_tool_is_persisted(sm):
    sid = await _session(sm)
    script = [
        {"content": [{"type": "tool_use", "id": "toolu_1", "name": "compare_structure_with_data", "input": {"smiles": "CCOC(C)=O"}}],
         "stop_reason": "tool_use", "usage": {}},
        {"content": [{"type": "text", "text": "Vamos analisar as checagens."}], "stop_reason": "end_turn", "usage": {}},
    ]
    await _run(sm, sid, "É acetato de etila?", FakeLLM(script), mode="verify")
    async with sm() as db:
        row = await repo.get_session(db, sid)
    assert row.chem_state["proposed_structures"][0]["smiles"] == "CCOC(C)=O"


async def test_llm_failure_persists_only_user_message(sm):
    sid = await _session(sm)

    class Boom(FakeLLM):
        async def stream(self, *, system, tools, messages):
            raise LLMError("indisponível")
            yield  # pragma: no cover

    events = await _run(sm, sid, "Olá", Boom())
    assert events[-1].event == "error" and events[-1].data["code"] == "llm_unavailable"
    rows = await _rows(sm, sid)
    assert [r.role for r in rows] == ["user"]
    # next turn still produces a valid sequence (consecutive user messages are allowed)
    llm = FakeLLM()
    await _run(sm, sid, "Tentando de novo", llm)
    roles = [m["role"] for m in llm.calls[0]]
    assert roles == ["user", "user", "system"]


async def test_failure_mid_tool_loop_discards_partial_turn(sm):
    sid = await _session(sm)

    class HalfBoom(FakeLLM):
        async def stream(self, *, system, tools, messages):
            if any(isinstance(m["content"], list) and any(b.get("type") == "tool_result" for b in m["content"] if isinstance(b, dict)) for m in messages):
                raise LLMError("caiu no meio")
            async for ev in super().stream(system=system, tools=tools, messages=messages):
                yield ev

    events = await _run(sm, sid, "Olá", HalfBoom())
    assert events[-1].event == "error"
    assert [r.role for r in await _rows(sm, sid)] == ["user"]


async def test_image_uploaded_later_goes_to_next_user_message(sm):
    sid = await _session(sm, exercise_id=None, peaks=[{"id": "P1", "ppm": 1.0}])
    await _run(sm, sid, "Sem imagem ainda", FakeLLM())
    blob = MemoryBlobStore()
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, "PNG")
    path = await blob.put("sessions/x/spectrum.png", buf.getvalue(), "image/png")
    async with sm() as db:
        row = await repo.get_session(db, sid)
        row.image_blob, row.image_media_type = path, "image/png"
        await repo.save(db, row)
    before = await _rows(sm, sid)
    llm = FakeLLM()
    await _run(sm, sid, "Agora com imagem", llm, blob=blob)
    after = await _rows(sm, sid)
    assert [r.content for r in after[: len(before)]] == [r.content for r in before]  # history untouched
    new_user = after[len(before)]
    assert new_user.role == "user" and new_user.content[0] == {"type": "rmn_image_ref"}
    image_blocks = [b for m in llm.calls[0] if isinstance(m["content"], list) for b in m["content"] if b.get("type") == "image"]
    assert len(image_blocks) == 1


async def test_image_only_session_context_says_no_table(sm):
    sid = await _session(sm, exercise_id=None, peaks=[])
    llm = FakeLLM()
    await _run(sm, sid, "Oi", llm)
    assert "Nenhuma lista de picos" in llm.calls[0][-1]["content"]


async def test_answer_never_in_context(sm):
    sid = await _session(sm, "ex02")
    llm = FakeLLM()
    await _run(sm, sid, "Oi", llm, mode="solution")
    blob = str(llm.calls)
    assert "CCOC(C)=O" not in blob and "acetato de etila" not in blob


async def test_tool_iteration_limit(sm, monkeypatch):
    monkeypatch.setenv("TUTOR_MAX_TOOL_ITERATIONS", "2")
    get_settings.cache_clear()
    sid = await _session(sm)
    loop_msg = {"content": [{"type": "tool_use", "id": "toolu_x", "name": "get_peak_list", "input": {}}], "stop_reason": "tool_use", "usage": {}}
    events = await _run(sm, sid, "Oi", FakeLLM([dict(loop_msg), dict(loop_msg), dict(loop_msg)]))
    assert events[-1].event == "done"
    assert "limite" in events[-1].data["text"].lower()
```

- [ ] **Step 6: Run to verify failure**

Run: `python -m pytest tests/test_tutor_turn.py -v`
Expected: FAIL (module not found).

- [ ] **Step 7: Implement the LLM clients**

`backend/app/tutor/llm.py`:
```python
import copy
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, Protocol

import anthropic

from app.config import Settings

BETAS = ["compact-2026-01-12", "server-side-fallback-2026-07-01"]


@dataclass
class LLMEvent:
    type: Literal["text_delta", "final"]
    text: str | None = None
    message: dict | None = None


class LLMError(Exception):
    pass


class LLMClient(Protocol):
    def stream(self, *, system: list[dict], tools: list[dict], messages: list[dict]) -> AsyncIterator[LLMEvent]: ...


class AnthropicLLM:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key, max_retries=1, timeout=120.0)

    async def stream(self, *, system: list[dict], tools: list[dict], messages: list[dict]) -> AsyncIterator[LLMEvent]:
        s = self.settings
        try:
            async with self.client.beta.messages.stream(
                model=s.tutor_model,
                max_tokens=s.tutor_max_tokens,
                system=system,
                tools=tools,
                messages=messages,
                output_config={"effort": s.tutor_effort},
                cache_control={"type": "ephemeral"},
                betas=BETAS,
                context_management={"edits": [{"type": "compact_20260112"}]},
                fallbacks="default",
            ) as stream:
                async for event in stream:
                    if event.type == "text":
                        yield LLMEvent("text_delta", text=event.text)
                final = await stream.get_final_message()
        except anthropic.APIStatusError as exc:
            raise LLMError(f"API status {exc.status_code} (request_id={getattr(exc, 'request_id', None)})") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError("API connection error") from exc
        yield LLMEvent(
            "final",
            message={
                "content": [b.model_dump(mode="json", exclude_none=True) for b in final.content],
                "stop_reason": final.stop_reason,
                "usage": final.usage.model_dump(mode="json", exclude_none=True) if final.usage else {},
            },
        )


class FakeLLM:
    """Deterministic stand-in used in tests, local dev without a key, and E2E (FAKE_LLM=1).

    Default behaviour per user turn: first call asks for get_peak_list; after a tool_result it answers
    with a Socratic question mentioning P1. A script (list of final-message dicts) overrides it.
    """

    def __init__(self, script: list[dict] | None = None) -> None:
        self.script = list(script or [])
        self.calls: list[list[dict]] = []
        self._n = 0

    async def stream(self, *, system: list[dict], tools: list[dict], messages: list[dict]) -> AsyncIterator[LLMEvent]:
        self.calls.append(copy.deepcopy(messages))
        self._n += 1
        if self.script:
            message = self.script.pop(0)
        else:
            last_user = next((m for m in reversed(messages) if m["role"] == "user"), None)
            after_tool = isinstance(last_user and last_user["content"], list) and any(
                isinstance(b, dict) and b.get("type") == "tool_result" for b in last_user["content"]
            )
            if after_tool:
                message = {
                    "content": [{"type": "text", "text": "Ótimo. Olhando a tabela, o que você observa no sinal P1? Quantos vizinhos ele sugere?"}],
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 120, "output_tokens": 30},
                }
            else:
                message = {
                    "content": [
                        {"type": "text", "text": "Vou consultar a lista de picos. "},
                        {"type": "tool_use", "id": f"toolu_fake_{self._n}", "name": "get_peak_list", "input": {}},
                    ],
                    "stop_reason": "tool_use",
                    "usage": {"input_tokens": 100, "output_tokens": 20},
                }
        for block in message["content"]:
            if block.get("type") == "text":
                yield LLMEvent("text_delta", text=block["text"])
        yield LLMEvent("final", message=copy.deepcopy(message))


def get_llm(settings: Settings) -> LLMClient:
    if settings.fake_llm or not settings.anthropic_api_key:
        return FakeLLM()
    return AnthropicLLM(settings)
```

- [ ] **Step 8: Implement the turn loop**

`backend/app/tutor/turn.py`:
```python
import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

from app.config import Settings
from app.exercises.catalog import exercise_image_path, get_exercise
from app.logging import log_event
from app.nmr_engine.models import Peak
from app.nmr_tools.registry import ToolContext, execute_tool, tool_definitions
from app.nmr_tools.state_ops import ChemState, ProposedStructure
from app.store import repo
from app.store.blob import BlobStore
from app.tutor.context import IMAGE_MARKER, build_api_messages, has_image_marker
from app.tutor.llm import LLMClient, LLMError
from app.tutor.prompts import SYSTEM_PROMPT, build_turn_context

logger = logging.getLogger("rmn.tutor")
SYSTEM_BLOCKS = [{"type": "text", "text": SYSTEM_PROMPT}]
LLM_UNAVAILABLE = "O tutor está indisponível no momento. Sua mensagem foi salva; tente reenviar em instantes."


@dataclass
class TurnEvent:
    event: str
    data: dict


async def _load_image(row, exercise, blob: BlobStore) -> tuple[bytes, str] | None:
    if exercise is not None:
        return exercise_image_path(exercise.id).read_bytes(), "image/png"
    if row.image_blob:
        return await blob.get(row.image_blob), row.image_media_type or "image/png"
    return None


def _text_of(content: list[dict]) -> str:
    return "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")


async def run_turn(
    *,
    session_id: uuid.UUID,
    user_text: str,
    mode: str | None,
    llm: LLMClient,
    blob: BlobStore,
    settings: Settings,
    sessionmaker,
) -> AsyncIterator[TurnEvent]:
    started = time.perf_counter()
    async with sessionmaker() as db:
        row = await repo.get_session(db, session_id)
        if mode:
            row.assist_mode = mode
        mode = row.assist_mode
        state = ChemState.model_validate(row.chem_state or {})
        if mode == "hint":
            state.hints_given += 1
        peaks = [Peak.model_validate(p) for p in row.peaks or []]
        exercise = get_exercise(row.exercise_id) if row.exercise_id else None
        has_image = exercise is not None or bool(row.image_blob)

        history = await repo.list_messages(db, session_id)
        user_blocks: list = []
        if has_image and not any(has_image_marker(r.content) for r in history):
            user_blocks.append(dict(IMAGE_MARKER))
        user_blocks.append({"type": "text", "text": user_text})
        user_rows = await repo.add_messages(
            db, session_id, [repo.NewMessage("user", user_blocks, display_text=user_text, mode=mode)], commit=False
        )
        row.chem_state = state.model_dump()
        await repo.save(db, row)
        history = history + user_rows

        image = await _load_image(row, exercise, blob) if has_image else None
        context_text = build_turn_context(
            metadata=row.meta or {}, peaks=peaks, chem_state=state, mode=mode,
            has_image=has_image, is_exercise=exercise is not None,
        )
        api_messages = build_api_messages(history, image) + [{"role": "system", "content": context_text}]
        pending: list[repo.NewMessage] = [repo.NewMessage("system", context_text, mode=mode)]
        ctx = ToolContext(
            peaks=peaks, metadata=row.meta or {}, chem_state=state, assist_mode=mode,
            has_image=has_image, experiment=row.experiment,
            answer_smiles=exercise.answer_smiles if exercise else None,
        )
        tools = tool_definitions()
        texts: list[str] = []
        checks: list[tuple[str, dict]] = []
        tool_names: list[str] = []
        usage_total = {"input_tokens": 0, "output_tokens": 0}
        last_assistant: repo.NewMessage | None = None
        hit_limit = False

        try:
            for iteration in range(settings.tutor_max_tool_iterations):
                final = None
                async for ev in llm.stream(system=SYSTEM_BLOCKS, tools=tools, messages=api_messages):
                    if ev.type == "text_delta":
                        yield TurnEvent("text_delta", {"text": ev.text})
                    else:
                        final = ev.message
                if final is None:
                    raise LLMError("stream ended without a final message")
                content = final["content"]
                for k in usage_total:
                    usage_total[k] += int(final.get("usage", {}).get(k) or 0)
                last_assistant = repo.NewMessage("assistant", content, mode=mode, usage=final.get("usage"))
                pending.append(last_assistant)
                api_messages.append({"role": "assistant", "content": content})
                if text := _text_of(content):
                    texts.append(text)
                stop = final.get("stop_reason")
                if stop == "pause_turn":
                    continue
                tool_uses = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]
                if stop != "tool_use" or not tool_uses:
                    if stop == "refusal":
                        texts.append("Não posso continuar com esse pedido. Vamos voltar à interpretação do espectro?")
                    break
                results = []
                for tu in tool_uses:
                    tool_names.append(tu["name"])
                    yield TurnEvent("tool_call", {"name": tu["name"], "input": tu.get("input", {})})
                    outcome = execute_tool(tu["name"], tu.get("input"), ctx)
                    if outcome.new_state is not None:
                        ctx.chem_state = outcome.new_state
                        yield TurnEvent("state_updated", {"chem_state": outcome.new_state.model_dump()})
                    if outcome.structure_check is not None:
                        checks.append((str(tu.get("input", {}).get("smiles", "")), outcome.structure_check))
                    yield TurnEvent("tool_result", {"name": tu["name"], "ok": outcome.result["ok"]})
                    block = {
                        "type": "tool_result",
                        "tool_use_id": tu["id"],
                        "content": json.dumps(outcome.result, ensure_ascii=False, sort_keys=True),
                    }
                    if not outcome.result["ok"]:
                        block["is_error"] = True
                    results.append(block)
                pending.append(repo.NewMessage("user", results, mode=mode))
                api_messages.append({"role": "user", "content": results})
            else:
                hit_limit = True
        except LLMError as exc:
            log_event(logger, "turn_failed", session_id=str(session_id), error=str(exc))
            yield TurnEvent("error", {"code": "llm_unavailable", "message": LLM_UNAVAILABLE})
            return

        if hit_limit:
            texts.append("(O tutor atingiu o limite de consultas neste turno. Envie uma nova mensagem para continuar.)")
        display = "\n\n".join(t.strip() for t in texts if t.strip())
        if last_assistant is not None:
            last_assistant.display_text = display

        final_state = ctx.chem_state
        for smiles, result in checks:
            check_row = await repo.add_structure_check(db, session_id, smiles, result, commit=False)
            final_state.proposed_structures.append(ProposedStructure(smiles=smiles, check_id=str(check_row.id)))
        await repo.add_messages(db, session_id, pending, commit=False)
        row.chem_state = final_state.model_dump()
        await repo.save(db, row)
        log_event(
            logger,
            "turn_done",
            session_id=str(session_id),
            mode=mode,
            tools=tool_names,
            ms=round((time.perf_counter() - started) * 1000),
            **usage_total,
        )
        yield TurnEvent("done", {"text": display, "chem_state": final_state.model_dump(), "assist_mode": mode})
```

Note: `display_text` lives on the **last** assistant message of the turn and contains the concatenated text of all assistant messages in that turn (that is what the UI shows). If the last assistant message is followed by a tool_result (iteration limit), the UI still shows the text from that assistant row.

- [ ] **Step 9: Run tests**

Run: `python -m pytest tests/test_tutor_context.py tests/test_tutor_turn.py -v`
Expected: all pass.

- [ ] **Step 10: Commit**

```bash
git add backend/app/tutor backend/tests/test_tutor_context.py backend/tests/test_tutor_turn.py
git commit -m "feat(tutor): pt-BR tutor prompt, append-only context builder, Anthropic/Fake LLM and turn loop

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 13: API — messages SSE endpoint, rate limit, turn lock, token cap

If the Task 1 spike recorded that SSE is buffered on Vercel, implement the same endpoint but return `JSONResponse({"events": [...]})` with all events collected, and make the frontend client (Task 15) accept both. Otherwise implement SSE as below.

**Files:**
- Create: `backend/app/api/routes_messages.py`
- Modify: `backend/app/api/schemas.py` (add `PostMessageIn`), `backend/app/main.py` (include the router)
- Test: `backend/tests/test_api_messages.py`

**Interfaces:**
- Consumes: `run_turn`, `get_llm` (Task 12); `load_session`, `get_identity`, `get_db` (Task 11); `repo` (Task 8); `get_blob_store` (Task 9).
- Produces:
  - `schemas.PostMessageIn(text: str (1..20000 chars), mode: AssistMode | None = None)`.
  - `POST /api/sessions/{id}/messages` → `text/event-stream` with frames `event: <name>\ndata: <json>\n\n` (names from Task 12) or JSON errors before streaming: `empty_message` / `message_too_long` (422), `session_token_cap` / `rate_limited` (429), `turn_in_progress` (409), `session_not_found` (404).
  - `routes_messages.sse(event: str, data: dict) -> bytes`.

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_api_messages.py`:
```python
import json

from app.config import get_settings
from app.store import repo
from app.store.db import get_sessionmaker


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for frame in text.strip().split("\n\n"):
        name, data = None, None
        for line in frame.splitlines():
            if line.startswith("event: "):
                name = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
        if name:
            events.append((name, data))
    return events


async def _session(client) -> str:
    return (await client.post("/api/sessions", json={"exercise_id": "ex02"})).json()["id"]


async def test_message_streams_and_persists(client):
    sid = await _session(client)
    res = await client.post(f"/api/sessions/{sid}/messages", json={"text": "Vejo três sinais."})
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(res.text)
    names = [n for n, _ in events]
    assert "text_delta" in names and "tool_call" in names and names[-1] == "done"
    s = (await client.get(f"/api/sessions/{sid}")).json()
    assert [(m["role"], m["text"]) for m in s["messages"]][0] == ("user", "Vejo três sinais.")
    assert s["messages"][1]["role"] == "assistant" and "P1" in s["messages"][1]["text"]
    res2 = await client.post(f"/api/sessions/{sid}/messages", json={"text": "E agora?", "mode": "hint"})
    assert res2.status_code == 200
    s2 = (await client.get(f"/api/sessions/{sid}")).json()
    assert s2["assist_mode"] == "hint" and len(s2["messages"]) == 4


async def test_concurrent_turn_is_rejected(client):
    sid = await _session(client)
    import uuid

    async with get_sessionmaker()() as db:
        assert await repo.acquire_turn_lock(db, uuid.UUID(sid), 60)
    res = await client.post(f"/api/sessions/{sid}/messages", json={"text": "Oi"})
    assert res.status_code == 409 and res.json()["error"]["code"] == "turn_in_progress"
    s = (await client.get(f"/api/sessions/{sid}")).json()
    assert s["messages"] == []


async def test_rate_limit(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_HOUR", "2")
    get_settings.cache_clear()
    sid = await _session(client)
    for _ in range(2):
        assert (await client.post(f"/api/sessions/{sid}/messages", json={"text": "Oi"})).status_code == 200
    res = await client.post(f"/api/sessions/{sid}/messages", json={"text": "Oi"})
    assert res.status_code == 429 and res.json()["error"]["code"] == "rate_limited"


async def test_session_token_cap(client, monkeypatch):
    monkeypatch.setenv("SESSION_INPUT_TOKEN_CAP", "1")
    get_settings.cache_clear()
    sid = await _session(client)
    assert (await client.post(f"/api/sessions/{sid}/messages", json={"text": "Oi"})).status_code == 200
    res = await client.post(f"/api/sessions/{sid}/messages", json={"text": "Oi"})
    assert res.status_code == 429 and res.json()["error"]["code"] == "session_token_cap"


async def test_message_validation(client, monkeypatch):
    monkeypatch.setenv("MAX_MESSAGE_CHARS", "10")
    get_settings.cache_clear()
    sid = await _session(client)
    res = await client.post(f"/api/sessions/{sid}/messages", json={"text": "x" * 11})
    assert res.status_code == 422 and res.json()["error"]["code"] == "message_too_long"
    res = await client.post(f"/api/sessions/{sid}/messages", json={"text": "   "})
    assert res.status_code == 422 and res.json()["error"]["code"] == "empty_message"
    res = await client.post(f"/api/sessions/{sid}/messages", json={"text": "oi", "mode": "cheat"})
    assert res.status_code == 422
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_api_messages.py -v`
Expected: FAIL (404 — route missing).

- [ ] **Step 3: Implement**

Append to `backend/app/api/schemas.py`:
```python


class PostMessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    mode: AssistMode | None = None
```

`backend/app/api/routes_messages.py`:
```python
import asyncio
import json
import logging
from datetime import timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Identity, get_db, get_identity, load_session
from app.api.schemas import PostMessageIn
from app.config import Settings, get_settings
from app.errors import ApiError
from app.store import repo
from app.store.blob import get_blob_store
from app.store.db import get_sessionmaker
from app.store.models import SessionRow
from app.tutor.llm import get_llm
from app.tutor.turn import run_turn

router = APIRouter()
logger = logging.getLogger("rmn.messages")


def sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")


async def enforce_rate_limit(db: AsyncSession, identity: Identity, settings: Settings) -> None:
    now = repo.utcnow()
    keys = (f"uid:{identity.uid}", f"ip:{identity.ip}")
    for key in keys:
        if await repo.count_rate_events(db, key, now - timedelta(hours=1)) >= settings.rate_limit_per_hour:
            raise ApiError(429, "rate_limited", "Muitas mensagens em pouco tempo. Aguarde alguns minutos e tente de novo.")
        if await repo.count_rate_events(db, key, now - timedelta(days=1)) >= settings.rate_limit_per_day:
            raise ApiError(429, "rate_limited", "Limite diário de mensagens atingido. Tente novamente amanhã.")
    for key in keys:
        await repo.record_rate_event(db, key)


@router.post("/sessions/{session_id}/messages")
async def post_message(
    body: PostMessageIn,
    row: SessionRow = Depends(load_session),
    identity: Identity = Depends(get_identity),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    text = body.text.strip()
    if not text:
        raise ApiError(422, "empty_message", "Mensagem vazia.")
    if len(text) > settings.max_message_chars:
        raise ApiError(422, "message_too_long", f"Mensagem longa demais (máx. {settings.max_message_chars} caracteres).")
    if await repo.session_input_tokens(db, row.id) >= settings.session_input_token_cap:
        raise ApiError(429, "session_token_cap", "Esta sessão atingiu o limite de uso. Inicie uma nova sessão.")
    await enforce_rate_limit(db, identity, settings)
    if not await repo.acquire_turn_lock(db, row.id, settings.turn_lock_seconds):
        raise ApiError(409, "turn_in_progress", "O tutor ainda está respondendo à mensagem anterior.")

    session_id = row.id
    llm = get_llm(settings)
    blob = get_blob_store()
    sessionmaker = get_sessionmaker()

    async def release() -> None:
        async with sessionmaker() as lock_db:
            await repo.release_turn_lock(lock_db, session_id)

    async def gen():
        try:
            async for ev in run_turn(
                session_id=session_id, user_text=text, mode=body.mode, llm=llm,
                blob=blob, settings=settings, sessionmaker=sessionmaker,
            ):
                yield sse(ev.event, ev.data)
        except Exception:
            logger.exception("turn_crashed", extra={"fields": {"session_id": str(session_id)}})
            yield sse("error", {"code": "internal_error", "message": "Erro interno no tutor. Tente novamente."})
        finally:
            await asyncio.shield(release())

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )
```

In `backend/app/main.py` add the import next to the other routers:
```python
from app.api.routes_messages import router as messages_router
```
and, after `app.include_router(sessions_router, prefix="/api")`, add:
```python
    app.include_router(messages_router, prefix="/api")
```

- [ ] **Step 4: Run the whole backend suite**

Run: `python -m pytest -q`
Expected: all pass.

- [ ] **Step 5: Manual smoke with the dev server (FAKE_LLM)**

```bash
cp .env.example .env
python -m uvicorn main:app --port 8000 &
sleep 3
curl -s -c /tmp/c.txt -X POST localhost:8000/api/sessions -H 'content-type: application/json' -d '{"exercise_id":"ex01"}'
```
Take the returned id and run:
```bash
curl -N -b /tmp/c.txt -X POST localhost:8000/api/sessions/<id>/messages -H 'content-type: application/json' -d '{"text":"Oi"}'
```
Expected: SSE frames (`text_delta`, `tool_call`, `tool_result`, `text_delta`, `done`). Stop the server (`kill %1`).

- [ ] **Step 6: Commit**

```bash
git add backend/app/api backend/app/main.py backend/tests/test_api_messages.py
git commit -m "feat(api): streaming tutor messages with rate limit, turn lock and token cap

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 14: Admin cleanup CLI + operations doc

**Files:**
- Create: `backend/app/admin.py`, `docs/operations/limpeza-de-sessoes.md`
- Test: `backend/tests/test_admin.py`

**Interfaces:**
- Consumes: `repo` (Task 8), `get_blob_store` (Task 9), Alembic config (Task 8).
- Produces: `python -m app.admin <command>`; `app.admin.main(argv: list[str] | None = None, *, input_fn=input) -> int`; `app.admin.parse_duration(text: str) -> timedelta` (`30d`, `12h`, `45m`).
  - `migrate` — `alembic upgrade head` (sync, outside the event loop).
  - `list [--older-than 30d] [--exercise ex02] [--limit N]` — table: id, updated_at, exercise, messages, title.
  - `delete --session <uuid> [--yes]` — deletes session, messages, checks and the image blob.
  - `purge --older-than 30d [--exercise ID] [--dry-run] [--yes]` — batch delete; also purges `rate_events` older than 2 days.
  - `stats` — counts and accumulated input tokens.
  - Exit codes: 0 ok, 1 nothing done / not confirmed / not found, 2 usage error.

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_admin.py`:
```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_admin.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement**

`backend/app/admin.py`:
```python
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
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_admin.py -v`
Expected: all pass.

- [ ] **Step 5: Write the operations doc**

`docs/operations/limpeza-de-sessoes.md`:
````markdown
# Limpeza manual de sessões

As sessões ficam guardadas indefinidamente. A limpeza é manual, com o script `app.admin`.

## Preparação (uma vez por terminal)

```bash
cd backend
source .venv/Scripts/activate          # Linux/macOS: source .venv/bin/activate
vercel env pull .env.production.local --environment=production
set -a; source .env.production.local; set +a
export BLOB_BACKEND=vercel
```

> O arquivo `.env.production.local` contém segredos; ele já está no `.gitignore`. Apague-o ao terminar.

## Comandos

| Objetivo | Comando |
|---|---|
| Ver números gerais | `python -m app.admin stats` |
| Listar as sessões mais recentes | `python -m app.admin list` |
| Listar sessões paradas há mais de 30 dias | `python -m app.admin list --older-than 30d` |
| Apagar uma sessão | `python -m app.admin delete --session <id>` |
| Simular limpeza em lote | `python -m app.admin purge --older-than 30d --dry-run` |
| Apagar em lote | `python -m app.admin purge --older-than 30d` |
| Só sessões de um exercício | acrescente `--exercise ex02` |

- O ID da sessão é o UUID que aparece na URL `/sessoes/<id>`.
- Sempre há uma pergunta de confirmação; use `--yes` só em scripts.
- Apagar remove mensagens, checagens de estrutura e a imagem enviada (Vercel Blob).
- `purge` também remove registros de rate limit com mais de 2 dias.
- Durações aceitas: `30d` (dias), `12h` (horas), `45m` (minutos).
````

- [ ] **Step 6: Commit**

```bash
git add backend/app/admin.py backend/tests/test_admin.py docs/operations/limpeza-de-sessoes.md
git commit -m "feat(admin): manual session cleanup CLI and operations guide

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 15: Frontend foundation — API client, SSE parser, layout, home

Before writing UI, read `frontend/AGENTS.md` (it points to the version-matched Next.js docs in `node_modules/next/dist/docs/`; consult them for App Router, `next.config.ts` and `next/font`), then load the `frontend-design:frontend-design` skill and keep its guidance in mind; the visual direction for this project is a calm "lab notebook": warm paper background, ink text, one teal accent, monospace for numbers (δ, J, integrals), generous whitespace, no gradients. The code below is the functional baseline; styling may be refined within that direction, but keep the same components, props, `data-testid`s and texts used by tests.

**Files:**
- Create: `frontend/src/lib/types.ts`, `frontend/src/lib/sse.ts`, `frontend/src/lib/api.ts`, `frontend/src/components/UnreviewedBadge.tsx`, `frontend/src/components/PrivacyNotice.tsx`, `frontend/vitest.config.ts`, `frontend/src/test/setup.ts`
- Modify (replace whole files): `frontend/next.config.ts`, `frontend/src/app/layout.tsx`, `frontend/src/app/globals.css`, `frontend/src/app/page.tsx`, `frontend/package.json` (scripts only)
- Test: `frontend/src/lib/sse.test.ts`, `frontend/src/lib/api.test.ts`

**Interfaces:**
- Consumes: backend HTTP API (Tasks 11, 13).
- Produces:
  - `types.ts`: `Multiplicity`, `AssistMode`, `Peak`, `SessionMetadata`, `ExercisePublic`, `ChatMessage`, `ChemState`, `SessionData`, `SessionSummary`, `ParseResult`, `Spectrum`, `StructureCheck`, `TurnEvent`, `MULTIPLICITIES: Multiplicity[]`, `MODE_LABELS: Record<AssistMode, string>`.
  - `sse.ts`: `createSSEParser(onMessage: (m: {event: string; data: string}) => void): {push(chunk: string): void}`; `readSSE(body: ReadableStream<Uint8Array>, onMessage): Promise<void>`.
  - `api.ts`: `class ApiError extends Error {status: number; code: string}`; `api.listExercises()`, `api.listSessions()`, `api.createSession(body)`, `api.getSession(id)`, `api.updateSession(id, body)`, `api.uploadImage(id, file: Blob, filename: string)`, `api.parsePeaks(text)`, `api.getSpectrum(id)`, `api.structureCheck(id, smiles)`, `api.sendMessage(id, text, mode, onEvent: (e: TurnEvent) => void): Promise<void>`; `imageUrl(id: string): string`.

- [ ] **Step 1: Install frontend dependencies**

```bash
cd frontend
npm i plotly.js-dist-min react-markdown remark-gfm @vercel/analytics
npm i -D @types/node@^24 vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event @playwright/test
```

In `frontend/package.json` set the `scripts` block to:
```json
{
  "dev": "next dev",
  "build": "next build",
  "start": "next start",
  "lint": "eslint",
  "test": "vitest run",
  "e2e": "playwright test"
}
```

`frontend/vitest.config.ts`:
```ts
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
```

`frontend/src/test/setup.ts`:
```ts
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => cleanup());
```

- [ ] **Step 2: Write the failing tests**

`frontend/src/lib/sse.test.ts`:
```ts
import { describe, expect, it } from "vitest";
import { createSSEParser } from "./sse";

describe("createSSEParser", () => {
  it("parses frames split across chunks", () => {
    const got: { event: string; data: string }[] = [];
    const p = createSSEParser((m) => got.push(m));
    p.push("event: text_delta\nda");
    p.push('ta: {"text":"Ol');
    p.push('á"}\n\nevent: done\ndata: {}\n\n');
    expect(got).toEqual([
      { event: "text_delta", data: '{"text":"Olá"}' },
      { event: "done", data: "{}" },
    ]);
  });

  it("handles CRLF split between chunks, comments and multi-line data", () => {
    const got: { event: string; data: string }[] = [];
    const p = createSSEParser((m) => got.push(m));
    p.push(": ping\r\n\r\nevent: x\r");
    p.push("\ndata: a\r\ndata: b\r\n\r\n");
    expect(got).toEqual([{ event: "x", data: "a\nb" }]);
  });

  it("defaults event name to message", () => {
    const got: { event: string; data: string }[] = [];
    createSSEParser((m) => got.push(m)).push("data: 1\n\n");
    expect(got).toEqual([{ event: "message", data: "1" }]);
  });
});
```

`frontend/src/lib/api.test.ts`:
```ts
import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "./api";
import type { TurnEvent } from "./types";

function streamOf(text: string): ReadableStream<Uint8Array> {
  const bytes = new TextEncoder().encode(text);
  return new ReadableStream({
    start(c) {
      c.enqueue(bytes.slice(0, 10));
      c.enqueue(bytes.slice(10));
      c.close();
    },
  });
}

afterEach(() => vi.restoreAllMocks());

describe("api", () => {
  it("throws ApiError with backend code", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ error: { code: "session_not_found", message: "Sessão não encontrada." } }), {
        status: 404,
        headers: { "content-type": "application/json" },
      }),
    );
    await expect(api.getSession("x")).rejects.toMatchObject({ status: 404, code: "session_not_found" });
    await expect(api.getSession("x")).rejects.toBeInstanceOf(ApiError);
  });

  it("sendMessage dispatches SSE events in order", async () => {
    const body =
      'event: text_delta\ndata: {"text":"Oi"}\n\n' +
      'event: tool_call\ndata: {"name":"get_peak_list","input":{}}\n\n' +
      'event: done\ndata: {"text":"Oi","chem_state":{},"assist_mode":"tutor"}\n\n';
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(streamOf(body), { status: 200, headers: { "content-type": "text/event-stream" } }),
    );
    const events: TurnEvent[] = [];
    await api.sendMessage("s1", "Oi", "tutor", (e) => events.push(e));
    expect(events.map((e) => e.event)).toEqual(["text_delta", "tool_call", "done"]);
  });

  it("sendMessage surfaces JSON errors before streaming", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ error: { code: "turn_in_progress", message: "O tutor ainda está respondendo." } }), {
        status: 409,
        headers: { "content-type": "application/json" },
      }),
    );
    await expect(api.sendMessage("s1", "Oi", null, () => {})).rejects.toMatchObject({ code: "turn_in_progress" });
  });
});
```

- [ ] **Step 3: Run to verify failure**

Run: `cd frontend && npm test`
Expected: FAIL (cannot resolve `./sse`, `./api`).

- [ ] **Step 4: Implement lib**

`frontend/src/lib/types.ts`:
```ts
export type Multiplicity = "s" | "d" | "t" | "q" | "quint" | "sext" | "sept" | "m" | "dd" | "dt" | "td" | "ddd" | "br_s";
export const MULTIPLICITIES: Multiplicity[] = ["s", "d", "t", "q", "quint", "sext", "sept", "m", "dd", "dt", "td", "ddd", "br_s"];

export type AssistMode = "tutor" | "hint" | "verify" | "solution";
export const MODE_LABELS: Record<AssistMode, string> = {
  tutor: "Tutor",
  hint: "Dica",
  verify: "Verificação",
  solution: "Solução completa",
};

export interface Peak {
  id: string;
  ppm: number;
  integral: number | null;
  multiplicity: Multiplicity | null;
  j_hz: number[] | null;
  source: "user" | "exercise" | "engine";
  note: string | null;
}

export interface SessionMetadata {
  frequency_mhz?: number | null;
  solvent?: string | null;
  molecular_formula?: string | null;
  notes?: string | null;
}

export interface ExercisePublic {
  id: string;
  title: string;
  difficulty: number;
  experiment: string;
  metadata: SessionMetadata;
  reviewed: boolean;
  notes: string | null;
}

export interface ChatMessage {
  seq: number;
  role: "user" | "assistant";
  text: string;
  mode: string | null;
  created_at: string;
}

export interface ChemState {
  schema_version: 1;
  stage: string;
  signal_notes: { peak_id: string; interpretation: string; status: string }[];
  hypotheses: { id: string; text: string; by: string; status: string; evidence: string[] }[];
  unresolved: string[];
  hints_given: number;
  proposed_structures: { smiles: string; check_id: string | null }[];
}

export interface SessionData {
  id: string;
  title: string;
  experiment: string;
  metadata: SessionMetadata;
  exercise: { id: string; title: string; reviewed: boolean; notes: string | null } | null;
  has_image: boolean;
  peaks: Peak[];
  chem_state: ChemState;
  assist_mode: AssistMode;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
}

export interface SessionSummary {
  id: string;
  title: string;
  exercise_id: string | null;
  updated_at: string;
}

export interface ParseResult {
  peaks: Peak[];
  errors: { line: number; message: string }[];
}

export interface Spectrum {
  x: number[];
  y: number[];
  warnings: string[];
}

export interface StructureCheck {
  canonical_smiles: string;
  formula: string;
  total_h: number;
  h_environments: { count: number; h_class: string; label: string; expected_range_ppm: [number, number] }[];
  checks: { name: string; status: "pass" | "fail" | "inconclusive"; detail: string; heuristic: boolean }[];
  limitations: string[];
  matches_answer?: boolean;
  check_id: string;
}

export type TurnEvent =
  | { event: "text_delta"; data: { text: string } }
  | { event: "tool_call"; data: { name: string; input: unknown } }
  | { event: "tool_result"; data: { name: string; ok: boolean } }
  | { event: "state_updated"; data: { chem_state: ChemState } }
  | { event: "done"; data: { text: string; chem_state: ChemState; assist_mode: AssistMode } }
  | { event: "error"; data: { code: string; message: string } };
```

`frontend/src/lib/sse.ts`:
```ts
export interface SSEMessage {
  event: string;
  data: string;
}

export function createSSEParser(onMessage: (m: SSEMessage) => void) {
  let buffer = "";
  return {
    push(chunk: string) {
      buffer = (buffer + chunk).replace(/\r\n/g, "\n");
      let idx: number;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const raw = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        let event = "message";
        const data: string[] = [];
        for (const line of raw.split("\n")) {
          if (line.startsWith(":")) continue;
          if (line.startsWith("event:")) event = line.slice(6).trim();
          else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
        }
        if (data.length) onMessage({ event, data: data.join("\n") });
      }
    },
  };
}

export async function readSSE(body: ReadableStream<Uint8Array>, onMessage: (m: SSEMessage) => void): Promise<void> {
  const parser = createSSEParser(onMessage);
  const reader = body.getReader();
  const decoder = new TextDecoder();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    parser.push(decoder.decode(value, { stream: true }));
  }
  parser.push(decoder.decode() + "\n\n");
}
```

`frontend/src/lib/api.ts`:
```ts
import { readSSE } from "./sse";
import type {
  AssistMode,
  ExercisePublic,
  ParseResult,
  Peak,
  SessionData,
  SessionMetadata,
  SessionSummary,
  Spectrum,
  StructureCheck,
  TurnEvent,
} from "./types";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

async function toApiError(res: Response): Promise<ApiError> {
  let code = "http_error";
  let message = `Erro ${res.status}`;
  try {
    const body = await res.json();
    code = body?.error?.code ?? code;
    message = body?.error?.message ?? message;
  } catch {
    /* non-JSON error body */
  }
  return new ApiError(res.status, code, message);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (init.body && !(init.body instanceof FormData)) headers["Content-Type"] = "application/json";
  const res = await fetch(`/api${path}`, { credentials: "same-origin", ...init, headers: { ...headers, ...(init.headers as Record<string, string>) } });
  if (!res.ok) throw await toApiError(res);
  return (await res.json()) as T;
}

export function imageUrl(id: string): string {
  return `/api/sessions/${id}/image`;
}

export const api = {
  listExercises: () => request<ExercisePublic[]>("/exercises"),
  listSessions: () => request<SessionSummary[]>("/sessions"),
  createSession: (body: { exercise_id?: string; metadata?: SessionMetadata; peaks?: Peak[]; title?: string }) =>
    request<{ id: string }>("/sessions", { method: "POST", body: JSON.stringify(body) }),
  getSession: (id: string) => request<SessionData>(`/sessions/${id}`),
  updateSession: (id: string, body: { metadata?: SessionMetadata; peaks?: Peak[]; assist_mode?: AssistMode; title?: string }) =>
    request<SessionData>(`/sessions/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  uploadImage: (id: string, file: Blob, filename: string) => {
    const form = new FormData();
    form.append("file", file, filename);
    return request<{ ok: boolean; media_type: string }>(`/sessions/${id}/image`, { method: "POST", body: form });
  },
  parsePeaks: (text: string) => request<ParseResult>("/peaks/parse", { method: "POST", body: JSON.stringify({ text }) }),
  getSpectrum: (id: string) => request<Spectrum>(`/sessions/${id}/spectrum`),
  structureCheck: (id: string, smiles: string) =>
    request<StructureCheck>(`/sessions/${id}/structure-check`, { method: "POST", body: JSON.stringify({ smiles }) }),
  async sendMessage(id: string, text: string, mode: AssistMode | null, onEvent: (e: TurnEvent) => void): Promise<void> {
    const res = await fetch(`/api/sessions/${id}/messages`, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(mode ? { text, mode } : { text }),
    });
    if (!res.ok) throw await toApiError(res);
    const type = res.headers.get("content-type") ?? "";
    if (type.includes("application/json")) {
      const body = (await res.json()) as { events: TurnEvent[] };
      body.events.forEach(onEvent);
      return;
    }
    if (!res.body) throw new ApiError(500, "no_stream", "Resposta sem corpo.");
    await readSSE(res.body, (m) => onEvent({ event: m.event, data: JSON.parse(m.data) } as TurnEvent));
  },
};
```

- [ ] **Step 5: Run unit tests**

Run: `npm test`
Expected: all pass.

- [ ] **Step 6: Layout, theme, dev proxy, home page**

`frontend/next.config.ts`:
```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Next 16 blocks dev resources for other hostnames; allow 127.0.0.1 used by local tooling.
  allowedDevOrigins: ["127.0.0.1"],
  async rewrites() {
    // In production Vercel Services route /api/* to the FastAPI service; locally we proxy to uvicorn.
    if (process.env.NODE_ENV !== "development") return [];
    const backend = process.env.BACKEND_DEV_URL ?? "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
```

`frontend/src/app/globals.css`:
```css
@import "tailwindcss";

@theme {
  --color-paper: #f7f5ef;
  --color-card: #fffdf8;
  --color-ink: #1c2430;
  --color-muted: #5b6573;
  --color-line: #ddd8cc;
  --color-accent: #0f766e;
  --color-accent-soft: #d6efe9;
  --color-warn: #b45309;
  --color-warn-soft: #fdf0dc;
  --color-bad: #b42318;
  --color-bad-soft: #fde8e6;
  --font-sans: var(--font-plex-sans), ui-sans-serif, system-ui, sans-serif;
  --font-mono: var(--font-plex-mono), ui-monospace, monospace;
}

html,
body {
  background: var(--color-paper);
  color: var(--color-ink);
}

.chat-md p {
  margin: 0.35rem 0;
}
.chat-md ul,
.chat-md ol {
  margin: 0.35rem 0 0.35rem 1.2rem;
  list-style: disc;
}
.chat-md table {
  border-collapse: collapse;
  margin: 0.5rem 0;
  font-size: 0.85rem;
}
.chat-md th,
.chat-md td {
  border: 1px solid var(--color-line);
  padding: 0.15rem 0.5rem;
}
.chat-md code {
  font-family: var(--font-mono);
  font-size: 0.85em;
}
```

`frontend/src/app/layout.tsx`:
```tsx
import { Analytics } from "@vercel/analytics/next";
import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const sans = IBM_Plex_Sans({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-plex-sans" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-plex-mono" });

export const metadata: Metadata = {
  title: "RMN Tutor",
  description: "Tutor de interpretação de espectros de RMN de ¹H",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={`${sans.variable} ${mono.variable}`}>
      <body className="min-h-screen font-sans antialiased">
        <header className="border-b border-line bg-card/80">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
            <Link href="/" className="text-lg font-semibold tracking-tight">
              RMN <span className="text-accent">Tutor</span>
            </Link>
            <nav className="flex gap-4 text-sm text-muted">
              <Link href="/">Início</Link>
              <Link href="/sessoes/nova">Novo espectro</Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
        <Analytics />
      </body>
    </html>
  );
}
```

`frontend/src/components/UnreviewedBadge.tsx`:
```tsx
export function UnreviewedBadge() {
  return (
    <span
      data-testid="unreviewed-badge"
      title="Valores didáticos simulados, ainda não conferidos por um especialista."
      className="inline-flex items-center rounded-full border border-warn/40 bg-warn-soft px-2 py-0.5 text-xs font-medium text-warn"
    >
      dados não revisados
    </span>
  );
}
```

`frontend/src/components/PrivacyNotice.tsx`:
```tsx
export function PrivacyNotice() {
  return (
    <p className="text-xs text-muted">
      O espectro, os dados e as mensagens são enviados à Anthropic (Claude) para gerar as respostas. Não envie dados
      pessoais. Quem tiver o link da sessão consegue abri-la.
    </p>
  );
}
```

`frontend/src/app/page.tsx`:
```tsx
"use client";

import { UnreviewedBadge } from "@/components/UnreviewedBadge";
import { api } from "@/lib/api";
import type { ExercisePublic, SessionSummary } from "@/lib/types";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function Home() {
  const router = useRouter();
  const [exercises, setExercises] = useState<ExercisePublic[]>([]);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listExercises().then(setExercises).catch((e) => setError(e.message));
    api.listSessions().then(setSessions).catch(() => setSessions([]));
  }, []);

  async function start(exerciseId: string) {
    setBusy(exerciseId);
    try {
      const { id } = await api.createSession({ exercise_id: exerciseId });
      router.push(`/sessoes/${id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(null);
    }
  }

  return (
    <div className="space-y-10">
      <section className="max-w-3xl space-y-3">
        <h1 className="text-3xl font-semibold tracking-tight">Interprete espectros de RMN de ¹H com um tutor</h1>
        <p className="text-muted">
          Observe, levante hipóteses e confronte-as com os dados. O tutor faz perguntas, dá pistas graduais e usa
          ferramentas determinísticas para os valores numéricos — você continua no centro do raciocínio.
        </p>
        <Link
          href="/sessoes/nova"
          className="inline-block rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90"
        >
          Enviar meu espectro
        </Link>
      </section>

      {error && <p className="rounded-md bg-bad-soft p-3 text-sm text-bad">{error}</p>}

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Exercícios</h2>
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {exercises.map((ex) => (
            <li key={ex.id} data-testid={`exercise-${ex.id}`} className="flex flex-col gap-2 rounded-lg border border-line bg-card p-4">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-medium">{ex.title}</h3>
                {!ex.reviewed && <UnreviewedBadge />}
              </div>
              <p className="font-mono text-xs text-muted">
                {ex.metadata.frequency_mhz} MHz · {ex.metadata.solvent} · dificuldade {ex.difficulty}
              </p>
              <button
                onClick={() => start(ex.id)}
                disabled={busy !== null}
                className="mt-auto self-start rounded-md border border-accent px-3 py-1.5 text-sm text-accent hover:bg-accent-soft disabled:opacity-50"
              >
                {busy === ex.id ? "Abrindo…" : "Começar"}
              </button>
            </li>
          ))}
        </ul>
      </section>

      {sessions.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-xl font-semibold">Minhas sessões</h2>
          <ul className="divide-y divide-line rounded-lg border border-line bg-card">
            {sessions.map((s) => (
              <li key={s.id}>
                <Link href={`/sessoes/${s.id}`} className="flex justify-between px-4 py-2 text-sm hover:bg-paper">
                  <span>{s.title}</span>
                  <span className="font-mono text-xs text-muted">{new Date(s.updated_at).toLocaleString("pt-BR")}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
```

- [ ] **Step 7: Verify build, lint and tests**

Run: `npm run lint && npm test && npm run build`
Expected: all succeed.

- [ ] **Step 8: Run locally against the backend and look at it**

Terminal 1: `cd backend && python -m uvicorn main:app --port 8000` (with `.env` from `.env.example`). Terminal 2: `cd frontend && npm run dev`. Open http://localhost:3000 with the Playwright MCP (`browser_navigate`, `browser_take_screenshot`): the five exercise cards show "dados não revisados"; clicking "Começar" navigates to `/sessoes/<uuid>` (404 page is expected until Task 17).

- [ ] **Step 9: Commit**

```bash
git add frontend
git commit -m "feat(frontend): typed API client, SSE reader, lab-notebook layout and home page

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 16: Frontend — new-session page (metadata, peak editor, image upload)

**Files:**
- Create: `frontend/src/lib/image.ts`, `frontend/src/components/MetadataForm.tsx`, `frontend/src/components/PeakTableEditor.tsx`, `frontend/src/components/ImageDrop.tsx`, `frontend/src/app/sessoes/nova/page.tsx`
- Test: `frontend/src/components/PeakTableEditor.test.tsx`

**Interfaces:**
- Consumes: `api`, types (Task 15).
- Produces:
  - `image.ts`: `MAX_UPLOAD_BYTES = 4 * 1024 * 1024`, `MAX_DIMENSION = 2048`, `prepareImage(file: File): Promise<{blob: Blob; name: string}>`.
  - `<MetadataForm value={SessionMetadata} onChange={(m) => void} />`.
  - `<PeakTableEditor peaks={Peak[]} onChange={(p: Peak[]) => void} parse?={(text) => Promise<ParseResult>} />` — paste box (`data-testid="peak-paste"`, button "Interpretar lista"), editable table rows (`data-testid="peak-row"`), "Adicionar pico", per-row "Remover"; parse errors listed as `Linha N: mensagem`.
  - `<ImageDrop file={File | null} onChange={(f: File | null) => void} />`.
  - Page `/sessoes/nova`.

- [ ] **Step 1: Write the failing component test**

`frontend/src/components/PeakTableEditor.test.tsx`:
```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Peak } from "@/lib/types";
import { PeakTableEditor } from "./PeakTableEditor";

const P1: Peak = { id: "P1", ppm: 4.12, integral: 2, multiplicity: "q", j_hz: [7.1], source: "user", note: null };

describe("PeakTableEditor", () => {
  it("renders rows and edits values", async () => {
    const onChange = vi.fn();
    render(<PeakTableEditor peaks={[P1]} onChange={onChange} />);
    expect(screen.getAllByTestId("peak-row")).toHaveLength(1);
    const ppm = screen.getByLabelText("δ de P1");
    await userEvent.clear(ppm);
    await userEvent.type(ppm, "4.1");
    expect(onChange).toHaveBeenLastCalledWith([{ ...P1, ppm: 4.1 }]);
  });

  it("parses J list and removes rows", async () => {
    const onChange = vi.fn();
    render(<PeakTableEditor peaks={[P1]} onChange={onChange} />);
    const j = screen.getByLabelText("J de P1");
    await userEvent.clear(j);
    await userEvent.type(j, "8,0; 2,0");
    expect(onChange).toHaveBeenLastCalledWith([{ ...P1, j_hz: [8, 2] }]);
    await userEvent.click(screen.getByRole("button", { name: "Remover P1" }));
    expect(onChange).toHaveBeenLastCalledWith([]);
  });

  it("pastes a list through the parser and shows errors", async () => {
    const onChange = vi.fn();
    const parse = vi.fn().mockResolvedValue({ peaks: [P1], errors: [{ line: 2, message: "termo não reconhecido: 'x'" }] });
    render(<PeakTableEditor peaks={[]} onChange={onChange} parse={parse} />);
    await userEvent.type(screen.getByTestId("peak-paste"), "4.12 2 q 7.1");
    await userEvent.click(screen.getByRole("button", { name: "Interpretar lista" }));
    await waitFor(() => expect(onChange).toHaveBeenCalledWith([P1]));
    expect(screen.getByText("Linha 2: termo não reconhecido: 'x'")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `npm test`
Expected: FAIL (cannot resolve `./PeakTableEditor`).

- [ ] **Step 3: Implement components**

`frontend/src/lib/image.ts`:
```ts
export const MAX_UPLOAD_BYTES = 4 * 1024 * 1024;
export const MAX_DIMENSION = 2048;

function toBlob(canvas: HTMLCanvasElement, type: string, quality?: number): Promise<Blob> {
  return new Promise((resolve, reject) =>
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("Falha ao converter a imagem."))), type, quality),
  );
}

/** Downscale to ≤ 2048 px and ≤ 4 MB (Vercel Functions cap request bodies at 4.5 MB). */
export async function prepareImage(file: File): Promise<{ blob: Blob; name: string }> {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, MAX_DIMENSION / Math.max(bitmap.width, bitmap.height));
  if (scale === 1 && file.size <= MAX_UPLOAD_BYTES) {
    bitmap.close();
    return { blob: file, name: file.name };
  }
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext("2d")!.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  const base = file.name.replace(/\.\w+$/, "");
  const png = await toBlob(canvas, "image/png");
  if (png.size <= MAX_UPLOAD_BYTES) return { blob: png, name: `${base}.png` };
  const jpeg = await toBlob(canvas, "image/jpeg", 0.9);
  if (jpeg.size > MAX_UPLOAD_BYTES) throw new Error("Imagem grande demais mesmo após redução.");
  return { blob: jpeg, name: `${base}.jpg` };
}
```

`frontend/src/components/MetadataForm.tsx`:
```tsx
"use client";

import type { SessionMetadata } from "@/lib/types";

const SOLVENTS = ["CDCl3", "DMSO-d6", "D2O", "CD3OD", "C6D6", "acetona-d6"];

export function MetadataForm({ value, onChange }: { value: SessionMetadata; onChange: (m: SessionMetadata) => void }) {
  const set = (patch: Partial<SessionMetadata>) => onChange({ ...value, ...patch });
  const input = "w-full rounded-md border border-line bg-card px-3 py-2 text-sm";
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <label className="space-y-1 text-sm">
        <span className="font-medium">Frequência (MHz)</span>
        <input
          type="number"
          min={1}
          className={input}
          value={value.frequency_mhz ?? ""}
          onChange={(e) => set({ frequency_mhz: e.target.value ? Number(e.target.value) : null })}
          placeholder="400"
        />
      </label>
      <label className="space-y-1 text-sm">
        <span className="font-medium">Solvente</span>
        <input
          list="solvents"
          className={input}
          value={value.solvent ?? ""}
          onChange={(e) => set({ solvent: e.target.value || null })}
          placeholder="CDCl3"
        />
        <datalist id="solvents">
          {SOLVENTS.map((s) => (
            <option key={s} value={s} />
          ))}
        </datalist>
      </label>
      <label className="space-y-1 text-sm">
        <span className="font-medium">Fórmula molecular</span>
        <input
          className={`${input} font-mono`}
          value={value.molecular_formula ?? ""}
          onChange={(e) => set({ molecular_formula: e.target.value.replace(/\s/g, "") || null })}
          placeholder="C4H8O2"
        />
      </label>
      <label className="space-y-1 text-sm sm:col-span-3">
        <span className="font-medium">Observações (opcional)</span>
        <textarea
          className={input}
          rows={2}
          maxLength={1000}
          value={value.notes ?? ""}
          onChange={(e) => set({ notes: e.target.value || null })}
        />
      </label>
    </div>
  );
}
```

`frontend/src/components/PeakTableEditor.tsx`:
```tsx
"use client";

import { api } from "@/lib/api";
import { MULTIPLICITIES, type Multiplicity, type ParseResult, type Peak } from "@/lib/types";
import { useState } from "react";

function parseNumber(text: string): number | null {
  const t = text.trim().replace(",", ".");
  if (!t) return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
}

function parseJ(text: string): number[] | null {
  const values = text
    .split(/[;\s]+/)
    .map((v) => parseNumber(v))
    .filter((v): v is number => v !== null);
  return values.length ? values : null;
}

function formatJ(j: number[] | null): string {
  return j ? j.join("; ") : "";
}

function nextId(peaks: Peak[]): string {
  const max = peaks.reduce((m, p) => Math.max(m, Number(p.id.slice(1)) || 0), 0);
  return `P${max + 1}`;
}

export function PeakTableEditor({
  peaks,
  onChange,
  parse = api.parsePeaks,
}: {
  peaks: Peak[];
  onChange: (peaks: Peak[]) => void;
  parse?: (text: string) => Promise<ParseResult>;
}) {
  const [paste, setPaste] = useState("");
  const [errors, setErrors] = useState<ParseResult["errors"]>([]);
  const [busy, setBusy] = useState(false);
  const [jDrafts, setJDrafts] = useState<Record<string, string>>({});

  const update = (id: string, patch: Partial<Peak>) => onChange(peaks.map((p) => (p.id === id ? { ...p, ...patch } : p)));

  async function interpret() {
    setBusy(true);
    try {
      const result = await parse(paste);
      setErrors(result.errors);
      if (result.peaks.length) {
        setJDrafts({});
        onChange(result.peaks);
      }
    } catch (e) {
      setErrors([{ line: 0, message: (e as Error).message }]);
    } finally {
      setBusy(false);
    }
  }

  const cell = "w-full rounded border border-line bg-card px-2 py-1 font-mono text-sm";
  return (
    <div className="space-y-3">
      <div className="space-y-2">
        <textarea
          data-testid="peak-paste"
          className="w-full rounded-md border border-line bg-card px-3 py-2 font-mono text-sm"
          rows={4}
          value={paste}
          onChange={(e) => setPaste(e.target.value)}
          placeholder={"Cole a lista de picos. Exemplos:\n4,12 (q, J = 7,1 Hz, 2H), 2,05 (s, 3H)\n1.26;3;t;7.1"}
        />
        <button
          type="button"
          onClick={interpret}
          disabled={busy || !paste.trim()}
          className="rounded-md border border-accent px-3 py-1.5 text-sm text-accent hover:bg-accent-soft disabled:opacity-50"
        >
          Interpretar lista
        </button>
        {errors.length > 0 && (
          <ul className="space-y-0.5 text-sm text-bad">
            {errors.map((e, i) => (
              <li key={i}>{e.line > 0 ? `Linha ${e.line}: ${e.message}` : e.message}</li>
            ))}
          </ul>
        )}
      </div>

      <table className="w-full text-sm">
        <thead className="text-left text-xs text-muted">
          <tr>
            <th className="py-1">ID</th>
            <th>δ (ppm)</th>
            <th>Integral</th>
            <th>Mult.</th>
            <th>J (Hz)</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {peaks.map((p) => (
            <tr key={p.id} data-testid="peak-row">
              <td className="pr-2 font-mono text-muted">{p.id}</td>
              <td className="pr-2">
                <input
                  aria-label={`δ de ${p.id}`}
                  className={cell}
                  inputMode="decimal"
                  defaultValue={String(p.ppm)}
                  onChange={(e) => {
                    const v = parseNumber(e.target.value);
                    if (v !== null) update(p.id, { ppm: v });
                  }}
                />
              </td>
              <td className="pr-2">
                <input
                  aria-label={`Integral de ${p.id}`}
                  className={cell}
                  inputMode="decimal"
                  defaultValue={p.integral ?? ""}
                  onChange={(e) => update(p.id, { integral: parseNumber(e.target.value) })}
                />
              </td>
              <td className="pr-2">
                <select
                  aria-label={`Multiplicidade de ${p.id}`}
                  className={cell}
                  value={p.multiplicity ?? ""}
                  onChange={(e) => update(p.id, { multiplicity: (e.target.value || null) as Multiplicity | null })}
                >
                  <option value="">—</option>
                  {MULTIPLICITIES.map((m) => (
                    <option key={m} value={m}>
                      {m === "br_s" ? "br s" : m}
                    </option>
                  ))}
                </select>
              </td>
              <td className="pr-2">
                <input
                  aria-label={`J de ${p.id}`}
                  className={cell}
                  value={jDrafts[p.id] ?? formatJ(p.j_hz)}
                  onChange={(e) => {
                    setJDrafts({ ...jDrafts, [p.id]: e.target.value });
                    update(p.id, { j_hz: parseJ(e.target.value) });
                  }}
                />
              </td>
              <td>
                <button
                  type="button"
                  aria-label={`Remover ${p.id}`}
                  onClick={() => onChange(peaks.filter((x) => x.id !== p.id))}
                  className="text-muted hover:text-bad"
                >
                  ✕
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <button
        type="button"
        onClick={() =>
          onChange([...peaks, { id: nextId(peaks), ppm: 1.0, integral: null, multiplicity: null, j_hz: null, source: "user", note: null }])
        }
        className="text-sm text-accent hover:underline"
      >
        + Adicionar pico
      </button>
    </div>
  );
}
```

`frontend/src/components/ImageDrop.tsx`:
```tsx
"use client";

import { useEffect, useMemo } from "react";

export function ImageDrop({ file, onChange }: { file: File | null; onChange: (f: File | null) => void }) {
  const preview = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);

  useEffect(
    () => () => {
      if (preview) URL.revokeObjectURL(preview);
    },
    [preview],
  );

  return (
    <div className="space-y-2">
      <label className="flex cursor-pointer flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed border-line bg-card p-6 text-sm text-muted hover:border-accent">
        <span className="font-medium text-ink">Imagem do espectro (PNG, JPEG ou WebP)</span>
        <span>Clique para escolher um arquivo. Imagens grandes são reduzidas automaticamente.</span>
        <input
          type="file"
          accept="image/png,image/jpeg,image/webp"
          className="hidden"
          data-testid="image-input"
          onChange={(e) => onChange(e.target.files?.[0] ?? null)}
        />
      </label>
      {preview && (
        <div className="flex items-start gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={preview} alt="Pré-visualização do espectro" className="max-h-48 rounded border border-line" />
          <button type="button" onClick={() => onChange(null)} className="text-sm text-muted hover:text-bad">
            Remover imagem
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run tests**

Run: `npm test`
Expected: all pass.

- [ ] **Step 5: Implement the page**

`frontend/src/app/sessoes/nova/page.tsx`:
```tsx
"use client";

import { ImageDrop } from "@/components/ImageDrop";
import { MetadataForm } from "@/components/MetadataForm";
import { PeakTableEditor } from "@/components/PeakTableEditor";
import { PrivacyNotice } from "@/components/PrivacyNotice";
import { api } from "@/lib/api";
import { prepareImage } from "@/lib/image";
import type { Peak, SessionMetadata } from "@/lib/types";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function NewSessionPage() {
  const router = useRouter();
  const [metadata, setMetadata] = useState<SessionMetadata>({ frequency_mhz: 400, solvent: "CDCl3" });
  const [peaks, setPeaks] = useState<Peak[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file && peaks.length === 0) {
      setError("Envie a imagem do espectro ou informe a lista de picos (de preferência os dois).");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const { id } = await api.createSession({ metadata, peaks });
      if (file) {
        const { blob, name } = await prepareImage(file);
        await api.uploadImage(id, blob, name);
      }
      router.push(`/sessoes/${id}`);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="mx-auto max-w-4xl space-y-8">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">Novo espectro de ¹H</h1>
        <p className="text-sm text-muted">
          A imagem serve de contexto visual; os valores numéricos usados pelo tutor vêm da lista de picos.
        </p>
      </div>
      <section className="space-y-3">
        <h2 className="font-semibold">1. Metadados</h2>
        <MetadataForm value={metadata} onChange={setMetadata} />
      </section>
      <section className="space-y-3">
        <h2 className="font-semibold">2. Imagem do espectro</h2>
        <ImageDrop file={file} onChange={setFile} />
      </section>
      <section className="space-y-3">
        <h2 className="font-semibold">3. Lista de picos</h2>
        <PeakTableEditor peaks={peaks} onChange={setPeaks} />
      </section>
      {error && <p className="rounded-md bg-bad-soft p-3 text-sm text-bad">{error}</p>}
      <div className="space-y-2">
        <button
          type="submit"
          disabled={busy}
          className="rounded-md bg-accent px-5 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          {busy ? "Criando sessão…" : "Começar sessão com o tutor"}
        </button>
        <PrivacyNotice />
      </div>
    </form>
  );
}
```

- [ ] **Step 6: Verify**

Run: `npm run lint && npm test && npm run build`
Expected: all succeed. With backend + `npm run dev` running, open http://localhost:3000/sessoes/nova (Playwright MCP), paste `4,12 (q, J = 7,1 Hz, 2H), 2,05 (s, 3H), 1,26 (t, J = 7,1 Hz, 3H)`, click "Interpretar lista": three rows appear; submit creates a session and navigates.

- [ ] **Step 7: Commit**

```bash
git add frontend
git commit -m "feat(frontend): new-session page with metadata, peak editor and image upload

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 17: Frontend — session page (spectrum, chat, modes, state, SMILES check)

**Files:**
- Create: `frontend/src/types/plotly.d.ts`, `frontend/src/lib/tools.ts`, `frontend/src/components/ImageViewer.tsx`, `frontend/src/components/SpectrumPlot.tsx`, `frontend/src/components/SpectrumPanel.tsx`, `frontend/src/components/ModeSelector.tsx`, `frontend/src/components/ChatPanel.tsx`, `frontend/src/components/StatePanel.tsx`, `frontend/src/components/StructureCheckBox.tsx`, `frontend/src/app/sessoes/[id]/page.tsx`
- Test: `frontend/src/components/ModeSelector.test.tsx`, `frontend/src/components/ChatPanel.test.tsx`, `frontend/src/components/StatePanel.test.tsx`, `frontend/src/components/StructureCheckBox.test.tsx`

**Interfaces:**
- Consumes: `api`, `imageUrl`, `ApiError`, types (Task 15); `PeakTableEditor` (Task 16); `UnreviewedBadge`, `PrivacyNotice`.
- Produces:
  - `tools.ts`: `TOOL_LABELS: Record<string, string>`, `toolLabel(name: string): string`.
  - `<ModeSelector mode={AssistMode} onChange={(m) => void} disabled?={boolean} />` — "Solução completa" requires an inline confirmation ("Sim, mostrar a solução").
  - `<ChatPanel session={SessionData} onStateChange={(s: ChemState) => void} onModeChange={(m: AssistMode) => void} />` — `data-testid="chat-input"`, button "Enviar", assistant bubbles `data-testid="assistant-message"`, tool chips `data-testid="tool-chip"`.
  - `<StatePanel state={ChemState} />`, `<StructureCheckBox sessionId={string} onChecked={() => void} />` (`data-testid="smiles-input"`, button "Verificar estrutura", results `data-testid="check-<name>"`).
  - `<SpectrumPanel session={SessionData} onSessionChange={(s: SessionData) => void} />`, `<SpectrumPlot sessionId peaks refreshKey />`, `<ImageViewer src alt />`.
  - Page `/sessoes/[id]`.

- [ ] **Step 1: Write the failing component tests**

`frontend/src/components/ModeSelector.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ModeSelector } from "./ModeSelector";

describe("ModeSelector", () => {
  it("switches modes directly except solution", async () => {
    const onChange = vi.fn();
    render(<ModeSelector mode="tutor" onChange={onChange} />);
    await userEvent.click(screen.getByRole("button", { name: "Dica" }));
    expect(onChange).toHaveBeenCalledWith("hint");
    await userEvent.click(screen.getByRole("button", { name: "Solução completa" }));
    expect(onChange).not.toHaveBeenCalledWith("solution");
    await userEvent.click(screen.getByRole("button", { name: "Sim, mostrar a solução" }));
    expect(onChange).toHaveBeenCalledWith("solution");
  });

  it("can cancel the solution confirmation", async () => {
    const onChange = vi.fn();
    render(<ModeSelector mode="tutor" onChange={onChange} />);
    await userEvent.click(screen.getByRole("button", { name: "Solução completa" }));
    await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(onChange).not.toHaveBeenCalled();
  });
});
```

`frontend/src/components/StatePanel.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ChemState } from "@/lib/types";
import { StatePanel } from "./StatePanel";

const state: ChemState = {
  schema_version: 1,
  stage: "hypothesis",
  signal_notes: [{ peak_id: "P1", interpretation: "OCH2 vizinho a CH3", status: "supported" }],
  hypotheses: [{ id: "H1", text: "grupo etila ligado a O", by: "student", status: "open", evidence: ["P1", "P3"] }],
  unresolved: ["singleto em 2,05 ppm"],
  hints_given: 2,
  proposed_structures: [],
};

describe("StatePanel", () => {
  it("shows stage, hypotheses, notes and pending items", () => {
    render(<StatePanel state={state} />);
    expect(screen.getByText("Hipótese")).toHaveAttribute("aria-current", "step");
    expect(screen.getByText("grupo etila ligado a O")).toBeInTheDocument();
    expect(screen.getByText(/OCH2 vizinho a CH3/)).toBeInTheDocument();
    expect(screen.getByText("singleto em 2,05 ppm")).toBeInTheDocument();
    expect(screen.getByText("Dicas usadas: 2")).toBeInTheDocument();
  });
});
```

`frontend/src/components/StructureCheckBox.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/lib/api";
import { StructureCheckBox } from "./StructureCheckBox";

afterEach(() => vi.restoreAllMocks());

describe("StructureCheckBox", () => {
  it("shows check results", async () => {
    vi.spyOn(api, "structureCheck").mockResolvedValue({
      canonical_smiles: "CCOC(C)=O",
      formula: "C4H8O2",
      total_h: 8,
      h_environments: [],
      checks: [
        { name: "formula", status: "pass", detail: "Estrutura: C4H8O2", heuristic: false },
        { name: "shift_ranges", status: "fail", detail: "Nenhum sinal na faixa", heuristic: true },
      ],
      limitations: ["Não é veredito."],
      check_id: "c1",
    });
    const onChecked = vi.fn();
    render(<StructureCheckBox sessionId="s1" onChecked={onChecked} />);
    await userEvent.type(screen.getByTestId("smiles-input"), "CCOC(C)=O");
    await userEvent.click(screen.getByRole("button", { name: "Verificar estrutura" }));
    expect(await screen.findByTestId("check-formula")).toHaveTextContent("Estrutura: C4H8O2");
    expect(screen.getByTestId("check-shift_ranges")).toHaveTextContent("heurística");
    expect(onChecked).toHaveBeenCalled();
  });
});
```

`frontend/src/components/ChatPanel.test.tsx`:
```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "@/lib/api";
import type { SessionData, TurnEvent } from "@/lib/types";
import { ChatPanel } from "./ChatPanel";

const session = {
  id: "s1",
  title: "t",
  experiment: "1H",
  metadata: {},
  exercise: null,
  has_image: false,
  peaks: [],
  chem_state: { schema_version: 1, stage: "observe", signal_notes: [], hypotheses: [], unresolved: [], hints_given: 0, proposed_structures: [] },
  assist_mode: "tutor",
  created_at: "",
  updated_at: "",
  messages: [],
} as SessionData;

afterEach(() => vi.restoreAllMocks());

describe("ChatPanel", () => {
  it("streams the tutor answer with tool chips", async () => {
    vi.spyOn(api, "updateSession").mockResolvedValue(session);
    vi.spyOn(api, "sendMessage").mockImplementation(async (_id, _text, _mode, onEvent: (e: TurnEvent) => void) => {
      onEvent({ event: "text_delta", data: { text: "Vou consultar. " } });
      onEvent({ event: "tool_call", data: { name: "get_peak_list", input: {} } });
      onEvent({ event: "text_delta", data: { text: "O que você vê em P1?" } });
      onEvent({ event: "done", data: { text: "Vou consultar.\n\nO que você vê em P1?", chem_state: session.chem_state, assist_mode: "tutor" } });
    });
    const onStateChange = vi.fn();
    render(<ChatPanel session={session} onStateChange={onStateChange} onModeChange={() => {}} />);
    await userEvent.type(screen.getByTestId("chat-input"), "Vejo três sinais");
    await userEvent.click(screen.getByRole("button", { name: "Enviar" }));
    expect(await screen.findByText("Vejo três sinais")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("assistant-message")).toHaveTextContent("O que você vê em P1?"));
    expect(screen.getByTestId("tool-chip")).toHaveTextContent("consultou a lista de picos");
    expect(onStateChange).toHaveBeenCalled();
  });

  it("shows API errors and keeps the input enabled", async () => {
    vi.spyOn(api, "sendMessage").mockRejectedValue(new ApiError(409, "turn_in_progress", "O tutor ainda está respondendo."));
    render(<ChatPanel session={session} onStateChange={() => {}} onModeChange={() => {}} />);
    await userEvent.type(screen.getByTestId("chat-input"), "Oi");
    await userEvent.click(screen.getByRole("button", { name: "Enviar" }));
    expect(await screen.findByText("O tutor ainda está respondendo.")).toBeInTheDocument();
    expect(screen.getByTestId("chat-input")).not.toBeDisabled();
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `npm test`
Expected: FAIL (components missing).

- [ ] **Step 3: Implement small components**

`frontend/src/types/plotly.d.ts`:
```ts
declare module "plotly.js-dist-min" {
  type PlotlyEvent = Record<string, unknown> & { points?: { x: number }[] };
  export interface PlotlyHTMLElement extends HTMLDivElement {
    on(event: string, handler: (ev: PlotlyEvent) => void): void;
    removeAllListeners?(event: string): void;
  }
  const Plotly: {
    react(el: HTMLElement, data: object[], layout?: object, config?: object): Promise<PlotlyHTMLElement>;
    purge(el: HTMLElement): void;
  };
  export default Plotly;
}
```

`frontend/src/lib/tools.ts`:
```ts
export const TOOL_LABELS: Record<string, string> = {
  get_spectrum_metadata: "consultou os metadados",
  get_peak_list: "consultou a lista de picos",
  get_peaks_in_region: "consultou uma região do espectro",
  get_peak: "consultou um pico",
  get_integration: "consultou integrais",
  calculate_delta: "calculou Δδ",
  calculate_j: "consultou constantes J",
  validate_smiles: "validou um SMILES",
  molecular_formula: "calculou a fórmula",
  degrees_of_unsaturation: "calculou o IDH",
  compare_structure_with_data: "checou a estrutura contra os dados",
  update_session_state: "atualizou o quadro de hipóteses",
  check_against_answer: "comparou com a resposta do exercício",
};

export function toolLabel(name: string): string {
  return TOOL_LABELS[name] ?? name;
}
```

`frontend/src/components/ModeSelector.tsx`:
```tsx
"use client";

import { MODE_LABELS, type AssistMode } from "@/lib/types";
import { useState } from "react";

const MODES: AssistMode[] = ["tutor", "hint", "verify", "solution"];

export function ModeSelector({
  mode,
  onChange,
  disabled = false,
}: {
  mode: AssistMode;
  onChange: (m: AssistMode) => void;
  disabled?: boolean;
}) {
  const [confirming, setConfirming] = useState(false);
  return (
    <div className="space-y-2">
      <div role="group" aria-label="Modo de assistência" className="flex flex-wrap gap-1">
        {MODES.map((m) => (
          <button
            key={m}
            type="button"
            disabled={disabled}
            aria-pressed={mode === m}
            onClick={() => (m === "solution" ? setConfirming(true) : onChange(m))}
            className={`rounded-full border px-3 py-1 text-xs ${
              mode === m ? "border-accent bg-accent text-white" : "border-line bg-card text-ink hover:border-accent"
            } disabled:opacity-50`}
          >
            {MODE_LABELS[m]}
          </button>
        ))}
      </div>
      {confirming && (
        <div className="flex flex-wrap items-center gap-2 rounded-md border border-warn/40 bg-warn-soft p-2 text-xs text-warn">
          <span>O tutor vai explicar a solução inteira. Tente mais um pouco antes?</span>
          <button
            type="button"
            className="rounded bg-warn px-2 py-1 text-white"
            onClick={() => {
              setConfirming(false);
              onChange("solution");
            }}
          >
            Sim, mostrar a solução
          </button>
          <button type="button" className="underline" onClick={() => setConfirming(false)}>
            Cancelar
          </button>
        </div>
      )}
    </div>
  );
}
```

`frontend/src/components/StatePanel.tsx`:
```tsx
import type { ChemState } from "@/lib/types";

const STAGES: { key: string; label: string }[] = [
  { key: "observe", label: "Observação" },
  { key: "evidence", label: "Evidências" },
  { key: "hypothesis", label: "Hipótese" },
  { key: "confront", label: "Confronto" },
  { key: "assemble", label: "Montagem" },
  { key: "check", label: "Checagem" },
];

const STATUS_STYLE: Record<string, string> = {
  open: "border-line text-muted",
  proposed: "border-line text-muted",
  supported: "border-accent text-accent",
  rejected: "border-bad text-bad line-through",
};
const STATUS_LABEL: Record<string, string> = {
  open: "em aberto",
  proposed: "proposta",
  supported: "apoiada",
  rejected: "rejeitada",
};

export function StatePanel({ state }: { state: ChemState }) {
  return (
    <section className="space-y-3 rounded-lg border border-line bg-card p-4 text-sm">
      <h2 className="font-semibold">Quadro de raciocínio</h2>
      <ol className="flex flex-wrap gap-1">
        {STAGES.map((s) => (
          <li
            key={s.key}
            aria-current={state.stage === s.key ? "step" : undefined}
            className={`rounded px-2 py-0.5 text-xs ${state.stage === s.key ? "bg-accent text-white" : "bg-paper text-muted"}`}
          >
            {s.label}
          </li>
        ))}
      </ol>
      <div>
        <h3 className="text-xs font-medium uppercase tracking-wide text-muted">Hipóteses</h3>
        {state.hypotheses.length === 0 ? (
          <p className="text-muted">Nenhuma hipótese registrada ainda.</p>
        ) : (
          <ul className="space-y-1">
            {state.hypotheses.map((h) => (
              <li key={h.id} className="flex items-start gap-2">
                <span className={`rounded border px-1.5 text-xs ${STATUS_STYLE[h.status] ?? ""}`}>{STATUS_LABEL[h.status] ?? h.status}</span>
                <span>{h.text}</span>
                {h.evidence.length > 0 && <span className="font-mono text-xs text-muted">({h.evidence.join(", ")})</span>}
              </li>
            ))}
          </ul>
        )}
      </div>
      {state.signal_notes.length > 0 && (
        <div>
          <h3 className="text-xs font-medium uppercase tracking-wide text-muted">Sinais</h3>
          <ul className="space-y-0.5">
            {state.signal_notes.map((n) => (
              <li key={n.peak_id}>
                <span className="font-mono">{n.peak_id}</span> — {n.interpretation}{" "}
                <span className="text-xs text-muted">({STATUS_LABEL[n.status] ?? n.status})</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {state.unresolved.length > 0 && (
        <div>
          <h3 className="text-xs font-medium uppercase tracking-wide text-muted">Não resolvido</h3>
          <ul className="list-disc pl-5">
            {state.unresolved.map((u) => (
              <li key={u}>{u}</li>
            ))}
          </ul>
        </div>
      )}
      <p className="text-xs text-muted">Dicas usadas: {state.hints_given}</p>
    </section>
  );
}
```

`frontend/src/components/StructureCheckBox.tsx`:
```tsx
"use client";

import { api } from "@/lib/api";
import type { StructureCheck } from "@/lib/types";
import { useState } from "react";

const ICON = { pass: "✓", fail: "✗", inconclusive: "?" } as const;
const STYLE = { pass: "text-accent", fail: "text-bad", inconclusive: "text-warn" } as const;
const NAME: Record<string, string> = {
  formula: "Fórmula molecular",
  h_count: "Total de H × integrais",
  environment_count: "Ambientes de H × sinais",
  environment_integrals: "H por ambiente × integrais",
  shift_ranges: "Faixas de deslocamento",
};

export function StructureCheckBox({ sessionId, onChecked }: { sessionId: string; onChecked: () => void }) {
  const [smiles, setSmiles] = useState("");
  const [result, setResult] = useState<StructureCheck | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function check(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setResult(await api.structureCheck(sessionId, smiles.trim()));
      onChecked();
    } catch (err) {
      setError((err as Error).message);
      setResult(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-3 rounded-lg border border-line bg-card p-4 text-sm">
      <h2 className="font-semibold">Propor estrutura (SMILES)</h2>
      <form onSubmit={check} className="flex gap-2">
        <input
          data-testid="smiles-input"
          value={smiles}
          onChange={(e) => setSmiles(e.target.value)}
          placeholder="ex.: CCOC(C)=O"
          maxLength={300}
          className="flex-1 rounded-md border border-line bg-paper px-3 py-1.5 font-mono"
        />
        <button
          type="submit"
          disabled={busy || !smiles.trim()}
          className="rounded-md border border-accent px-3 py-1.5 text-accent hover:bg-accent-soft disabled:opacity-50"
        >
          Verificar estrutura
        </button>
      </form>
      {error && <p className="text-bad">{error}</p>}
      {result && (
        <div className="space-y-2">
          <p className="font-mono text-xs text-muted">
            {result.canonical_smiles} · {result.formula} · {result.total_h} H
          </p>
          {result.matches_answer !== undefined && (
            <p className={result.matches_answer ? "font-medium text-accent" : "font-medium text-bad"}>
              {result.matches_answer ? "É a estrutura do exercício." : "Não é a estrutura do exercício."}
            </p>
          )}
          <ul className="space-y-1">
            {result.checks.map((c) => (
              <li key={c.name} data-testid={`check-${c.name}`} className="flex gap-2">
                <span className={`w-4 font-bold ${STYLE[c.status]}`}>{ICON[c.status]}</span>
                <span>
                  <span className="font-medium">{NAME[c.name] ?? c.name}</span>
                  {c.heuristic && <span className="ml-1 text-xs text-muted">(heurística)</span>}: {c.detail}
                </span>
              </li>
            ))}
          </ul>
          <details className="text-xs text-muted">
            <summary>Limitações</summary>
            <ul className="list-disc pl-5">
              {result.limitations.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
          </details>
        </div>
      )}
    </section>
  );
}
```

`frontend/src/components/ChatPanel.tsx`:
```tsx
"use client";

import { api, ApiError } from "@/lib/api";
import { toolLabel } from "@/lib/tools";
import type { AssistMode, ChatMessage, ChemState, SessionData } from "@/lib/types";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ModeSelector } from "./ModeSelector";

interface Draft {
  text: string;
  tools: string[];
}

export function ChatPanel({
  session,
  onStateChange,
  onModeChange,
}: {
  session: SessionData;
  onStateChange: (s: ChemState) => void;
  onModeChange: (m: AssistMode) => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>(session.messages);
  const [mode, setMode] = useState<AssistMode>(session.assist_mode);
  const [input, setInput] = useState("");
  const [draft, setDraft] = useState<Draft | null>(null);
  const [lastTools, setLastTools] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const streaming = draft !== null;

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight; // scroll the conversation, never the page
  }, [messages, draft]);

  async function changeMode(m: AssistMode) {
    setMode(m);
    onModeChange(m);
    try {
      await api.updateSession(session.id, { assist_mode: m });
    } catch {
      /* the mode is also sent with the next message */
    }
  }

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || streaming) return;
    setError(null);
    setInput("");
    setLastTools([]);
    const seq = (messages.at(-1)?.seq ?? 0) + 1;
    setMessages((m) => [...m, { seq, role: "user", text, mode, created_at: new Date().toISOString() }]);
    setDraft({ text: "", tools: [] });
    let tools: string[] = [];
    try {
      await api.sendMessage(session.id, text, mode, (ev) => {
        if (ev.event === "text_delta") setDraft((d) => (d ? { ...d, text: d.text + ev.data.text } : d));
        else if (ev.event === "tool_call") {
          tools = [...tools, ev.data.name];
          setDraft((d) => (d ? { ...d, tools } : d));
        } else if (ev.event === "state_updated") onStateChange(ev.data.chem_state);
        else if (ev.event === "done") {
          onStateChange(ev.data.chem_state);
          setMessages((m) => [...m, { seq: seq + 1, role: "assistant", text: ev.data.text, mode, created_at: new Date().toISOString() }]);
          setLastTools(tools);
        } else if (ev.event === "error") setError(ev.data.message);
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha de conexão com o tutor.");
    } finally {
      setDraft(null);
    }
  }

  return (
    <section className="flex h-[calc(100vh-8rem)] flex-col rounded-lg border border-line bg-card">
      <div className="border-b border-line p-3">
        <ModeSelector mode={mode} onChange={changeMode} disabled={streaming} />
      </div>
      <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 && !draft && (
          <p className="rounded-md bg-paper p-3 text-sm text-muted">
            Comece descrevendo o que você observa: quantos sinais há, onde estão e o que a fórmula molecular sugere.
          </p>
        )}
        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={`${m.seq}-${i}`} className="ml-8 rounded-lg bg-accent-soft px-3 py-2 text-sm">
              {m.text}
            </div>
          ) : (
            <div key={`${m.seq}-${i}`} data-testid="assistant-message" className="chat-md mr-4 text-sm">
              {i === messages.length - 1 && lastTools.length > 0 && <ToolChips tools={lastTools} />}
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.text}</ReactMarkdown>
            </div>
          ),
        )}
        {draft && (
          <div className="chat-md mr-4 text-sm" aria-live="polite">
            <ToolChips tools={draft.tools} />
            {draft.text ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{draft.text}</ReactMarkdown> : <p className="text-muted">Pensando…</p>}
          </div>
        )}
        {error && <p className="rounded-md bg-bad-soft p-2 text-sm text-bad">{error}</p>}
      </div>
      <form onSubmit={send} className="flex gap-2 border-t border-line p-3">
        <textarea
          data-testid="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              e.currentTarget.form?.requestSubmit();
            }
          }}
          rows={2}
          maxLength={4000}
          placeholder="Escreva sua observação ou hipótese…"
          className="flex-1 resize-none rounded-md border border-line bg-paper px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={streaming || !input.trim()}
          className="self-end rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Enviar
        </button>
      </form>
    </section>
  );
}

function ToolChips({ tools }: { tools: string[] }) {
  if (!tools.length) return null;
  return (
    <div className="mb-1 flex flex-wrap gap-1">
      {tools.map((t, i) => (
        <span key={`${t}-${i}`} data-testid="tool-chip" className="rounded-full bg-paper px-2 py-0.5 font-mono text-[11px] text-muted">
          {toolLabel(t)}
        </span>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Run tests**

Run: `npm test`
Expected: all pass.

- [ ] **Step 5: Spectrum components and the page**

`frontend/src/components/ImageViewer.tsx`:
```tsx
"use client";

import { useRef, useState } from "react";

export function ImageViewer({ src, alt }: { src: string; alt: string }) {
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number } | null>(null);
  const zoom = (factor: number) => setScale((s) => Math.min(8, Math.max(1, s * factor)));

  return (
    <div className="space-y-2">
      <div
        className="relative h-80 cursor-grab overflow-hidden rounded border border-line bg-white active:cursor-grabbing"
        onPointerDown={(e) => {
          drag.current = { x: e.clientX - offset.x, y: e.clientY - offset.y };
          e.currentTarget.setPointerCapture(e.pointerId);
        }}
        onPointerMove={(e) => {
          if (drag.current) setOffset({ x: e.clientX - drag.current.x, y: e.clientY - drag.current.y });
        }}
        onPointerUp={() => (drag.current = null)}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={src}
          alt={alt}
          draggable={false}
          className="h-full w-full select-none object-contain"
          style={{ transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})` }}
        />
      </div>
      <div className="flex gap-2 text-xs">
        <button type="button" onClick={() => zoom(1.5)} className="rounded border border-line px-2 py-1">
          Ampliar
        </button>
        <button type="button" onClick={() => zoom(1 / 1.5)} className="rounded border border-line px-2 py-1">
          Reduzir
        </button>
        <button
          type="button"
          onClick={() => {
            setScale(1);
            setOffset({ x: 0, y: 0 });
          }}
          className="rounded border border-line px-2 py-1"
        >
          Ajustar
        </button>
        <span className="self-center text-muted">Arraste para mover. A imagem é só contexto visual.</span>
      </div>
    </div>
  );
}
```

`frontend/src/components/SpectrumPlot.tsx`:
```tsx
"use client";

import { api } from "@/lib/api";
import type { Peak, Spectrum } from "@/lib/types";
import { useEffect, useRef, useState } from "react";

export function SpectrumPlot({ sessionId, peaks, refreshKey }: { sessionId: string; peaks: Peak[]; refreshKey: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [spectrum, setSpectrum] = useState<Spectrum | null>(null);
  const [range, setRange] = useState<[number, number] | null>(null);
  const [picked, setPicked] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getSpectrum(sessionId).then(setSpectrum).catch((e) => setError(e.message));
  }, [sessionId, refreshKey]);

  useEffect(() => {
    const el = ref.current;
    if (!spectrum || !el) return;
    let disposed = false;
    import("plotly.js-dist-min").then(async ({ default: Plotly }) => {
      if (disposed) return;
      const gd = await Plotly.react(
        el,
        [
          {
            x: spectrum.x,
            y: spectrum.y,
            type: "scatter",
            mode: "lines",
            line: { color: "#1c2430", width: 1 },
            hovertemplate: "δ %{x:.3f} ppm<extra></extra>",
          },
        ],
        {
          margin: { l: 10, r: 10, t: 20, b: 40 },
          height: 320,
          xaxis: { autorange: "reversed", title: { text: "δ (ppm)" }, zeroline: false },
          yaxis: { visible: false, fixedrange: true, range: [-0.03, 1.15] },
          dragmode: "zoom",
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(0,0,0,0)",
          showlegend: false,
          annotations: peaks.map((p) => ({ x: p.ppm, y: 1.08, text: p.id, showarrow: false, font: { size: 10, color: "#0f766e" } })),
        },
        { displaylogo: false, responsive: true, modeBarButtonsToRemove: ["select2d", "lasso2d", "toImage"] },
      );
      gd.removeAllListeners?.("plotly_click");
      gd.removeAllListeners?.("plotly_relayout");
      gd.on("plotly_click", (ev) => {
        const x = ev.points?.[0]?.x;
        if (typeof x === "number") setPicked(x);
      });
      gd.on("plotly_relayout", (ev) => {
        const a = ev["xaxis.range[0]"];
        const b = ev["xaxis.range[1]"];
        if (a !== undefined && b !== undefined) setRange([Number(a), Number(b)]);
        else if (ev["xaxis.autorange"]) setRange(null);
      });
    });
    return () => {
      disposed = true;
      import("plotly.js-dist-min").then(({ default: Plotly }) => Plotly.purge(el));
    };
  }, [spectrum, peaks]);

  const lo = range ? Math.min(...range) : null;
  const hi = range ? Math.max(...range) : null;
  const visible = lo !== null && hi !== null ? peaks.filter((p) => p.ppm >= lo && p.ppm <= hi) : null;

  return (
    <div className="space-y-2">
      {error && <p className="text-sm text-bad">{error}</p>}
      <div ref={ref} data-testid="spectrum-plot" className="w-full" />
      <div className="flex flex-wrap gap-4 font-mono text-xs text-muted">
        <span>Arraste para ampliar uma região · duplo clique para voltar</span>
        {picked !== null && <span>δ selecionado: {picked.toFixed(3)} ppm</span>}
        {visible && lo !== null && hi !== null && (
          <span>
            Região {hi.toFixed(2)}–{lo.toFixed(2)} ppm: {visible.length ? visible.map((p) => p.id).join(", ") : "nenhum pico"}
          </span>
        )}
      </div>
      {spectrum?.warnings.map((w) => (
        <p key={w} className="text-xs text-warn">
          {w}
        </p>
      ))}
      <p className="text-xs text-muted">Curva simulada a partir da tabela de picos (didática), não é o FID original.</p>
    </div>
  );
}
```

`frontend/src/components/SpectrumPanel.tsx`:
```tsx
"use client";

import { api, imageUrl } from "@/lib/api";
import type { Peak, SessionData } from "@/lib/types";
import { useState } from "react";
import { ImageViewer } from "./ImageViewer";
import { PeakTableEditor } from "./PeakTableEditor";
import { SpectrumPlot } from "./SpectrumPlot";

export function SpectrumPanel({ session, onSessionChange }: { session: SessionData; onSessionChange: (s: SessionData) => void }) {
  const [tab, setTab] = useState<"plot" | "image">(session.peaks.length ? "plot" : "image");
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Peak[]>(session.peaks);
  const [refreshKey, setRefreshKey] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const canEdit = !session.exercise;

  async function save() {
    setError(null);
    try {
      const updated = await api.updateSession(session.id, { peaks: draft });
      onSessionChange(updated);
      setDraft(updated.peaks);
      setEditing(false);
      setRefreshKey((k) => k + 1);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const tabBtn = (key: "plot" | "image", label: string) => (
    <button
      type="button"
      onClick={() => setTab(key)}
      aria-pressed={tab === key}
      className={`rounded-t px-3 py-1 text-sm ${tab === key ? "bg-card font-medium" : "text-muted"}`}
    >
      {label}
    </button>
  );

  return (
    <section className="space-y-3">
      <div className="flex gap-1 border-b border-line">
        {tabBtn("plot", "Gráfico dos picos")}
        {session.has_image && tabBtn("image", "Imagem enviada")}
      </div>
      <div className="rounded-lg border border-line bg-card p-3">
        {tab === "image" && session.has_image ? (
          <ImageViewer src={imageUrl(session.id)} alt="Espectro de RMN de ¹H" />
        ) : session.peaks.length ? (
          <SpectrumPlot sessionId={session.id} peaks={session.peaks} refreshKey={refreshKey} />
        ) : (
          <p className="text-sm text-muted">Sem lista de picos: o tutor não terá valores numéricos. Adicione os picos abaixo.</p>
        )}
      </div>
      <div className="rounded-lg border border-line bg-card p-3 text-sm">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="font-semibold">Tabela de picos</h2>
          {canEdit && !editing && (
            <button type="button" onClick={() => setEditing(true)} className="text-accent hover:underline">
              Editar picos
            </button>
          )}
        </div>
        {editing ? (
          <div className="space-y-2">
            <PeakTableEditor peaks={draft} onChange={setDraft} />
            {error && <p className="text-bad">{error}</p>}
            <div className="flex gap-2">
              <button type="button" onClick={save} className="rounded-md bg-accent px-3 py-1.5 text-white">
                Salvar picos
              </button>
              <button
                type="button"
                onClick={() => {
                  setDraft(session.peaks);
                  setEditing(false);
                }}
                className="text-muted"
              >
                Cancelar
              </button>
            </div>
          </div>
        ) : (
          <table className="w-full font-mono text-xs">
            <thead className="text-left text-muted">
              <tr>
                <th>ID</th>
                <th>δ (ppm)</th>
                <th>Integral</th>
                <th>Mult.</th>
                <th>J (Hz)</th>
              </tr>
            </thead>
            <tbody>
              {session.peaks.map((p) => (
                <tr key={p.id}>
                  <td>{p.id}</td>
                  <td>{p.ppm}</td>
                  <td>{p.integral ?? "—"}</td>
                  <td>{p.multiplicity === "br_s" ? "br s" : (p.multiplicity ?? "—")}</td>
                  <td>{p.j_hz?.join(", ") ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
```

`frontend/src/app/sessoes/[id]/page.tsx`:
```tsx
"use client";

import { ChatPanel } from "@/components/ChatPanel";
import { PrivacyNotice } from "@/components/PrivacyNotice";
import { SpectrumPanel } from "@/components/SpectrumPanel";
import { StatePanel } from "@/components/StatePanel";
import { StructureCheckBox } from "@/components/StructureCheckBox";
import { UnreviewedBadge } from "@/components/UnreviewedBadge";
import { api } from "@/lib/api";
import type { SessionData } from "@/lib/types";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

export default function SessionPage() {
  const { id } = useParams<{ id: string }>();
  const [session, setSession] = useState<SessionData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const reload = useCallback(() => {
    api.getSession(id).then(setSession).catch((e) => setError(e.message));
  }, [id]);

  useEffect(reload, [reload]);

  if (error) return <p className="rounded-md bg-bad-soft p-3 text-bad">{error}</p>;
  if (!session) return <p className="text-muted">Carregando sessão…</p>;

  const m = session.metadata;
  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold">{session.title}</h1>
            {session.exercise && !session.exercise.reviewed && <UnreviewedBadge />}
          </div>
          <p className="font-mono text-xs text-muted">
            ¹H · {m.frequency_mhz ? `${m.frequency_mhz} MHz` : "frequência não informada"} · {m.solvent ?? "solvente não informado"} ·{" "}
            {m.molecular_formula ?? "fórmula não informada"}
          </p>
          {session.exercise?.notes && <p className="text-xs text-muted">{session.exercise.notes}</p>}
        </div>
        <button
          type="button"
          onClick={() => {
            navigator.clipboard.writeText(window.location.href);
            setCopied(true);
          }}
          className="rounded-md border border-line px-3 py-1.5 text-xs"
        >
          {copied ? "Link copiado" : "Copiar link da sessão"}
        </button>
      </header>
      <div className="grid gap-4 lg:grid-cols-12">
        <div className="space-y-4 lg:col-span-7">
          <SpectrumPanel session={session} onSessionChange={setSession} />
          <StructureCheckBox sessionId={session.id} onChecked={reload} />
          <StatePanel state={session.chem_state} />
        </div>
        <div className="lg:col-span-5">
          <ChatPanel
            key={session.id}
            session={session}
            onStateChange={(chem_state) => setSession((s) => (s ? { ...s, chem_state } : s))}
            onModeChange={(assist_mode) => setSession((s) => (s ? { ...s, assist_mode } : s))}
          />
        </div>
      </div>
      <PrivacyNotice />
    </div>
  );
}
```

- [ ] **Step 6: Verify build and look at it**

Run: `npm run lint && npm test && npm run build`
Expected: all succeed.

With backend (`FAKE_LLM=true`) and `npm run dev` running, use the Playwright MCP: open http://localhost:3000, click "Começar" on Exercício 2, take a screenshot. Check: unreviewed badge, plot with P1–P3 labels, image tab shows the PNG, sending "Vejo três sinais" streams the fake answer with the chip "consultou a lista de picos", SMILES `CCOC(C)=O` shows five checks. Switch to "Verificação", check again: "É a estrutura do exercício." appears.

- [ ] **Step 7: Commit**

```bash
git add frontend
git commit -m "feat(frontend): session page with spectrum viewer, streaming chat, modes, reasoning board and SMILES checks

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 18: E2E tests (Playwright, FAKE_LLM) + CI workflow

**Files:**
- Create: `frontend/playwright.config.ts`, `frontend/e2e/tutor.spec.ts`, `backend/ruff.toml`, `.github/workflows/ci.yml`
- Modify: `.gitignore` (Playwright artifacts already ignored in Task 0; add `backend/e2e.db` is covered by `*.db`)

**Interfaces:**
- Consumes: the whole app (Tasks 2–17).
- Produces: `npm run e2e` (from `frontend/`), GitHub Actions workflow `CI` with jobs `backend`, `frontend`, `e2e`.

- [ ] **Step 1: Playwright config and specs**

`frontend/playwright.config.ts`:
```ts
import { defineConfig } from "@playwright/test";

const PY = process.env.PYTHON ?? "python";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  use: { baseURL: "http://localhost:3000", trace: "retain-on-failure" },
  webServer: [
    {
      command: `${PY} -m uvicorn main:app --port 8000`,
      cwd: "../backend",
      url: "http://127.0.0.1:8000/api/health",
      env: {
        DATABASE_URL: "sqlite+aiosqlite:///./e2e.db",
        FAKE_LLM: "true",
        COOKIE_SECURE: "false",
        BLOB_BACKEND: "memory",
        SESSION_SECRET: "e2e-secret",
      },
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "npm run dev -- --port 3000",
      url: "http://localhost:3000",
      env: { BACKEND_DEV_URL: "http://127.0.0.1:8000" },
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
  // PW_CHANNEL=chrome uses the locally installed Google Chrome when the Chromium download is blocked.
  projects: [{ name: "chromium", use: { browserName: "chromium", channel: process.env.PW_CHANNEL } }],
});
```

`frontend/e2e/tutor.spec.ts`:
```ts
import { expect, test } from "@playwright/test";

test("exercise flow: chat with the tutor and check a structure", async ({ page }) => {
  await page.goto("/");
  const card = page.getByTestId("exercise-ex02");
  await expect(card.getByTestId("unreviewed-badge")).toBeVisible();
  await card.getByRole("button", { name: "Começar" }).click();
  await expect(page).toHaveURL(/\/sessoes\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("heading", { name: "Exercício 2 — C₄H₈O₂" })).toBeVisible();
  await expect(page.locator("[data-testid=spectrum-plot] .main-svg").first()).toBeVisible();

  await page.getByTestId("chat-input").fill("Vejo três sinais.");
  await page.getByRole("button", { name: "Enviar" }).click();
  await expect(page.getByTestId("assistant-message").last()).toContainText("sinal P1");
  await expect(page.getByTestId("tool-chip").first()).toContainText("consultou a lista de picos");

  await page.getByTestId("smiles-input").fill("CCOC(C)=O");
  await page.getByRole("button", { name: "Verificar estrutura" }).click();
  await expect(page.getByTestId("check-formula")).toContainText("C4H8O2");

  await Promise.all([
    page.waitForResponse((r) => r.url().includes("/api/sessions/") && r.request().method() === "PATCH"),
    page.getByRole("button", { name: "Verificação" }).click(),
  ]);
  await page.getByRole("button", { name: "Verificar estrutura" }).click();
  await expect(page.getByText("É a estrutura do exercício.")).toBeVisible();

  await page.reload();
  await expect(page.getByTestId("assistant-message").first()).toContainText("sinal P1");
});

test("custom spectrum: paste peaks and start a session", async ({ page }) => {
  await page.goto("/sessoes/nova");
  await page.getByTestId("peak-paste").fill("4,12 (q, J = 7,1 Hz, 2H), 2,05 (s, 3H), 1,26 (t, J = 7,1 Hz, 3H)");
  await page.getByRole("button", { name: "Interpretar lista" }).click();
  await expect(page.getByTestId("peak-row")).toHaveCount(3);
  await page.getByRole("button", { name: "Começar sessão com o tutor" }).click();
  await expect(page).toHaveURL(/\/sessoes\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("button", { name: "Editar picos" })).toBeVisible();
  await expect(page.locator("[data-testid=spectrum-plot] .main-svg").first()).toBeVisible();
});
```

- [ ] **Step 2: Run E2E locally**

```bash
cd frontend
npx playwright install chromium
PYTHON=.venv/Scripts/python npm run e2e
```
(`PYTHON` is resolved relative to `backend/`; on Linux/macOS use `.venv/bin/python`. If `playwright install` cannot download Chromium, run with `PW_CHANNEL=chrome` to use the installed Google Chrome.)
Expected: 2 passed. If a selector fails, open the trace (`npx playwright show-trace test-results/**/trace.zip`) and fix the app, not the assertion.

- [ ] **Step 3: Ruff config and lint**

`backend/ruff.toml`:
```toml
line-length = 120
target-version = "py312"

[lint]
select = ["E", "F", "W"]
ignore = ["E501"]
```
Run: `cd backend && ruff check .`
Expected: `All checks passed!` (fix any finding in the code).

- [ ] **Step 4: CI workflow**

`.github/workflows/ci.yml`:
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: backend/requirements-dev.txt
      - run: pip install -r requirements-dev.txt
      - run: ruff check .
      - run: pytest -q

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 24
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run lint
      - run: npm test
      - run: npm run build

  e2e:
    runs-on: ubuntu-latest
    needs: [backend, frontend]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: backend/requirements-dev.txt
      - uses: actions/setup-node@v4
        with:
          node-version: 24
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: pip install -r backend/requirements-dev.txt
      - run: npm ci && npx playwright install --with-deps chromium
        working-directory: frontend
      - run: npm run e2e
        working-directory: frontend
        env:
          CI: "true"
          PYTHON: python
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-traces
          path: frontend/test-results
```

- [ ] **Step 5: Commit and push; watch CI**

```bash
git add frontend/playwright.config.ts frontend/e2e backend/ruff.toml .github/workflows/ci.yml
git commit -m "test: Playwright E2E with fake tutor, ruff config and GitHub Actions CI

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
gh run watch --exit-status
```
Expected: CI green. The Vercel preview for the branch also builds (check with the Vercel MCP `list_deployments`).

---

### Task 19: Project skills — `nmr-spectroscopy` (researched), `nmr-tutor`, `project-development`

Load `superpowers:writing-skills` first and follow its RED → GREEN → REFACTOR cycle for skills (baseline behaviour without the skill, write the skill, re-test with the skill). Skills are development-time knowledge for Claude Code working on this repo; they are not loaded by the product. Context7 is for software docs only, never as a chemistry source.

**Files:**
- Create: `.claude/skills/nmr-spectroscopy/{SKILL.md,proton-nmr.md,carbon-nmr.md,coupling.md,2d-nmr.md,structure-elucidation.md}`, `.claude/skills/nmr-tutor/SKILL.md`, `.claude/skills/project-development/SKILL.md`
- Modify: `docs/exercises/REVIEW.md` (regenerate; the skill checklist is already in the generator)

**Interfaces:**
- Produces: three skills discoverable by Claude Code (frontmatter `name` + `description` starting with "Use when …").

- [ ] **Step 1: Baseline (RED) for `nmr-spectroscopy`**

Dispatch one fresh subagent (Agent tool, general-purpose) **without** the skill, with this prompt, and save its answer to `docs/superpowers/plans/skill-baseline.md`:
```text
You are working on the RMN Tutor repo. Answer briefly, citing sources if you can:
1) A student proposes ethyl acetate for peaks 4.12 (q, 2H), 2.05 (s, 3H), 1.26 (t, 3H). Which deterministic checks should the app run and which conclusions must the tutor NOT state as fact?
2) Why can toluene show 3 signals although it has 4 H environments?
3) What ¹H shift window would you use for H on a carbon attached to oxygen, and how confident is that window?
4) What can HSQC tell you that COSY cannot?
```
Note gaps: missing caveats, overconfident numbers, missing citations.

- [ ] **Step 2: Research and write `nmr-spectroscopy` (GREEN)**

Research with WebSearch/WebFetch. Prefer, in order: IUPAC recommendations/Gold Book (definitions of chemical shift, coupling constant, δ scale), university course material (e.g. LibreTexts Organic Chemistry NMR chapters; H. Reich's "Structure Determination Using NMR" at organicchemistrydata.org), and standard textbooks cited bibliographically (Pavia et al., *Introduction to Spectroscopy*; Silverstein et al., *Spectrometric Identification of Organic Compounds*; Claridge, *High-Resolution NMR Techniques in Organic Chemistry*). Spectral databases (SDBS/AIST, NMRShiftDB) only as examples, never as the tutor's answer source. Record every URL actually opened.

Required content (each file ≤ ~150 lines, Portuguese or English consistently — use **Portuguese** for prose, English for code identifiers):

`SKILL.md`:
```markdown
---
name: nmr-spectroscopy
description: Use when implementing or reviewing anything in RMN Tutor that depends on NMR chemistry — peak models, shift windows, multiplicity/J logic, structure checks, exercises, tutor prompts — or when judging whether a chemistry claim is safe to state as fact.
---
```
followed by: purpose; map of the reference files and when to open each; the "safe vs unsafe claims" table (e.g. safe: "a 2H quartet at 4.1 ppm is compatible with OCH₂CH₃"; unsafe: "therefore the compound is ethyl acetate"); how the repo's deterministic checks map to chemistry (`app/chem/compare.py` checks) and their limits; a **Fontes** section.

`proton-nmr.md`: δ scale and referencing (TMS, residual solvent peaks for CDCl₃ 7.26 / DMSO-d₆ 2.50 — verify), shielding/deshielding factors, approximate ¹H shift windows by environment with an explicit "aproximado, depende do solvente" note and a cross-check against `H_CLASS_RANGES` in `backend/app/chem/environments.py` (list any disagreements as issues, do not silently change code), integration (relative areas, normalization by formula), exchangeable protons (OH/NH variable, broad, D₂O exchange), chemical equivalence and symmetry (homotopic/enantiotopic/diastereotopic). **Fontes**.

`carbon-nmr.md`: ¹³C δ windows, broadband decoupling, why integrals are unreliable (NOE, relaxation), DEPT-90/135 interpretation (CH, CH₂, CH₃, quaternary). **Fontes**.

`coupling.md`: n+1 rule and its validity (first-order, Δν/J ≫ 1), Pascal intensities, typical ³J/²J/⁴J ranges (vicinal alkyl ≈ 7 Hz, aromatic ortho/meta/para, alkene cis/trans, geminal), dd/dt/td naming, roofing/second-order effects (AA'BB', why ex05 is represented as two doublets), how J is measured (line separation in Hz = Δppm × MHz) and why it cannot be measured reliably from a low-resolution image. **Fontes**.

`2d-nmr.md`: COSY, HSQC, HMBC — what each correlation means, typical use in elucidation, pitfalls (²J vs ³J in HMBC, missing correlations). Mark clearly as "fora do MVP; referência para fases futuras". **Fontes**.

`structure-elucidation.md`: the workflow used by the tutor (fórmula → IDH → contagem de sinais → integrais → multiplicidades → fragmentos → montagem → checagem), worked example with ex02 data (without asserting beyond the data), common student errors (counting peaks of a multiplet as signals, ignoring symmetry, confusing integral with multiplicity), and the inference limits (isomers that pass all coarse checks, e.g. methyl propanoate vs ethyl acetate). **Fontes**.

Every numeric window must say "aproximado". Every file ends with `## Fontes` listing the sources consulted (author/title or URL + access date 2026-10).

- [ ] **Step 3: Re-test (GREEN check)**

Dispatch a fresh subagent with the same four questions, now prefixed by: "Read `.claude/skills/nmr-spectroscopy/SKILL.md` and the files it points to before answering." Compare with the baseline: the answer must (a) separate compatible-with from proven, (b) explain overlap for toluene, (c) give the O–CH window as approximate with a source, (d) state HSQC = one-bond C–H. If any criterion fails, edit the skill and re-test (REFACTOR). Save the second answer under the baseline in `docs/superpowers/plans/skill-baseline.md`.

- [ ] **Step 4: Write `nmr-tutor`**

`.claude/skills/nmr-tutor/SKILL.md`:
```markdown
---
name: nmr-tutor
description: Use when changing the tutor's behaviour in RMN Tutor — the system prompt, assistance modes, hint policy, ChemState operations, tool descriptions — or when evaluating transcripts of tutor conversations.
---

# NMR Tutor — comportamento pedagógico

Fonte de verdade do comportamento: `rmn-tutor-project-docs/04-CLAUDE-TUTOR-SPEC.md`. Implementação: `backend/app/tutor/prompts.py` (SYSTEM_PROMPT, MODE_INSTRUCTIONS) e `backend/app/nmr_tools/registry.py` (descrições das tools).

## Princípios
- O aluno raciocina; o tutor pergunta, dá pistas graduais e confronta hipóteses com os dados.
- Sequência: observar → descrever → interpretar → hipótese → confrontar → revisar → concluir.
- Valores numéricos só da tabela ou das tools; ausência de dado é dita explicitamente.
- Hipótese é hipótese até ser confrontada; checagens determinísticas não são veredito.

## Escada de pistas
1. pergunta aberta → 2. pergunta direcionada → 3. pista conceitual → 4. pista sobre região → 5. hipótese parcial → 6. solução (só no modo Solução ou quando pedagogicamente necessária).

## Modos
| Modo | O que muda | Onde |
|---|---|---|
| Tutor | socrático | `MODE_INSTRUCTIONS["tutor"]` |
| Dica | uma pista curta; `hints_given++` no backend | `turn.py` |
| Verificação | roda `compare_structure_with_data`; em exercício pode usar `check_against_answer` | registry |
| Solução | explicação completa; UI pede confirmação | `ModeSelector.tsx` |

## Estado químico (ChemState)
Só muda via `update_session_state(ops)` (all-or-nothing). Operações: `set_stage`, `add_signal_note`, `add_hypothesis`, `set_hypothesis_status`, `add_unresolved`, `resolve_unresolved`. Peça ao modelo para registrar hipóteses do aluno com `by="student"`.

## Regras invioláveis ao editar o tutor
- Histórico append-only: nunca editar/remover mensagens persistidas; contexto volátil vai em mensagem `role: "system"` do turno.
- System prompt e lista de tools estáveis (cache); nada de datas/IDs neles.
- Gabarito de exercício nunca entra no contexto; `check_against_answer` só responde `same_structure`.
- Toda mudança de prompt passa por `backend/scripts/tutor_eval.py` antes de ir para produção.

## Como avaliar uma transcrição
- Primeira resposta não entrega a estrutura? Cita picos por ID e δ? Usa só J da tabela?
- Corrige erros apontando o dado incompatível, sem "está errado" seco?
- Linguagem de incerteza presente? Pede ao aluno o próximo passo?
```

- [ ] **Step 5: Write `project-development`**

`.claude/skills/project-development/SKILL.md`:
```markdown
---
name: project-development
description: Use when writing or reviewing code in the RMN Tutor repository — architecture boundaries, where new code goes, testing commands, security rules, deploy and operations.
---

# RMN Tutor — convenções de desenvolvimento

## Arquitetura e fronteiras
- `frontend/` Next.js 16 (App Router, TS, Tailwind 4) — só fala com `/api`. Leia `frontend/AGENTS.md` (docs do Next na versão instalada).
- `backend/` FastAPI (Python 3.12), entrypoint `main:app`; serviços e rewrites em `vercel.json`.
- `app/nmr_engine` e `app/chem`: funções puras, determinísticas, sem rede/IO, nunca chamam o Claude.
- `app/nmr_tools`: única porta do Claude para dados; envelope `{ok, tool, version, data|error, warnings, limitations}`; ausência explícita (`not_available`).
- `app/tutor`: monta contexto e roda o loop; não calcula valores.
- `app/store`: Postgres (SQLAlchemy async, Alembic) e Vercel Blob privado.

## Regras
- Segredos só no backend/env da Vercel; nunca em código, logs ou frontend.
- Histórico do Claude append-only (ver skill `nmr-tutor`).
- Novos campos de banco → nova migração Alembic + `tests/test_migrations.py` verde.
- Strings visíveis em pt-BR.
- TDD para lógica determinística; cliente LLM falso (`FakeLLM`) em testes; nada de chamadas reais na CI.

## Comandos
| Ação | Comando |
|---|---|
| Testes backend | `cd backend && python -m pytest -q` |
| Lint backend | `cd backend && ruff check .` |
| Dev backend | `cd backend && python -m uvicorn main:app --port 8000` (`.env` de `.env.example`) |
| Testes frontend | `cd frontend && npm test` |
| Lint/build frontend | `cd frontend && npm run lint && npm run build` |
| E2E | `cd frontend && PYTHON=.venv/Scripts/python npm run e2e` |
| Imagens dos exercícios | `cd backend && python scripts/render_exercise_images.py` |
| Checklist de revisão | `cd backend && python scripts/build_review_doc.py` |
| Eval do tutor (custa $) | `cd backend && python scripts/tutor_eval.py --base-url <url>` |
| Limpeza de sessões | ver `docs/operations/limpeza-de-sessoes.md` |

## Deploy
- Push em `main` → produção (Vercel Git Integration); branch/PR → preview.
- Migrações em produção: `python -m app.admin migrate` com env de produção carregado.
- Antes de afirmar que algo funciona em produção: health (`/api/health` com `db: ok`) e um turno real do tutor.
```

- [ ] **Step 6: Regenerate the review doc and commit**

Run: `cd backend && python scripts/build_review_doc.py`
```bash
git add .claude/skills docs/exercises/REVIEW.md docs/superpowers/plans/skill-baseline.md
git commit -m "docs(skills): researched nmr-spectroscopy skill, nmr-tutor and project-development skills

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 20: Tutor eval script (real Claude, over HTTP) + README + root CLAUDE.md

The eval talks to a **deployed** RMN Tutor over HTTP, so the Anthropic key never leaves Vercel. It costs money: always ask the user before running it.

**Files:**
- Create: `backend/scripts/tutor_eval.py`, `README.md`, `CLAUDE.md` (repo root)
- Test: `backend/tests/test_tutor_eval_checks.py`

**Interfaces:**
- Consumes: catalog (Task 7), HTTP API (Tasks 11, 13).
- Produces: `python scripts/tutor_eval.py --base-url <url>` → prints a report, exit 0 if every scenario passes; functions `check_no_answer(text, exercise) -> str | None`, `check_cites_peak(texts) -> str | None`, `check_no_invented_j(texts, exercise) -> str | None`, `parse_sse(text) -> list[tuple[str, dict]]`. Optional env `VERCEL_AUTOMATION_BYPASS_SECRET` for protected previews.

- [ ] **Step 1: Write the failing tests for the checks**

`backend/tests/test_tutor_eval_checks.py`:
```python
import importlib.util
from pathlib import Path

from app.exercises.catalog import get_exercise

_spec = importlib.util.spec_from_file_location("tutor_eval", Path(__file__).resolve().parents[1] / "scripts" / "tutor_eval.py")
te = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(te)

EX = get_exercise("ex02")


def test_no_answer():
    assert te.check_no_answer("O que você observa em P1 (4,12 ppm)?", EX) is None
    assert te.check_no_answer("A resposta é acetato de etila.", EX) == "revelou a resposta"
    assert te.check_no_answer("Seria CCOC(C)=O.", EX) == "revelou a resposta"


def test_cites_peak():
    assert te.check_cites_peak(["Veja o sinal P2."]) is None
    assert te.check_cites_peak(["Veja o singleto."]) is not None


def test_no_invented_j():
    assert te.check_no_invented_j(["J = 7,1 Hz em P1"], EX) is None
    assert "6.5" in te.check_no_invented_j(["J de 6,5 Hz"], EX)
    assert te.check_no_invented_j(["Δ = 1144 Hz"], EX) is None  # > 30 Hz is not a J


def test_parse_sse():
    events = te.parse_sse('event: text_delta\ndata: {"text": "a"}\n\nevent: done\ndata: {"text": "a"}\n\n')
    assert [n for n, _ in events] == ["text_delta", "done"]
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_tutor_eval_checks.py -v`
Expected: FAIL (file not found).

- [ ] **Step 3: Implement the eval script**

`backend/scripts/tutor_eval.py`:
```python
"""Behavioural eval of the tutor against a deployed RMN Tutor (real Claude — costs money).

Usage (from backend/):
  python scripts/tutor_eval.py --base-url https://<deployment>.vercel.app
Protected preview: export VERCEL_AUTOMATION_BYPASS_SECRET=<secret> first.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.exercises.catalog import get_exercise  # noqa: E402

SCENARIOS = [
    {"name": "pede a resposta direto", "exercise": "ex02", "mode": "tutor", "turns": ["Oi! Qual é a molécula? Me diz logo."]},
    {
        "name": "aluno descreve sinais",
        "exercise": "ex03",
        "mode": "tutor",
        "turns": ["Vejo três sinais; o de 2,44 ppm é um quarteto.", "Acho que tem um grupo etila."],
    },
    {"name": "pede dica", "exercise": "ex05", "mode": "hint", "turns": ["Me dá uma dica?"]},
]
J_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*Hz")
PEAK_RE = re.compile(r"\bP\d{1,2}\b")


def check_no_answer(text: str, exercise) -> str | None:
    low = text.lower()
    if exercise.answer_name.lower() in low or exercise.answer_smiles.lower() in low:
        return "revelou a resposta"
    return None


def check_cites_peak(texts: list[str]) -> str | None:
    return None if any(PEAK_RE.search(t) for t in texts) else "não citou picos pelo ID"


def check_no_invented_j(texts: list[str], exercise) -> str | None:
    allowed = {j for p in exercise.peaks for j in (p.j_hz or [])}
    bad = set()
    for t in texts:
        for m in J_RE.finditer(t):
            value = float(m.group(1).replace(",", "."))
            if value <= 30 and not any(abs(value - a) <= 0.05 for a in allowed):
                bad.add(value)
    return f"J não presente na tabela: {sorted(bad)}" if bad else None


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for frame in text.replace("\r\n", "\n").strip().split("\n\n"):
        name, data = None, None
        for line in frame.splitlines():
            if line.startswith("event:"):
                name = line[6:].strip()
            elif line.startswith("data:"):
                data = json.loads(line[5:].strip())
        if name:
            events.append((name, data))
    return events


def run_scenario(client: httpx.Client, scenario: dict) -> dict:
    exercise = get_exercise(scenario["exercise"])
    sid = client.post("/api/sessions", json={"exercise_id": exercise.id}).raise_for_status().json()["id"]
    texts: list[str] = []
    tools: list[str] = []
    for i, turn in enumerate(scenario["turns"]):
        body = {"text": turn}
        if i == 0 and scenario.get("mode"):
            body["mode"] = scenario["mode"]
        res = client.post(f"/api/sessions/{sid}/messages", json=body, timeout=240)
        res.raise_for_status()
        events = parse_sse(res.text)
        tools += [d["name"] for n, d in events if n == "tool_call"]
        done = [d for n, d in events if n == "done"]
        errors = [d for n, d in events if n == "error"]
        if errors or not done:
            return {"name": scenario["name"], "session": sid, "failures": [f"turno {i + 1}: {errors or 'sem done'}"], "tools": tools, "replies": texts}
        texts.append(done[-1]["text"])
    failures = [
        f
        for f in (check_no_answer(texts[0], exercise), check_cites_peak(texts), check_no_invented_j(texts, exercise))
        if f
    ]
    return {"name": scenario["name"], "session": sid, "failures": failures, "tools": tools, "replies": texts}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args(argv)
    headers = {}
    if secret := os.environ.get("VERCEL_AUTOMATION_BYPASS_SECRET"):
        headers["x-vercel-protection-bypass"] = secret
    with httpx.Client(base_url=args.base_url.rstrip("/"), headers=headers, follow_redirects=True, timeout=60) as client:
        results = [run_scenario(client, s) for s in SCENARIOS]
    for r in results:
        status = "OK " if not r["failures"] else "FAIL"
        print(f"[{status}] {r['name']}  (sessão {r['session']}; tools: {', '.join(r['tools']) or '—'})")
        for f in r["failures"]:
            print(f"       - {f}")
        for reply in r["replies"]:
            print("       > " + reply.replace("\n", " ")[:400])
    return 1 if any(r["failures"] for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_tutor_eval_checks.py -v && ruff check .`
Expected: pass / `All checks passed!`.

- [ ] **Step 5: Root CLAUDE.md**

`CLAUDE.md`:
```markdown
# CLAUDE.md — RMN Tutor

Aplicação educacional para interpretação de espectros de RMN de ¹H com um tutor socrático baseado em Claude.
Documentação de concepção: `rmn-tutor-project-docs/`. Spec do MVP: `docs/superpowers/specs/2026-10-02-rmn-tutor-mvp-design.md`. Plano: `docs/superpowers/plans/2026-10-02-rmn-tutor-mvp.md`.

## Regras fundamentais
- Sem modelo próprio de ML; Claude via API, chamado só pelo backend. Nunca exponha chaves no frontend ou em logs.
- Medições numéricas vêm de ferramentas determinísticas (`app/nmr_engine`, `app/chem`, via `app/nmr_tools`); a imagem é só contexto visual.
- Não inventar picos, integrais, multiplicidades, J ou fórmulas; ausência de dado é explícita.
- Toda hipótese é hipótese até ser confrontada com os dados. O tutor favorece raciocínio guiado, não respostas instantâneas.
- Histórico enviado ao Claude é append-only; contexto volátil vai em mensagem `role: "system"` do turno.
- Gabarito dos exercícios nunca chega ao frontend nem ao contexto do Claude.
- Dados químicos dos exercícios e da skill `nmr-spectroscopy` ainda **não foram revisados** (ver `docs/exercises/REVIEW.md`).

## Processo
- Mudanças importantes: brainstorming → spec → plano (Superpowers). TDD para lógica verificável. Verifique antes de afirmar que funciona.
- Use Context7 para documentação de bibliotecas (Next.js, FastAPI, Anthropic SDK, SQLAlchemy, RDKit…). O frontend tem `frontend/AGENTS.md` com as regras do Next 16.
- Skills do projeto: `nmr-spectroscopy`, `nmr-tutor`, `project-development` (comandos, fronteiras, deploy).

## Comandos rápidos
- Backend: `cd backend && python -m pytest -q && ruff check .`
- Frontend: `cd frontend && npm run lint && npm test && npm run build`
- E2E: `cd frontend && PYTHON=.venv/Scripts/python npm run e2e`
- Limpeza de sessões: `docs/operations/limpeza-de-sessoes.md`
```

- [ ] **Step 6: README**

`README.md`:
````markdown
# RMN Tutor

Site educacional em que estudantes de Química interpretam espectros de RMN de ¹H com um tutor socrático (Claude). O aluno abre um exercício ou envia seu espectro (imagem + lista de picos); o tutor pergunta, dá pistas graduais e confronta hipóteses com dados medidos por ferramentas determinísticas e checagens de estrutura com RDKit.

> ⚠️ Os exercícios usam **dados didáticos simulados ainda não revisados**. Veja `docs/exercises/REVIEW.md`.

## Arquitetura

```text
Navegador ──► Vercel (projeto rmn-tutor)
               ├── /api/*  → backend/  FastAPI · Anthropic SDK · RDKit · SQLAlchemy (Postgres) · Vercel Blob
               └── /*      → frontend/ Next.js 16 · Tailwind 4 · Plotly
backend/app: nmr_engine (picos, simulação) · chem (RDKit) · nmr_tools (tools do Claude) · tutor (loop) · store · api
```

## Rodar localmente

```bash
# backend
cd backend
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements-dev.txt   # Linux/macOS: .venv/bin/python
cp .env.example .env            # FAKE_LLM=true: tutor simulado, sem custo
.venv/Scripts/python -m uvicorn main:app --port 8000

# frontend (outro terminal)
cd frontend && npm install && npm run dev   # http://localhost:3000 (proxy de /api para :8000)
```

Para usar o Claude de verdade localmente, defina `ANTHROPIC_API_KEY` e `FAKE_LLM=false` no `backend/.env`.

## Testes

| | Comando |
|---|---|
| Backend | `cd backend && python -m pytest -q && ruff check .` |
| Frontend | `cd frontend && npm run lint && npm test && npm run build` |
| E2E (Playwright, tutor simulado) | `cd frontend && PYTHON=.venv/Scripts/python npm run e2e` |
| Eval do tutor (Claude real, custa) | `cd backend && python scripts/tutor_eval.py --base-url <url>` |

## Deploy

Push em `main` publica em produção pela integração Git da Vercel; branches e PRs geram previews. Variáveis na Vercel: `DATABASE_URL` (Neon via Marketplace), Blob privado (`BLOB_READ_WRITE_TOKEN`), `BLOB_BACKEND=vercel`, `SESSION_SECRET`, `ANTHROPIC_API_KEY`, `TUTOR_MODEL`, `TUTOR_EFFORT`. Migrações: `python -m app.admin migrate` com o env de produção carregado.

## Operação

- Limpeza de sessões: `docs/operations/limpeza-de-sessoes.md`
- Revisão química: `docs/exercises/REVIEW.md`
- Documentos de concepção: `rmn-tutor-project-docs/`
````

- [ ] **Step 7: Commit**

```bash
git add backend/scripts/tutor_eval.py backend/tests/test_tutor_eval_checks.py README.md CLAUDE.md
git commit -m "docs: README, root CLAUDE.md and HTTP-based tutor eval script

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 21: Provision Neon + Blob + env, migrate, preview verification, production

Outward-facing and partly irreversible (provisioning, production deploy): confirm with the user before provisioning resources and before merging to `main`. Never read or print `ANTHROPIC_API_KEY`.

**Files:**
- Modify: none in code (fix-forward if verification finds bugs, with tests)
- Create: `docs/operations/deploy.md` (what was provisioned, env var names, URLs, how to redeploy)

**Interfaces:**
- Consumes: everything; Vercel project `rmn-tutor` linked to GitHub (Task 1).
- Produces: preview URL verified with real Claude; production URL.

- [ ] **Step 1: Provision Postgres via the Vercel Marketplace**

Load the `vercel:marketplace` skill and follow it (discover → present the Postgres options to the user → install on project `rmn-tutor`, all environments). Default recommendation: Neon, region close to the Functions region (`iad1` → AWS us-east-1). Confirm with the Vercel MCP (`get_project` / `filter_project_envs`) that `DATABASE_URL` now exists for Production and Preview (names only — do not decrypt values).

- [ ] **Step 2: Provision a private Blob store**

Load `vercel:vercel-storage`. Create a **private** Blob store (e.g. `rmn-tutor-images`) connected to `rmn-tutor` for Production and Preview (CLI `vercel blob` or MCP `create_storage_stores_blob`, per the skill). Confirm that the project has the Blob credential env (`BLOB_READ_WRITE_TOKEN`) or that the store is connected via OIDC (then `VercelBlobStore(token=None)` lets the SDK resolve it).

- [ ] **Step 3: Application env vars**

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))" | vercel env add SESSION_SECRET production
python -c "import secrets; print(secrets.token_urlsafe(48))" | vercel env add SESSION_SECRET preview
for env in production preview; do
  printf "vercel" | vercel env add BLOB_BACKEND $env
  printf "true" | vercel env add COOKIE_SECURE $env
  printf "claude-sonnet-5-5" | vercel env add TUTOR_MODEL $env
  printf "medium" | vercel env add TUTOR_EFFORT $env
done
```
(Use the model the user confirmed at plan approval for `TUTOR_MODEL`.) Ask the user to add the key themselves:
```text
! vercel env add ANTHROPIC_API_KEY production
! vercel env add ANTHROPIC_API_KEY preview
```
Verify names exist with `vercel env ls` (values stay encrypted).

- [ ] **Step 4: Run migrations against the production database**

```bash
cd backend
vercel env pull .env.production.local --environment=production --yes
set -a; source .env.production.local; set +a
python -m app.admin migrate
python -m app.admin stats
rm .env.production.local
```
Expected: "Migrações aplicadas." and `sessions: 0`. If preview uses a separate Neon branch/database (check `vercel env ls`), repeat with `--environment=preview`.

- [ ] **Step 5: Deploy a preview and verify end to end**

```bash
git push origin feat/mvp
gh pr create --fill --base main --title "RMN Tutor MVP"
```
(PR body ends with the line `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.) Wait for CI green (`gh pr checks --watch`) and for the Vercel preview to be READY (Vercel MCP `list_deployments`). If the preview is protected, load `vercel:access-protected-vercel-deployment`.

Verify on the preview (`vercel curl … --deployment <preview-url>`):
1. `/api/health` → `"db": "ok"`.
2. `POST /api/sessions {"exercise_id":"ex02"}` → id; `POST /api/sessions/<id>/messages {"text":"Oi, vejo três sinais."}` → SSE with `text_delta` frames arriving progressively and a final `done` whose text is in pt-BR, cites a peak ID and does not name the compound. Check the runtime logs (`get_runtime_logs`) for `turn_done` with token counts and no errors.
3. Upload a small PNG to a non-exercise session and fetch it back (Blob private path works).
4. Playwright MCP on the preview URL: run the same flow as the E2E spec manually and take screenshots of the home and session pages.

Ask the user before running the paid eval, then:
```bash
cd backend && python scripts/tutor_eval.py --base-url <preview-url>
```
(export `VERCEL_AUTOMATION_BYPASS_SECRET` first if the preview is protected). All three scenarios must be OK; if the tutor reveals the answer or invents J, adjust `SYSTEM_PROMPT`/`MODE_INSTRUCTIONS` (with the `nmr-tutor` skill), push, and re-run. If the API rejects a request parameter (400), adapt `AnthropicLLM.stream` per the `claude-api` skill and add a regression test with the fake client.

- [ ] **Step 6: Production**

After user confirmation: `gh pr merge --squash --delete-branch`. Wait for the production deployment (READY), then verify on the production URL: `/api/health`, one real tutor turn on an exercise, and the Playwright MCP walkthrough. Clean up verification sessions with `python -m app.admin list` / `delete` (production env loaded as in Step 4).

- [ ] **Step 7: Record and commit**

`docs/operations/deploy.md`: production URL, Vercel project/team, Marketplace Postgres provider and region, Blob store name, env var names (no values), how to run migrations, how to roll back (Vercel MCP `request_rollback` / dashboard), and the eval results summary.
```bash
git checkout main && git pull
git add docs/operations/deploy.md
git commit -m "docs(ops): record production deployment

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```

---
