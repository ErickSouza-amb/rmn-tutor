# RMN Tutor — Design do MVP (ciclo 1)

- **Data:** 2026-10-02
- **Status:** aprovado em conversa (seções 1–5) + revisão 1 do usuário incorporada
- **Fontes:** `rmn-tutor-project-docs/` (00–09, CLAUDE.md)

## 1. Entendimento e escopo

### 1.1 Objetivo

Site educacional em pt-BR no qual um estudante de graduação em Química envia um espectro de RMN ¹H (imagem + lista de picos) ou escolhe um exercício pronto, e resolve a elucidação estrutural conversando com um tutor socrático baseado em Claude. O tutor usa ferramentas determinísticas para todo valor numérico e verifica estruturas propostas (SMILES) com RDKit.

### 1.2 Critério de aceitação do ciclo

Em produção na Vercel, um usuário anônimo consegue:

1. abrir um exercício pronto **ou** criar sessão com upload de imagem + metadados + picos digitados/colados;
2. ver a imagem (zoom/pan) e o plot interativo dos picos;
3. conduzir uma sessão de interpretação com o tutor (streaming), alternando modos Tutor/Dica/Verificação/Solução;
4. propor um SMILES e receber checagens determinísticas (fórmula, nº de H, nº de ambientes, faixas de δ);
5. fechar o navegador e reabrir a sessão pelo link com histórico e estado químico preservados.

### 1.3 Classificação das decisões

| Item | Classe | Resolução neste ciclo |
|---|---|---|
| Site educacional, chat com Claude via API, chave só no servidor | Decisão já tomada | Mantida |
| Separar medição determinística do raciocínio do LLM | Decisão já tomada | Mantida (camada `nmr_tools`) |
| Next.js no frontend | Proposta inicial | **Adotada** (Abordagem A) |
| FastAPI no backend | Proposta inicial | **Adotada** (Abordagem A) |
| Formato aceito no MVP | Questão aberta | **Imagem PNG/JPEG/WebP + lista de picos (texto/CSV)** |
| Só ¹H no MVP | Questão aberta | **Sim**; enum de experimento preparado para 13C/DEPT/COSY/HSQC/HMBC |
| Exercícios predefinidos | Questão aberta | **Sim: 5 exercícios ¹H curados + upload livre** |
| Login | Questão aberta | **Não: anônimo + link da sessão (cookie assinado)** |
| Banco | Questão aberta | **Postgres via Vercel Marketplace** |
| Armazenamento de imagens | Questão aberta | **Vercel Blob privado** |
| Acesso ao Claude | Questão aberta | **Chave Anthropic direta, SDK oficial Python** |
| NMR MCP local/remoto | Questão aberta | **Adiado:** no MVP as tools rodam in-process via tool use; servidor MCP é adaptador futuro sobre o mesmo registro |
| nmrglue | Hipótese a validar | **Fora do MVP** (só entra com dados brutos) |
| RDKit na Vercel (tamanho, cold start) | Hipótese a validar | **Spike na Tarefa 1** |
| SSE de longa duração no FastAPI via Vercel Services | Hipótese a validar | **Spike na Tarefa 1** |
| Valores químicos dos exercícios | Hipótese a validar | **Não revisados neste ciclo**; marcados `reviewed: false` + checklist em `docs/exercises/REVIEW.md` para revisão posterior do usuário |
| Repositório / CI | Questão aberta | **GitHub + Git Integration da Vercel** (deploy automático: push em `main` → produção, PR → preview) |
| Retenção de sessões | Questão aberta | **Indefinida; limpeza manual pelo usuário via script `admin`** (§6.1) |
| Skill `nmr-spectroscopy` | Proposta inicial | **No escopo**, com pesquisa e citação de fontes (§10.1) |

## 2. Arquitetura

### 2.1 Componentes

