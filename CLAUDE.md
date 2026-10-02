# CLAUDE.md — RMN Tutor

Aplicação educacional para interpretação de espectros de RMN de ¹H com um tutor socrático baseado em Claude.
Documentação de concepção: `rmn-tutor-project-docs/`. Spec do MVP: `docs/superpowers/specs/2026-10-02-rmn-tutor-mvp-design.md`. Plano: `docs/superpowers/plans/2026-10-02-rmn-tutor-mvp.md`.

## Antes de tudo
- **Leia `docs/handoff.md`**: estado atual (produção com tutor simulado), como rodar no Windows, armadilhas de ambiente/Vercel, problemas abertos e próximos passos. Atualize-o ao fim de cada sessão.
- Produção: https://rmn-tutor.vercel.app (`main` publica automaticamente). Trabalhe em branch + PR; merge só com confirmação do usuário.
- Usuário: Erick (UFG), escreve em português; responda em pt-BR.

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

## Armadilhas críticas (detalhes em docs/handoff.md §4)
- Git Bash: `gh` em `"/c/Program Files/GitHub CLI/gh.exe"`; `export MSYS_NO_PATHCONV=1` antes de `vercel curl /api/...`.
- `vercel link` / `integration add` / `blob create-store` acrescentam `.env*` ao `.gitignore` — troque por `.env.local`.
- MCP da Vercel dá 403 neste projeto: use o CLI `vercel`.
- E2E no sandbox: suba os servidores à mão e use `PW_CHANNEL=chrome`; abra `localhost:3000`, não `127.0.0.1`.
- Previews e produção compartilham o mesmo banco Neon.

## Comandos rápidos
- Backend: `cd backend && python -m pytest -q && ruff check .`
- Frontend: `cd frontend && npm run lint && npm test && npm run build`
- E2E: `cd frontend && PYTHON=.venv/Scripts/python npm run e2e`
- Limpeza de sessões: `docs/operations/limpeza-de-sessoes.md`
