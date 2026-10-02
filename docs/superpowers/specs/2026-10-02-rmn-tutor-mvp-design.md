# RMN Tutor — Design do MVP (ciclo 1)

- **Data:** 2026-10-02
- **Status:** aprovado em conversa (seções 1–5); aguardando revisão da spec escrita
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
| Valores químicos dos exercícios | Hipótese a validar | Revisão humana (professor/usuário) antes de uso com alunos |

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

**sessions**: `id uuid pk (v4)`, `owner_uid text idx`, `title text`, `experiment text` ('1H'), `metadata jsonb` ({frequency_mhz, solvent, molecular_formula, notes}), `exercise_id text null`, `image_blob text null`, `peaks jsonb` (Peak[]), `chem_state jsonb` (ChemState), `assist_mode text` (tutor|hint|verify|solution), `history_summary text null`, `summary_upto_seq int null`, `created_at`, `updated_at`.

**messages**: `id uuid pk`, `session_id fk idx`, `seq int` (único por sessão), `role text` (user|assistant), `content jsonb` (blocos Anthropic fiéis: text, image-ref, tool_use, tool_result), `display_text text`, `mode text`, `usage jsonb` (input/output/cache tokens), `created_at`.

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

- Sempre no contexto: system prompt (cache), definições de tools (cache), bloco de sessão (metadados, tabela de picos, ChemState, modo).
- Histórico integral até ~40k tokens estimados; acima disso, mensagens antigas viram `history_summary` (gerado pelo Claude, persistido com `summary_upto_seq`) + últimas 10 trocas.
- Imagem enviada em base64 apenas na primeira mensagem do usuário, com breakpoint de cache; não reenviada em turnos seguintes salvo se o cache expirar (então reenviada uma vez).

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
| POST | `/api/sessions/{id}/image` | multipart `file` → `{ok}`; magic bytes PNG/JPEG/WebP, ≤8 MB, re-encode Pillow |
| GET | `/api/sessions/{id}/image` | → bytes da imagem (só o dono) |
| POST | `/api/peaks/parse` | `{text}` → `{peaks: Peak[], errors: [{line, message}]}` |
| GET | `/api/sessions/{id}/spectrum` | → `{x: ppm[], y: number[], peaks}` simulado |
| POST | `/api/sessions/{id}/messages` | `{text, mode?}` → SSE: `text_delta`, `tool_call`, `tool_result`, `state_updated`, `done`, `error` |
| POST | `/api/sessions/{id}/structure-check` | `{smiles}` → resultado de `compare_structure_with_data` (+ `matches_answer` se exercício e modo permitir) |

Posse: toda rota com `{id}` exige `session.owner_uid == rmn_uid` → senão 404.

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

- **Modelo:** `TUTOR_MODEL` (padrão `claude-sonnet-5-5`, confirmar parâmetros no plano via documentação atual). `max_tokens` por turno configurável.
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
- Upload: magic bytes, ≤8 MB, re-encode Pillow (remove EXIF), dimensão máx. 4096 px (redimensiona).
- Mensagem ≤4000 caracteres; rate limit 30 mensagens/h e 200/dia por uid e por IP (configurável); teto de tokens por sessão (configurável, padrão 400k input acumulado).
- Aviso de privacidade na UI: conteúdo enviado à Anthropic; não enviar dados pessoais.
- Logs JSON estruturados: `request_id`, `session_id`, rota, latência, tokens, tools chamadas, erro; sem corpo de mensagens em nível INFO.
- Vercel Analytics no frontend; runtime logs da Vercel.

## 7. Exercícios curados

Cinco exercícios ¹H (CDCl₃, 400 MHz, **dados didáticos simulados**) em YAML, cada um com: título, dificuldade, fórmula molecular, picos (δ, integral, multiplicidade, J), SMILES de resposta (nunca enviado ao front nem ao contexto do Claude).

1. etanol
2. acetato de etila
3. 2-butanona
4. tolueno
5. 4'-metoxiacetofenona

O plot e uma imagem PNG gerada no backend vêm da simulação Lorentziana dos picos, com desdobramento de primeira ordem pelos J. Valores devem ser revisados por especialista antes de uso com alunos (risco R4).

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

- Git local na raiz `D:\Projeto NMR`; GitHub opcional.
- Projeto Vercel `rmn-tutor`, time `erick-0f6f`, `vercel.json` com `services` (frontend, backend) e rewrites `/api/(.*)` → backend.
- Postgres via Vercel Marketplace (provedor confirmado no provisionamento); Blob privado.
- `ANTHROPIC_API_KEY` inserida pelo usuário (`vercel env add`); nunca lida/gravada pelo agente.
- Preview → verificação E2E na URL → produção.
- Requer Vercel CLI (`npm i -g vercel`).

## 10. Fora do escopo do ciclo 1

- Dados brutos (JCAMP-DX, Bruker, nmrglue), peak picking automático, extração de picos de imagem, J estimado de imagem.
- ¹³C, DEPT, COSY, HSQC, HMBC (apenas enum preparado).
- Servidor NMR MCP separado.
- Login, modo professor, métricas pedagógicas, avaliação com estudantes.
- i18n além de pt-BR.
- Skill completa `nmr-spectroscopy` (exige pesquisa de fontes); neste ciclo apenas `nmr-tutor` e `project-development` enxutas.

## 11. Riscos

| # | Risco | Mitigação |
|---|---|---|
| R1 | Pacote RDKit+numpy+Pillow no Python da Vercel: tamanho/cold start | Spike de deploy na Tarefa 1; limite de 5 GB do Fluid Compute |
| R2 | SSE de longa duração no FastAPI via Services | Spike na Tarefa 1; fallback: resposta não-streaming |
| R3 | Tutor vazar a resposta | Gabarito fora do contexto; tool restrita por modo; eval |
| R4 | Qualidade química dos exercícios | Rotulados como simulados; revisão humana obrigatória |
| R5 | Custo de API sem login | Rate limit + teto de tokens por sessão |
| R6 | Heurística de ambientes de H por simetria canônica falhar em casos de diastereotopia/troca | Check rotulado `heuristic`/`inconclusive`; tutor instruído a não tratar como prova |

## 12. Questões para decisão humana (pendentes)

1. Quem revisará os dados químicos dos 5 exercícios antes de uso com alunos?
2. Haverá repositório GitHub (para CI/Git integration na Vercel) ou deploy via CLI?
3. Política de retenção de sessões (padrão proposto: indefinida no MVP, limpeza manual).