```text
Navegador
  │  HTTPS + cookie anônimo assinado rmn_uid
  ▼
Projeto Vercel "rmn-tutor"   (vercel.json → services + rewrites)
  ├── /api/*  → backend  (FastAPI, Python 3.12, Fluid Compute)
  └── /*      → frontend (Next.js App Router, TypeScript, Tailwind)

frontend/
  /                 início: Novo espectro | Exercícios | Minhas sessões
  /sessoes/nova     upload + metadados + picos (tabela editável / colar CSV)
  /sessoes/[id]     SpectrumPanel | ChatPanel | StatePanel
                    SpectrumPanel: imagem (zoom/pan) + plot dos picos (Plotly)
                    ChatPanel: streaming SSE, seletor de modo, caixa "propor SMILES"
                    StatePanel: hipóteses, sinais interpretados, não resolvidos

backend/
  app/api/          rotas HTTP, dependências (cookie, posse, rate limit)
  app/tutor/        prompt builder, loop de tool use, modos, compactação, cliente LLM
  app/nmr_engine/   PURO: Peak, parser, consultas de região, Δppm, J, simulação
  app/chem/         PURO: RDKit (SMILES, fórmula, massa, IDH, ambientes de H, comparação)
  app/nmr_tools/    registro de tools: schema JSON v1 + handler → engine/chem/store
  app/store/        SQLAlchemy (Postgres) + cliente Blob
  app/exercises/    catálogo YAML curado
  migrations/       Alembic
```

### 2.2 Fronteiras

- `nmr_engine` e `chem` são funções puras, determinísticas, sem rede e sem I/O; nunca chamam o Claude.
- `nmr_tools` é a única porta do Claude para dados. Toda tool retorna o envelope `{ok, tool, version, data, warnings[], limitations[]}`; ausência de dado é explícita (`not_available`).
- `tutor` monta contexto e executa o loop; não calcula valores.
- O frontend nunca chama a Anthropic; só fala com `/api`.
- Imagem = contexto visual; tabela de picos = fonte numérica oficial. Sessão com imagem sem picos é permitida, e o tutor declara que só tem leitura visual.

## 3. Modelo de dados

### 3.1 Tabelas (Postgres, Alembic)

**sessions**: `id uuid pk (v4)`, `owner_uid text idx`, `title text`, `experiment text` ('1H'), `metadata jsonb` ({frequency_mhz, solvent, molecular_formula, notes}), `exercise_id text null`, `image_blob text null`, `peaks jsonb` (Peak[]), `chem_state jsonb` (ChemState), `assist_mode text` (tutor|hint|verify|solution), `turn_lock_until timestamptz null` (impede turnos concorrentes), `created_at`, `updated_at`.

**messages**: `id uuid pk`, `session_id fk idx`, `seq int` (único por sessão), `role text` (user|assistant|system), `content jsonb` (blocos Anthropic fiéis: text, image-ref, tool_use, tool_result), `display_text text`, `mode text`, `usage jsonb` (input/output/cache tokens), `created_at`.

**structure_checks**: `id uuid pk`, `session_id fk`, `smiles text`, `result jsonb`, `created_at`.

**rate_events**: `id bigserial`, `key text idx` (uid:<x> ou ip:<x>), `created_at idx`. Janela deslizante por contagem.

### 3.2 Peak (v1)

```json
{"id":"P1","ppm":4.12,"integral":2.0,"multiplicity":"q","j_hz":[7.1],"source":"user|exercise","note":null}
```

Multiplicidades aceitas: `s d t q quint sext sept m dd dt td ddd br_s`. Campos ausentes = `null`, nunca inferidos. Limites: ≤200 picos; ppm ∈ [-2, 16]; integral > 0; J ∈ (0, 30] Hz.

### 3.3 ChemState (v1)

```json
{
  "schema_version": 1,
  "stage": "observe|evidence|hypothesis|confront|assemble|check",
  "signal_notes": [{"peak_id":"P1","interpretation":"...","status":"proposed|supported|rejected"}],
  "hypotheses": [{"id":"H1","text":"...","by":"student|tutor","status":"open|supported|rejected","evidence":["P1"]}],
  "unresolved": ["..."],
  "hints_given": 0,
  "proposed_structures": [{"smiles":"...","check_id":"..."}]
}
```

O Claude altera o estado **somente** via `update_session_state(ops[])` com operações tipadas (`set_stage`, `add_signal_note`, `add_hypothesis`, `set_hypothesis_status`, `add_unresolved`, `resolve_unresolved`). O backend valida e grava; operação inválida → erro no `tool_result`, sem alterar estado.

### 3.4 Histórico e contexto

**Histórico append-only (requisito da API atual):** os modelos atuais vinculam blocos de raciocínio ao histórico exato que os produziu; editar ou remover turnos anteriores invalida esses blocos (e contas novas recebem erro 400). Portanto:

