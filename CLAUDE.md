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
