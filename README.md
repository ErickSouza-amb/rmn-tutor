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
