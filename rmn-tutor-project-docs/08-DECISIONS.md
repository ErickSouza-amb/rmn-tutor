# Decisões e questões abertas

## Decisões já estabelecidas nesta conversa

1. O projeto será um site educacional de interpretação de RMN.
2. O usuário poderá enviar um espectro.
3. Haverá um chat baseado em Claude.
4. O tutor será especializado em conduzir a resolução do espectro.
5. O Claude não deve receber como objetivo principal simplesmente devolver a estrutura final.
6. A primeira versão não depende de treinamento de um modelo próprio de machine learning.
7. O sistema deve separar medições determinísticas do raciocínio do LLM.
8. nmrglue é uma candidata forte para processamento dos dados de RMN em Python.
9. RDKit é uma candidata forte para manipulação/validação de estruturas.
10. Um NMR MCP próprio é uma possível camada de ferramentas para fornecer dados determinísticos ao Claude.
11. O desenvolvimento será planejado com Superpowers.
12. Context7 será usado para documentação atualizada de software/APIs.

## Questões abertas

### Produto

- Qual tipo de arquivo será aceito no MVP?
- O primeiro experimento será exclusivamente 1H?
- O usuário poderá informar a fórmula molecular sempre?
- Haverá exercícios predefinidos ou apenas espectros livres?

### Interface

- React/Next.js é realmente a melhor escolha para o MVP?
- Qual biblioteca será usada para renderizar/interagir com o espectro?
- O usuário poderá selecionar picos e regiões?

### Backend

- FastAPI é a escolha final?
- SQLite ou PostgreSQL?
- Como armazenar espectros e sessões?
- Será necessário login no MVP?

### NMR Engine

- Trabalhar com imagem, dados brutos, CSV exportado ou múltiplos formatos?
- Como detectar picos?
- Como representar integral e multiplicidade?
- Como medir J de forma robusta?

### MCP

- O NMR MCP será implementado como processo local ou servidor remoto?
- O backend chamará as mesmas funções diretamente além do MCP?
- Quais tools entram no MVP?

### IA

- Qual modelo Claude será usado em produção?
- Qual política de fallback?
- Como controlar custo/tamanho de contexto?
- Como preservar o comportamento pedagógico ao longo de conversas longas?

### Pesquisa acadêmica

- O projeto será apenas de desenvolvimento ou também terá avaliação com estudantes?
- Qual protocolo experimental será adotado?
- Quais métricas serão usadas?

## Regra para resolução

Questões abertas devem ser resolvidas durante o planejamento, com documentação atualizada e critérios objetivos, e não por suposição.
