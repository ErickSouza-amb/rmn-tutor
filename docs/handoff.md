# Handoff — estado do projeto e contexto para a próxima sessão

> Documento vivo. **Leia antes de mudar qualquer coisa** e atualize ao final de cada sessão (estado, decisões, armadilhas novas). Não repete o que já está em outro lugar: aponta para lá.
> Última atualização: 2026-10-02 (sessão 1: concepção → spec → plano → implementação → deploy).

## 1. Estado atual (2026-10-02)

- **Produção:** https://rmn-tutor.vercel.app — no ar, **tutor simulado** (`FAKE_LLM=true`; banner avisa). `GET /api/health` → `{"db":"ok","tutor":"simulated"}`.
- **Repositório:** https://github.com/ErickSouza-amb/rmn-tutor (público; `main` = produção). MVP entrou pelo PR #1 (squash `d1a9d4c`) + `0d50fc7`.
- **Pronto e testado:** 5 exercícios ¹H (dados simulados, **não revisados**), upload de espectro (imagem + picos), parser pt-BR de picos, gráfico simulado, chat com streaming, modos Tutor/Dica/Verificação/Solução, quadro de raciocínio (ChemState), checagem de SMILES com RDKit, limpeza manual de sessões, 3 skills do projeto.
- **Testes:** backend 167 (pytest), frontend 21 (vitest), E2E 2 (Playwright). CI no GitHub Actions (backend/frontend/e2e) em PR e push para `main`.
- **Banco de produção:** limpo (0 sessões) ao fim da sessão 1.
- **Nunca testado:** o caminho com **Claude real** (`AnthropicLLM`) — ver §6.

## 2. Mapa de documentos (fonte de verdade de cada assunto)

| Assunto | Onde |
|---|---|
| Visão/requisitos originais do usuário | `rmn-tutor-project-docs/` (00–09) |
| Spec aprovada do MVP (decisões e porquês) | `docs/superpowers/specs/2026-10-02-rmn-tutor-mvp-design.md` |
| Plano executado (21 tarefas, contratos, código de referência) | `docs/superpowers/plans/2026-10-02-rmn-tutor-mvp.md` |
| Regras permanentes p/ agentes | `CLAUDE.md` (raiz) |
| Convenções de código, comandos | skill `project-development` (`.claude/skills/project-development/SKILL.md`) |
| Comportamento pedagógico do tutor | skill `nmr-tutor`; código em `backend/app/tutor/prompts.py` |
| Química de RMN + limites das checagens + **9 issues químicas** | skill `nmr-spectroscopy` (`proton-nmr.md` → "Issues para revisão") |
| Deploy, env vars, ligar o Claude real | `docs/operations/deploy.md` |
| Limpeza de sessões | `docs/operations/limpeza-de-sessoes.md` |
| Revisão química pendente (contém respostas!) | `docs/exercises/REVIEW.md` (gerado por `backend/scripts/build_review_doc.py`) |
| Teste RED/GREEN da skill de RMN | `docs/superpowers/plans/skill-baseline.md` |

## 3. Como rodar tudo localmente (Windows + Git Bash)

```bash
# backend (venv já existe em backend/.venv; recriar: python -m venv .venv && .venv/Scripts/python -m pip install -r requirements-dev.txt)
cd backend
cp .env.example .env                       # FAKE_LLM=true, SQLite local (dev.db), Blob em memória
.venv/Scripts/python -m uvicorn main:app --port 8000
.venv/Scripts/python -m pytest -q && .venv/Scripts/ruff check .

# frontend (outro terminal)
cd frontend
npm install
npm run dev                                # http://localhost:3000 — proxy /api → 127.0.0.1:8000 (next.config.ts, só em dev)
npm run lint && npm test && npm run build

# E2E (com backend e frontend já rodando — ver armadilhas)
cd frontend && PW_CHANNEL=chrome npx playwright test     # via PowerShell funciona melhor
```

- SQLite local: as tabelas são criadas no startup (`lifespan` em `app/main.py`) **só** quando `DATABASE_URL` é sqlite. Postgres usa Alembic (`python -m app.admin migrate`).
- Imagens dos exercícios são PNGs versionados; regenere com `python scripts/render_exercise_images.py` após editar YAML (`backend/app/exercises/data/`), e depois `python scripts/build_review_doc.py`.

## 4. Armadilhas do ambiente (descobertas na sessão 1)

