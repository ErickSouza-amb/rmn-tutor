# RMN Tutor — Documentação inicial do projeto

Este pacote transforma a conversa de concepção do projeto em documentação consumível pelo Claude Code.

## Como usar

1. Coloque estes arquivos na raiz do novo repositório.
2. Abra o projeto no Claude Code.
3. Use Superpowers para conduzir brainstorming e planejamento antes de escrever código.
4. Use Context7 para documentação atualizada de bibliotecas/APIs.
5. Comece lendo `01-PROJECT-SPEC.md`, `02-ARCHITECTURE.md` e `03-NMR-MCP-SPEC.md`.
6. Depois peça ao Claude Code para usar `07-CLAUDE-CODE-PROMPT.md`.

## Ordem recomendada de leitura

- `CLAUDE.md` — regras permanentes do projeto.
- `01-PROJECT-SPEC.md` — visão, objetivos e requisitos.
- `02-ARCHITECTURE.md` — arquitetura proposta.
- `03-NMR-MCP-SPEC.md` — ferramentas químicas determinísticas e MCP.
- `04-CLAUDE-TUTOR-SPEC.md` — comportamento do tutor de RMN.
- `05-SKILLS-SPEC.md` — Skills específicas a serem criadas.
- `06-ROADMAP.md` — MVP e evolução.
- `07-CLAUDE-CODE-PROMPT.md` — prompt inicial para o planejamento.
- `08-DECISIONS.md` — decisões já tomadas e questões ainda abertas.

## Princípio central

O sistema deve separar três responsabilidades:

**Ferramentas determinísticas:** extraem/medem dados do espectro.

**Claude:** raciocina, formula hipóteses, explica e conduz o aluno.

**Aluno:** participa ativamente da elucidação em vez de apenas receber a resposta.
