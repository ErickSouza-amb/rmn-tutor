# Roadmap — RMN Tutor

## Fase 0 — Descoberta e planejamento

Objetivo: eliminar ambiguidades e produzir uma arquitetura implementável.

Entregáveis:

- requisitos refinados;
- arquitetura;
- decisões tecnológicas;
- modelo de dados inicial;
- especificação do NMR MCP;
- plano do MVP;
- critérios de aceitação.

## Fase 1 — MVP conversacional

- frontend básico;
- upload de imagem;
- metadados;
- backend FastAPI;
- Claude API;
- chat persistente;
- tutor com prompt especializado;
- tratamento de erros.

Critério de aceitação:

Um usuário consegue subir um espectro 1H e conduzir uma sessão de interpretação com o tutor.

## Fase 2 — Viewer e interação com o espectro

- zoom;
- seleção de região;
- leitura de ppm;
- marcação de pontos;
- painel de informações.

## Fase 3 — NMR Engine

- suporte estruturado a dados de espectro;
- lista de sinais;
- consulta de regiões;
- integrações;
- funções de medição.

## Fase 4 — NMR MCP

- schemas das tools;
- servidor MCP;
- conexão com engine;
- tratamento de erros;
- testes de contrato das tools.

## Fase 5 — Estrutura molecular

- entrada de SMILES;
- validação com RDKit;
- fórmula e massa;
- comparação básica entre hipótese e dados.

## Fase 6 — Mais experimentos

- 13C;
- DEPT;
- COSY;
- HSQC;
- HMBC.

## Fase 7 — Avaliação educacional

- conjunto de exercícios;
- protocolo de testes com estudantes;
- métricas de acerto e tempo;
- análise das interações;
- limites e falhas do tutor.