**Windows / Git Bash**
- `gh` não está no PATH do Git Bash: use `"/c/Program Files/GitHub CLI/gh.exe"`. Autenticado como `ErickSouza-amb`.
- `vercel curl /api/...` falha com "URL rejected" porque o MSYS converte `/api` em caminho Windows → `export MSYS_NO_PATHCONV=1`. Use o hostname (sem `https://`) em `--deployment`. Args extras de curl vão depois de `--`.
- Console cp1252: imprimir "C₄H₈O" quebrava o CLI (corrigido em `app/admin.py` com `reconfigure(errors="replace")`); vale para scripts novos.
- Existe um **ruff global do usuário** (regras B/BLE/UP); o `backend/ruff.toml` do projeto sobrepõe — rode o ruff sempre de dentro de `backend/`.
- `npm` 11 + vitest 5 exige `@types/node@^24` (já no package.json).
- `create-next-app` gerou `frontend/AGENTS.md`/`CLAUDE.md` (regras do Next 16: ler `node_modules/next/dist/docs/` antes de escrever código Next). Mantidos.
- Nunca use `taskkill //IM python.exe` (mata tudo). Para parar servidores: matar o PID que escuta na porta (`netstat -ano | grep :8000`).

**Playwright / E2E**
- No sandbox do agente, o `webServer` do Playwright não consegue spawnar `cmd.exe` → suba backend e frontend manualmente (em background) e rode os testes (o config reutiliza servidores fora do CI).
- O download do Chromium falhou (timeout) → `PW_CHANNEL=chrome` usa o Chrome instalado. No CI o Chromium baixa normalmente.
- Next 16 bloqueia recursos de dev para outro hostname: abra **`localhost:3000`**, não `127.0.0.1:3000` (há `allowedDevOrigins` como reforço).
- Ao rodar o backend para E2E: `DATABASE_URL=sqlite+aiosqlite:///./e2e.db FAKE_LLM=true COOKIE_SECURE=false BLOB_BACKEND=memory SESSION_SECRET=e2e-secret`.

**Vercel**
- Time `erick-0f6f`, projeto `rmn-tutor` (`prj_oYAD7MRMD93vtHn5KuHrbuGAUjcf`), CLI autenticado como `ericksouza-amb`. **O MCP da Vercel nesta máquina responde 403** para este projeto → use o CLI (`vercel ls/inspect/logs/env`).
- `vercel link`, `vercel integration add` e `vercel blob create-store` **acrescentam `.env*` ao `.gitignore`** (isso passaria a ignorar `backend/.env.example`). Depois de qualquer um desses comandos, troque por `.env.local`.
- Previews exigem login da Vercel (Deployment Protection): teste com `vercel curl ... --deployment <host>`; produção é pública.
- Services: `/api/*` chega ao FastAPI **com** o prefixo `/api` (rotas declaradas com prefixo). RDKit + numpy cabem e carregam (build ~1m20s).
- Corpo de requisição de Functions ≤ 4,5 MB → upload limitado a 4 MB no servidor; o navegador reduz a imagem (`frontend/src/lib/image.ts`).
- Sem `DATABASE_URL`, o backend cai no SQLite padrão e **crasha no lifespan** (aiosqlite não está em `requirements.txt` de produção). Foi o que aconteceu no primeiro deploy.
- Web Analytics ainda não ativado no painel → console mostra 404 de `/_vercel/insights/script.js` (inofensivo).

**Banco (Neon via Marketplace) e Blob**
- Neon `rmn-tutor-db`, mesmo `DATABASE_URL` para Production/Preview/Development (previews escrevem no mesmo banco!).
- Conexão: `postgresql+psycopg` com `NullPool` + `prepare_threshold=None` (pgbouncer do Neon). Normalização da URL em `app/store/db.py`.
- Rodar comandos admin contra produção a partir do Windows: `vercel env pull backend/.env.production.local --environment=production --yes`, exportar `DATABASE_URL`/`BLOB_READ_WRITE_TOKEN` (e `BLOB_BACKEND=vercel`), `PYTHONPATH=. .venv/Scripts/python -m app.admin <cmd>`, **apagar o arquivo** no fim. Não imprima valores.
- Blob privado `rmn-tutor-images` (`BLOB_READ_WRITE_TOKEN`); SDK Python `vercel.blob` (`put_async/get_async/delete_async`, `access="private"`).

## 5. Invariantes que não podem quebrar (resumo; detalhes na spec)

