# CLAUDE.md — RMN Tutor

## Objetivo do projeto

Construir uma aplicação educacional para interpretação de espectros de RMN com um tutor conversacional baseado em Claude.

O usuário faz upload de espectros e interage em um chat. O tutor deve ajudá-lo a resolver a elucidação estrutural passo a passo.

## Regras fundamentais

- Não desenvolver ou treinar um modelo próprio de machine learning para a primeira versão.
- Claude será usado via API.
- Não expor chaves de API no frontend.
- O backend deve controlar chamadas à API e estado da sessão.
- Medições numéricas do espectro devem ser feitas por ferramentas determinísticas sempre que possível.
- A imagem do espectro pode servir como contexto visual, mas não deve ser a única fonte para medições precisas.
- Separar processamento espectral, raciocínio do tutor e interface do usuário.
- O tutor deve favorecer raciocínio guiado, não respostas instantâneas.
- Não inventar picos, integrações, multiplicidades, constantes de acoplamento ou outros dados ausentes.
- Toda hipótese deve ser tratada como hipótese até ser confrontada com os dados disponíveis.
- Não transformar decisões provisórias deste documento em decisões irrevogáveis sem planejamento e revisão.

## Processo de desenvolvimento

- Antes de implementar mudanças importantes, use o fluxo de brainstorming/design do Superpowers.
- Para tarefas de múltiplas etapas, produza plano escrito antes de alterar o código.
- Prefira TDD quando houver lógica verificável.
- Após implementação, faça verificação objetiva antes de afirmar que algo está concluído.
- Use Context7 para documentação atualizada de bibliotecas e APIs quando houver possibilidade de API desatualizada, especialmente Next.js, React, FastAPI, Anthropic SDK, nmrglue e qualquer biblioteca adicional.

## Arquitetura desejada

Frontend
→ Backend/API
→ NMR Engine determinístico
→ ferramentas/MCP de RMN
→ Claude
→ resposta pedagógica

RDKit pode ser usado para validação/manipulação de estruturas moleculares.

## Escopo inicial

Começar pelo menor produto útil:

- upload de um espectro 1H;
- visualização do espectro;
- sessão de chat;
- envio da imagem e metadados ao Claude;
- tutor guiando o aluno;
- extração/representação básica de sinais como próxima etapa;
- estrutura preparada para expansão para 13C e RMN 2D.

## Decisões a confirmar

Não assumir automaticamente:

- framework definitivo do frontend;
- provedor de autenticação;
- banco de dados definitivo;
- formato de espectro suportado na primeira versão;
- estratégia de hospedagem;
- se o NMR MCP será local, embutido no backend ou remoto.

Essas decisões devem ser avaliadas no planejamento.
