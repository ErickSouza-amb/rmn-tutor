# Prompt inicial para o Claude Code

Quero que você assuma este repositório como um novo projeto chamado RMN Tutor.

Antes de escrever qualquer código, leia:

- @CLAUDE.md
- @01-PROJECT-SPEC.md
- @02-ARCHITECTURE.md
- @03-NMR-MCP-SPEC.md
- @04-CLAUDE-TUTOR-SPEC.md
- @05-SKILLS-SPEC.md
- @06-ROADMAP.md
- @08-DECISIONS.md

Use o workflow de planejamento do Superpowers. Comece com brainstorming/descoberta e depois produza um plano de implementação completo antes de tocar no código.

Quando precisar de documentação de bibliotecas, frameworks ou APIs, use Context7 para consultar documentação atualizada e específica da versão que estivermos adotando.

## Objetivo desta sessão

Não implemente ainda.

Quero um plano de projeto tecnicamente rigoroso para chegar a um MVP do RMN Tutor.

## O que analisar

1. Requisitos funcionais e não funcionais.
2. Arquitetura frontend/backend.
3. Fluxo de upload e armazenamento.
4. Integração segura com Claude API.
5. Estratégia de histórico de conversa.
6. Estado químico da sessão.
7. Visualização do espectro.
8. Processamento determinístico do espectro.
9. Uso de nmrglue ou alternativas.
10. Uso de RDKit.
11. Desenho do NMR MCP.
12. Estratégia de testes.
13. Segurança e privacidade.
14. Observabilidade e tratamento de erros.
15. Estratégia de deploy.
16. O que deve ficar fora do MVP.

## Regra essencial

Não aceite automaticamente todas as escolhas presentes nos documentos. Diferencie:

- decisão já tomada;
- proposta inicial;
- questão em aberto;
- requisito técnico;
- hipótese que precisa de validação.

Quando uma escolha depender de tecnologia atual, consulte Context7 antes de recomendar uma implementação.

## Entregável

Produza:

- arquitetura proposta;
- diagrama de componentes;
- estrutura de diretórios;
- decisões tecnológicas com justificativa técnica;
- contrato preliminar das APIs;
- contrato preliminar das tools do NMR MCP;
- plano do MVP;
- plano de testes;
- riscos técnicos;
- questões que precisam de decisão humana;
- ordem exata das próximas tarefas.

Não escreva código de produção nesta etapa.
