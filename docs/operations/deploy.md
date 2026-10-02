# Deploy — RMN Tutor

## Produção

- URL: https://rmn-tutor.vercel.app
- Projeto Vercel: `erick-0f6f/rmn-tutor` (Git Integration com `ErickSouza-amb/rmn-tutor`)
- Push em `main` → produção; branches/PRs → preview (previews exigem login da Vercel).
- Serviços (`vercel.json`): `frontend/` (Next.js) em `/*`, `backend/` (FastAPI, `main:app`) em `/api/*`.
- Publicado em 2026-10-02 com **tutor simulado** (`FAKE_LLM=true`); o banner do site avisa os visitantes.

## Recursos provisionados

| Recurso | Nome | Como |
|---|---|---|
| Postgres | Neon `rmn-tutor-db` (Vercel Marketplace) | `vercel integration add neon` — injeta `DATABASE_URL` e afins em Production/Preview/Development |
| Imagens | Vercel Blob **privado** `rmn-tutor-images` | `vercel blob create-store rmn-tutor-images --access private` — injeta `BLOB_READ_WRITE_TOKEN` |

## Variáveis de ambiente (nomes; valores ficam na Vercel)

`DATABASE_URL`, `BLOB_READ_WRITE_TOKEN`, `BLOB_BACKEND=vercel`, `SESSION_SECRET`, `COOKIE_SECURE=true`, `FAKE_LLM=true`, `TUTOR_MODEL=claude-sonnet-5-5`, `TUTOR_EFFORT=medium`. Opcionais: `RATE_LIMIT_PER_HOUR` (30), `RATE_LIMIT_PER_DAY` (200), `RATE_LIMIT_IP_PER_HOUR` (300), `RATE_LIMIT_IP_PER_DAY` (2000), `SESSION_INPUT_TOKEN_CAP` (400000).

## Ligar o Claude real

1. Crie uma chave em console.anthropic.com e defina um limite de gasto.
2. `vercel env add ANTHROPIC_API_KEY production` (e `preview`), digitando a chave você mesmo.
3. `vercel env rm FAKE_LLM production` e `vercel env add FAKE_LLM production` com valor `false` (idem preview).
4. Redeploy (push em `main` ou `vercel redeploy`). `/api/health` passa a mostrar `"tutor": "claude"` e o banner some.
5. Rode o eval (custa): `cd backend && python scripts/tutor_eval.py --base-url https://rmn-tutor.vercel.app`.
6. Verifique nos logs (`vercel logs`) os eventos `turn_done` e se o SSE chega progressivamente (risco R2 ainda não verificado com o Claude real).

## Migrações

```bash
cd backend
vercel env pull .env.production.local --environment=production --yes
set -a; source .env.production.local; set +a
python -m app.admin migrate
rm .env.production.local
```

## Rollback

Dashboard da Vercel → Deployments → deploy anterior → "Promote to Production", ou `vercel rollback`.

## Pendências conhecidas

- Web Analytics: ative em Project → Analytics (o script `/_vercel/insights` responde 404 até lá; é inofensivo).
- Revisão química dos exercícios e da skill: `docs/exercises/REVIEW.md`.
- Ajustes menores adiados na revisão final: ver o resumo da entrega no PR #1.
