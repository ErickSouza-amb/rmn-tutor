# Skills desejadas para o Claude Code

## Skill 1 — nmr-spectroscopy

### Objetivo

Dar ao Claude Code conhecimento organizado sobre espectroscopia de RMN para desenvolver o produto corretamente.

### Conteúdo sugerido

- 1H NMR;
- 13C NMR;
- deslocamento químico;
- integração;
- multiplicidade;
- acoplamento e J;
- equivalência;
- simetria;
- efeitos de ambiente químico;
- DEPT;
- COSY;
- HSQC;
- HMBC;
- estratégias de elucidação;
- limitações de inferência a partir de espectros.

### Estrutura sugerida

```text
.claude/skills/nmr-spectroscopy/
├── SKILL.md
├── proton-nmr.md
├── carbon-nmr.md
├── coupling.md
├── 2d-nmr.md
└── structure-elucidation.md
```

## Skill 2 — nmr-tutor

### Objetivo

Definir como transformar o conhecimento de RMN em uma experiência de ensino guiado.

### Conteúdo

- questionamento socrático;
- pistas progressivas;
- detecção/correção de erros;
- verificação de hipóteses;
- prevenção de respostas prematuras;
- gerenciamento do estado químico;
- apresentação das evidências.

## Skill 3 — project-development

### Objetivo

Registrar convenções técnicas do projeto e guiar o Claude Code na arquitetura, testes, integração e segurança.

## 6. Processo para criação das Skills

O Claude Code deve criar e testar essas Skills como artefatos próprios do projeto, em vez de começar com arquivos enormes e monolíticos.

Antes de consolidar conteúdo químico, pesquisar fontes confiáveis e verificar definições.

## 7. Uso com Superpowers

Usar o fluxo de brainstorming/design antes de criar uma Skill nova e o fluxo específico para authoring/testing de Skills quando disponível.

## 8. Uso com Context7

Context7 deve ser usado para documentação atualizada de bibliotecas e APIs de software, não como fonte primária de conhecimento químico.