- O histórico enviado é exatamente a sequência persistida em `messages`, sem edição, resumo local ou remoção.
- System prompt e definições de tools são estáveis (cache); nada volátil neles.
- O contexto volátil de cada turno (metadados, tabela de picos, ChemState, modo) vai numa **mensagem de sistema no meio da conversa** (`role: "system"`) logo após a mensagem do usuário, e é persistida (cópias anteriores ficam no histórico).
- Conversas longas usam a **compactação do lado do servidor** da API (beta `compact-2026-01-12`); os blocos de compactação retornados são persistidos como parte do conteúdo do assistente.
- A imagem vai em base64 na primeira mensagem do usuário e é reconstruída byte a byte idêntica a cada requisição (mesmo blob re-encodado), preservando o prefixo de cache.
- Atomicidade: a mensagem do usuário é persistida ao chegar; a mensagem de sistema do turno e as mensagens do assistente/tool_result só são persistidas juntas ao fim do turno bem-sucedido. Um turno que falha não deixa sequência inválida (usuários consecutivos são permitidos pela API).

## 4. Contratos

### 4.1 API HTTP (`/api`, erros `{"error":{"code","message"}}`)

| Método | Rota | Entrada → Saída |
|---|---|---|
| GET | `/api/health` | → `{status, version, db}` |
| GET | `/api/exercises` | → `[{id, title, difficulty, experiment, metadata}]` (sem resposta) |
| POST | `/api/sessions` | `{experiment, metadata, peaks?, exercise_id?, title?}` → `{id}`; define cookie se ausente |
| GET | `/api/sessions` | → sessões do `rmn_uid` (id, title, updated_at) |
| GET | `/api/sessions/{id}` | → sessão + peaks + chem_state + mensagens (`display_text`, role, mode) |
| PATCH | `/api/sessions/{id}` | `{metadata?, peaks?, assist_mode?, title?}` → sessão |
| POST | `/api/sessions/{id}/image` | multipart `file` → `{ok}`; magic bytes PNG/JPEG/WebP, ≤4 MB, re-encode Pillow |
| GET | `/api/sessions/{id}/image` | → bytes da imagem (só o dono) |
| POST | `/api/peaks/parse` | `{text}` → `{peaks: Peak[], errors: [{line, message}]}` |
| GET | `/api/sessions/{id}/spectrum` | → `{x: ppm[], y: number[], peaks}` simulado |
| POST | `/api/sessions/{id}/messages` | `{text, mode?}` → SSE: `text_delta`, `tool_call`, `tool_result`, `state_updated`, `done`, `error` |
| POST | `/api/sessions/{id}/structure-check` | `{smiles}` → resultado de `compare_structure_with_data` (+ `matches_answer` se exercício e modo permitir) |

Acesso: o **link da sessão é a credencial** (UUID v4 não adivinhável). Quem tem o link pode abrir e continuar a sessão, em qualquer navegador. `owner_uid` serve apenas para listar "Minhas sessões" e para rate limit. Sessão inexistente → 404. Um turno em andamento na mesma sessão → 409.

### 4.2 Tools do Claude (`nmr_tools` v1)

Leitura:
- `get_spectrum_metadata()`
- `get_peak_list()`
- `get_peaks_in_region(ppm_start, ppm_end)`
- `get_peak(peak_id? | ppm?, tolerance_ppm=0.05)`
- `get_integration(ppm_start, ppm_end)`: soma das integrais informadas; normalização por nº de H da fórmula quando houver; `not_available` se faltar integral em algum pico da região
- `calculate_delta(peak_a, peak_b)`
- `calculate_j(peak_id)`: devolve `j_hz` informado; sem dado → `not_available` + `limitations`

Química (RDKit):
- `validate_smiles(smiles)`
- `molecular_formula(smiles)`: fórmula, MW, massa exata
- `degrees_of_unsaturation(formula? | smiles?)`
- `compare_structure_with_data(smiles)`: checks individuais `pass|fail|inconclusive`:
  - fórmula vs. fórmula informada;
  - nº total de H vs. soma das integrais (com normalização);
  - nº de ambientes de H distintos (ranking canônico de simetria) vs. nº de sinais;
  - faixa de δ esperada por tipo de H (tabela heurística, marcada `heuristic`).
  Nunca um veredito único "correto".

Estado:
- `update_session_state(ops[])`

Restrita (só modos `verify`/`solution` em sessão de exercício):
- `check_against_answer(smiles)` → `{same_structure: bool}` por InChIKey, sem revelar a resposta

Regras: nenhuma tool consulta base externa; SMILES ≤300 caracteres; números com unidade; incerteza e heurística sempre rotuladas.

## 5. Tutor

