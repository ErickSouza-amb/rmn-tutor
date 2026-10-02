# Arquitetura proposta — RMN Tutor

## 1. Princípio

Separar claramente:

1. interface;
2. backend/orquestração;
3. processamento espectral determinístico;
4. ferramentas disponíveis ao Claude;
5. raciocínio pedagógico;
6. persistência.

## 2. Diagrama conceitual

```text
                    USUÁRIO
                       │
                       ▼
              ┌─────────────────┐
              │    FRONTEND     │
              │                 │
              │ upload          │
              │ viewer          │
              │ chat            │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │     BACKEND     │
              │                 │
              │ sessões         │
              │ arquivos        │
              │ API             │
              └───────┬─────────┘
                      │
          ┌───────────┼────────────┐
          ▼           ▼            ▼
   ┌────────────┐ ┌──────────┐ ┌───────────┐
   │ NMR ENGINE │ │ Claude   │ │  RDKit    │
   │ nmrglue    │ │   API    │ │ structures│
   └─────┬──────┘ └────┬─────┘ └───────────┘
         │              │
         └──────┬───────┘
                ▼
          NMR TOOL LAYER
                │
                ▼
             CLAUDE
                │
                ▼
         resposta pedagógica
                │
                ▼
             usuário
```

## 3. Frontend

Possível stack inicial:

- React + Next.js;
- TypeScript;
- componente de gráfico espectral;
- área de upload;
- painel do espectro;
- chat.

A escolha final deve ser validada durante o planejamento com documentação atualizada via Context7.

## 4. Backend

Possível stack inicial:

- Python;
- FastAPI;
- SDK da Anthropic;
- módulo de processamento de RMN;
- camada de persistência;
- autenticação futura.

## 5. NMR Engine

Responsável por tarefas determinísticas:

- leitura de dados;
- normalização/representação;
- metadados;
- detecção/consulta de picos;
- consulta de regiões;
- integrações quando disponíveis;
- medições auxiliares.

A implementação exata deve ser escolhida após investigar os formatos de entrada e os dados que o usuário fornecerá.

## 6. Camada Claude

O Claude deve receber:

- system prompt do tutor;
- histórico da conversa;
- imagem do espectro quando disponível;
- metadados;
- estado químico da sessão;
- resultados de ferramentas;
- instruções do modo de assistência.

## 7. Estado químico

Exemplo conceitual:

```json
{
  "experiment": "1H NMR",
  "molecular_formula": "C6H12O",
  "signals": [
    {
      "ppm": 4.10,
      "integration": 2,
      "multiplicity": "q",
      "status": "hypothesis"
    }
  ],
  "hypotheses": [
    "CH2 ligado a oxigênio"
  ],
  "unresolved": [
    "sinal em 1.25 ppm"
  ]
}
```

Este estado é um exemplo de estrutura, não um schema final.

## 8. Segurança

- API key somente no servidor.
- Validação de uploads.
- Limitação de tamanho de arquivo.
- Não executar dados de usuário como código.
- Separar arquivos temporários e persistentes.
- Registrar erros sem armazenar segredos.

## 9. Arquitetura para evolução

MVP:

imagem → backend → Claude → chat

MVP+:

imagem + dados estruturados → NMR Engine → Claude

Versão avançada:

espectro → NMR Engine → NMR Tools/MCP → Claude tutor → estado químico → interface interativa
