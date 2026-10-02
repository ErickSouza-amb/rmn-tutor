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