- **Modelo:** `TUTOR_MODEL` (padrão `claude-sonnet-5-5`), `TUTOR_EFFORT` (padrão `medium`); raciocínio adaptativo (padrão do modelo), com blocos de raciocínio persistidos e reenviados sem alteração. `max_tokens` por turno configurável (padrão 16000).
- **Fallback de recusa:** parâmetro `fallbacks: "default"` (beta `server-side-fallback-2026-07-01`) habilitado por padrão.
- **System prompt:** derivado de `04-CLAUDE-TUTOR-SPEC.md` (fluxo A–F, escada de 6 pistas, tratamento de erro, linguagem de incerteza, proibições) + regras: citar picos por ID e δ; usar apenas valores da tabela/tools; declarar dado ausente; priorizar tabela sobre imagem em divergência; nunca revelar SMILES de gabarito.
- **Modos (instrução por turno):**
  - Tutor: socrático.
  - Dica: uma pista curta, `hints_given++`.
  - Verificação: rodar `compare_structure_with_data` e confrontar.
  - Solução: explicação integral, só após confirmação explícita na UI.
- **Loop:** até 6 iterações de tool use por turno; cada chamada validada (Pydantic), executada, logada e emitida via SSE.
- **Falhas:** 1 retry com backoff em 429/5xx/overloaded; depois evento `error` amigável. A mensagem do aluno fica persistida e pode ser reenviada.

## 6. Segurança, limites e observabilidade

- Segredos (`ANTHROPIC_API_KEY`, `DATABASE_URL`, `BLOB_READ_WRITE_TOKEN`, `SESSION_SECRET`) só no backend/Vercel env; nunca em logs.
- Cookie `rmn_uid`: httpOnly, Secure, SameSite=Lax, assinado (itsdangerous) com `SESSION_SECRET`.
- Links de sessão são segredos: a UI avisa que quem tiver o link acessa a sessão.
- Upload: magic bytes, ≤4 MB no servidor (limite de 4,5 MB do corpo de requisição das Vercel Functions; o navegador reduz imagens maiores para ≤2048 px antes de enviar), re-encode Pillow (remove EXIF), dimensão máx. 2048 px (redimensiona).
- Mensagem ≤4000 caracteres; rate limit 30 mensagens/h e 200/dia por uid e por IP (configurável); teto de tokens por sessão (configurável, padrão 400k input acumulado).
- Aviso de privacidade na UI: conteúdo enviado à Anthropic; não enviar dados pessoais.
- Logs JSON estruturados: `request_id`, `session_id`, rota, latência, tokens, tools chamadas, erro; sem corpo de mensagens em nível INFO.
- Vercel Analytics no frontend; runtime logs da Vercel.

### 6.1 Limpeza manual de sessões

Script de administração executado localmente pelo usuário (credenciais via `vercel env pull`):

```bash
cd backend
python -m app.admin list   [--older-than 30d] [--exercise ID]       # lista id, título, criada, nº msgs
python -m app.admin delete --session <uuid> [--yes]                 # apaga 1 sessão
python -m app.admin purge  --older-than 30d [--dry-run] [--yes]     # apaga em lote
python -m app.admin stats                                           # contagem, tokens acumulados
```

- Apaga em cascata: mensagens, structure_checks e o blob da imagem.
- Sempre mostra o que será apagado e pede confirmação (salvo `--yes`); `--dry-run` não altera nada.
- Purga também `rate_events` com mais de 2 dias.
- Documentado em `docs/operations/limpeza-de-sessoes.md`.

## 7. Exercícios curados

Cinco exercícios ¹H (CDCl₃, 400 MHz, **dados didáticos simulados**) em YAML, cada um com: título, dificuldade, fórmula molecular, picos (δ, integral, multiplicidade, J), SMILES de resposta (nunca enviado ao front nem ao contexto do Claude).

1. etanol
2. acetato de etila
3. 2-butanona
4. tolueno
5. 4'-metoxiacetofenona

O plot e uma imagem PNG gerada no backend vêm da simulação Lorentziana dos picos, com desdobramento de primeira ordem pelos J.

**Revisão adiada (decisão do usuário):** os dados não são conferidos neste ciclo.
- Cada YAML leva `reviewed: false`, `reviewed_by: null`, `sources: []`.
- A UI exibe o selo "dados não revisados" enquanto `reviewed: false`.
- `docs/exercises/REVIEW.md` reúne, por exercício, a tabela de picos, o SMILES, a fórmula, a imagem gerada e um checklist (δ, integral, multiplicidade, J, solvente), para o usuário conferir e então marcar `reviewed: true`.

## 8. Testes