- Histórico do Claude **append-only**; contexto volátil do turno = mensagem `role:"system"` persistida; turno só persiste sistema+assistente+tool_result no sucesso.
- `tool_use` sem `tool_result` nunca é persistido (falha o turno).
- Gabarito (SMILES/nome) nunca vai ao frontend nem ao contexto; `check_against_answer` só responde `same_structure` nos modos Verificação/Solução.
- Valores numéricos só da tabela/tools; sem tabela → `not_available`.
- IDs de pico são estáveis após a criação (PATCH não renumera); imagem não pode ser trocada depois de enviada ao tutor (409 `image_locked`).
- Link da sessão (UUID) é a credencial; cookie `rmn_uid` só lista "Minhas sessões" e chaveia rate limit.

## 6. Problemas abertos e riscos

1. **Claude real nunca exercitado.** `backend/app/tutor/llm.py` usa `client.beta.messages.stream` com `betas=["compact-2026-01-12","server-side-fallback-2026-07-01"]`, `fallbacks="default"`, `context_management`, `output_config={"effort":...}`, `cache_control` top-level e mensagens `role:"system"` no meio da conversa; blocos de resposta são persistidos via `model_dump(mode="json", exclude_none=True)` e reenviados. Qualquer um pode dar 400 — validar com a skill `claude-api` e o eval antes de abrir para alunos.
2. **SSE progressivo pela Vercel não verificado** (o FakeLLM responde de uma vez). Medir na primeira sessão com Claude real.
3. **Modelo do tutor em aberto:** padrão `claude-sonnet-5-5` ($2/$10 por MTok); `claude-opus-5-5` é o dobro e raciocina melhor. Estimativa (não medida): ~US$0,02–0,05 por mensagem com Sonnet.
4. **Química não revisada** (decisão do usuário): exercícios + skill. As 9 issues em `nmr-spectroscopy/proton-nmr.md` (formiatos/formamidas classificados como aldeído, CH₂Cl₂/acetais fora da janela α-heteroátomo, Si–CH₃, `=CH₂` diastereotópico, rotação de amida, janela `exchangeable` larga demais, `shift_ranges` não pareia sinal↔classe, divergência entre fontes) afetam `backend/app/chem/environments.py`/`compare.py`. Notas do ex01 e ex05 dão pistas da resposta.
5. **Lock de turno de 300 s:** se uma Function morrer no meio, a sessão fica bloqueada até expirar; com Claude real, um turno > 300 s poderia colidir no `seq`.
6. **Adiados da revisão final (menores):** secret/Blob sem checagem fail-closed no startup; `chem_state` pode perder um `proposed_structures` se a checagem de SMILES ocorrer durante um turno; `hints_given` conta em turno que falhou e o modo Dica é "grudento"; sessão duplicada se o upload falha após criar; StatePanel mantém `state_updated` de turno que falhou; contexto diz imagem "enviada no início" mesmo quando veio depois; cookie não é setado em rotas que retornam `Response` direto; guarda de descompressão de imagem frouxa (40M px); transação aberta durante o streaming; "Observações" do aluno não chegam ao tutor; FakeLLM cita P1 sem tabela; textarea do chat sem label / erros sem `role="alert"` / `/api/docs` público; sem teste de desconexão do navegador no meio do stream.

## 7. Ideias e próximos passos (do usuário e da spec)

- Ligar o Claude real (procedimento em `docs/operations/deploy.md`), rodar `backend/scripts/tutor_eval.py`, decidir o modelo.
- Revisão química pelos professores → marcar `reviewed: true` nos YAML; corrigir as 9 issues com TDD.
- Fora do MVP, já previsto na arquitetura: dados brutos (JCAMP-DX/Bruker via nmrglue), peak picking automático, ¹³C/DEPT/COSY/HSQC/HMBC (enum `Experiment` já existe), servidor NMR MCP reaproveitando `app/nmr_tools/registry.py`, login/modo professor, métricas pedagógicas e avaliação com estudantes (projeto acadêmico na UFG).
- Mais exercícios curados; checagem de multiplicidade (n+1) no `compare` (hoje nenhuma checagem olha multiplicidade/J — isômeros como propanoato de metila passam em tudo).
- Programas de crédito educacional da Anthropic para custear a API.

## 8. Como trabalhamos (processo)

- Superpowers: brainstorming → spec → plano → execução com TDD → revisão independente do branch → finishing. Mudanças grandes: novo spec/plano em `docs/superpowers/`.
- Trabalhe em branch + PR; o CI precisa ficar verde; merge em `main` publica em produção (confirme com o usuário antes).
- Commits terminam com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; PRs com a linha "🤖 Generated with [Claude Code](https://claude.com/claude-code)".
- Nunca leia/grave/imprima `ANTHROPIC_API_KEY` ou outros segredos; o usuário digita a chave (`! vercel env add ...`).
