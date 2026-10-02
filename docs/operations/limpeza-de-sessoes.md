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