- **Backend (pytest, TDD):**
  - `nmr_engine` (parser, consultas, Δ, J, simulação: área ∝ integral);
  - `chem` (moléculas de referência);
  - `nmr_tools` (contrato: schema, envelope, `not_available`, limites);
  - `tutor` (cliente LLM falso roteirizado: loop, compactação, não vazamento do gabarito, modos);
  - `api` (TestClient + Postgres de teste: posse, rate limit, upload, SSE).
- **Frontend (Vitest + Testing Library):** parser SSE, tabela de picos, seletor de modo.
- **E2E (Playwright):** exercício → conversa → SMILES, com `FAKE_LLM=1`.
- **Eval do tutor (fora da CI):** script com 3 conversas-padrão contra o Claude real. Verifica:
  - sem resposta no turno 1;
  - picos citados por ID;
  - sem J inventado.

## 9. Deploy

- Git na raiz `D:\Projeto NMR`, publicado em repositório **GitHub** (nome proposto `rmn-tutor`, visibilidade a confirmar na criação). Requer GitHub CLI (`gh`) instalado e `gh auth login` feito pelo usuário.
- **Git Integration da Vercel:** projeto Vercel conectado ao repositório; push em `main` → deploy de produção; cada PR/branch → preview.
- Projeto Vercel `rmn-tutor`, time `erick-0f6f`, `vercel.json` com `services` (frontend, backend) e rewrites `/api/(.*)` → backend.
- Postgres via Vercel Marketplace (provedor confirmado no provisionamento); Blob privado.
- `ANTHROPIC_API_KEY` inserida pelo usuário (`vercel env add`); nunca lida/gravada pelo agente.
- Preview (branch) → verificação E2E na URL → merge em `main` → produção.
- Requer Vercel CLI (`npm i -g vercel`).

## 10. Fora do escopo do ciclo 1

- Dados brutos (JCAMP-DX, Bruker, nmrglue), peak picking automático, extração de picos de imagem, J estimado de imagem.
- ¹³C, DEPT, COSY, HSQC, HMBC (apenas enum preparado).
- Servidor NMR MCP separado.
- Login, modo professor, métricas pedagógicas, avaliação com estudantes.
- i18n além de pt-BR.

### 10.1 Skills do projeto (no escopo)

Criadas com o fluxo `superpowers:writing-skills` (testar a skill antes de consolidar):

- `.claude/skills/nmr-spectroscopy/`: `SKILL.md`, `proton-nmr.md`, `carbon-nmr.md`, `coupling.md`, `2d-nmr.md`, `structure-elucidation.md`.
  - Conteúdo pesquisado em fontes confiáveis (IUPAC, livros-texto de referência, material didático universitário, documentação de bancos como SDBS/NMRShiftDB apenas como referência).
  - Cada arquivo com seção **Fontes** (citação + URL quando houver).
  - Faixas numéricas marcadas como aproximadas; limitações de inferência explícitas.
  - Conteúdo químico também não revisado por especialista: mesmo selo e entrada em `docs/exercises/REVIEW.md` (seção "Skill").
- `.claude/skills/nmr-tutor/`: questionamento socrático, escada de pistas, correção de erros, estado químico.
- `.claude/skills/project-development/`: convenções de arquitetura, testes, segurança e deploy deste repositório.

## 11. Riscos

| # | Risco | Mitigação |
|---|---|---|
| R1 | Pacote RDKit+numpy+Pillow no Python da Vercel: tamanho/cold start | Spike de deploy na Tarefa 1; limite de 5 GB do Fluid Compute |
| R2 | SSE de longa duração no FastAPI via Services | Spike na Tarefa 1; fallback: resposta não-streaming |
| R3 | Tutor vazar a resposta | Gabarito fora do contexto; tool restrita por modo; eval |
| R4 | Qualidade química dos exercícios | Rotulados como simulados; revisão humana obrigatória |
| R5 | Custo de API sem login | Rate limit + teto de tokens por sessão |
| R6 | Heurística de ambientes de H por simetria canônica falhar em casos de diastereotopia/troca | Check rotulado `heuristic`/`inconclusive`; tutor instruído a não tratar como prova |

## 12. Decisões humanas

Resolvidas em 2026-10-02:

1. Exercícios: sem revisão neste ciclo; checklist salvo para revisão posterior (§7).
2. GitHub + deploy automático pela Vercel (§9).
3. Sessões guardadas; limpeza manual facilitada por script (§6.1).
4. Skill `nmr-spectroscopy` no escopo, com pesquisa de fontes (§10.1).

Pendentes (não bloqueiam o plano):

- Visibilidade do repositório GitHub (público/privado), perguntada na criação.
