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
