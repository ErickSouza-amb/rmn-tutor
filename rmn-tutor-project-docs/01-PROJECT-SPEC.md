# Especificação do Projeto — RMN Tutor

## 1. Visão

Criar um site educacional no qual um estudante de Química possa enviar/dar upload em um espectro de RMN e conversar com um tutor baseado em Claude para realizar a interpretação do espectro de forma guiada.

A proposta não é simplesmente perguntar ao Claude "qual é a molécula?". O diferencial é construir um tutor especializado em elucidação estrutural, que ajude o estudante a observar evidências, formular hipóteses, testar essas hipóteses e revisar inconsistências.

## 2. Objetivo geral

Investigar e demonstrar como uma IA generativa multimodal pode funcionar como ferramenta de apoio ao ensino e à interpretação de espectros de RMN, mantendo o estudante no centro do processo de raciocínio.

## 3. Objetivos específicos

- Permitir upload de espectros.
- Exibir o espectro de forma interativa.
- Permitir que o usuário forneça metadados: tipo de RMN, frequência, solvente, fórmula molecular etc.
- Enviar imagem + informações estruturadas ao Claude.
- Manter o histórico da conversa.
- Fazer o tutor perguntar ao estudante o que ele observa.
- Fornecer dicas graduais.
- Corrigir erros conceituais sem simplesmente entregar a resposta.
- No final, verificar se a estrutura proposta explica os dados.
- Construir uma arquitetura extensível para 1H, 13C, DEPT, COSY, HSQC e HMBC.

## 4. Usuário-alvo

Primeiro foco: estudantes de graduação em Química que estejam estudando RMN e elucidação estrutural.

Possíveis usuários futuros: professores, monitores e estudantes de iniciação científica.

## 5. Fluxo principal

1. Usuário abre o projeto.
2. Seleciona o tipo de experimento.
3. Faz upload do espectro.
4. Informa os metadados disponíveis.
5. O sistema cria uma sessão de análise.
6. O tutor recebe o espectro como contexto.
7. O tutor inicia a conversa.
8. O aluno observa, responde e propõe hipóteses.
9. O tutor usa dados numéricos/ferramentas quando necessário.
10. O sistema mantém o estado químico da sessão.
11. Ao final, o tutor executa uma checagem de consistência.

## 6. Funcionalidades do MVP

### Obrigatórias

- Upload de imagem de espectro.
- Cadastro de tipo de RMN.
- Cadastro de solvente, frequência e fórmula molecular quando disponíveis.
- Visualização do espectro.
- Chat com Claude.
- Histórico da sessão.
- System prompt especializado em RMN.
- Modo tutor guiado.

### Desejáveis para o MVP expandido

- Seleção de região do espectro.
- Exibição de ppm do ponto selecionado.
- Lista de sinais digitada/importada.
- Estado interno de hipóteses.
- Verificação da resposta final com RDKit.

## 7. Funcionalidades futuras

- Leitura de dados brutos de RMN além de imagens.
- Extração automática de picos.
- Integrais.
- Multiplicidades.
- Medição de J.
- 13C.
- DEPT.
- COSY.
- HSQC.
- HMBC.
- Comparação entre espectros.
- Biblioteca de exercícios.
- Modo professor.
- Métricas pedagógicas.
- Avaliação de desempenho do tutor com estudantes.

## 8. Não-objetivos da primeira versão

- Não treinar modelo próprio.
- Não criar sistema autônomo de descoberta de moléculas sem interação do usuário.
- Não depender de consulta automática a uma base externa para descobrir a resposta.
- Não afirmar precisão científica baseada apenas em análise visual do LLM.

## 9. Requisito pedagógico central

O tutor deve privilegiar a sequência:

observar → descrever → interpretar → formular hipótese → confrontar com os dados → revisar → concluir.

## 10. Requisito de confiabilidade

Sempre que um valor exato puder ser obtido por software, o sistema deve preferir o valor calculado/extraído em vez de uma estimativa visual do modelo.

Exemplo:

- permitido: Claude interpreta que uma região parece aromática;
- preferível: engine determinístico informa a lista exata de posições de pico disponíveis para o raciocínio.

## 11. Métrica científica futura

Uma possibilidade de avaliação do projeto é comparar estudantes resolvendo exercícios:

- sem tutor;
- com tutor baseado em Claude.

Possíveis métricas:

- tempo de resolução;
- quantidade de erros;
- quantidade de dicas solicitadas;
- qualidade da justificativa;
- taxa de estruturas finais compatíveis com os dados.

Essas métricas são uma proposta de pesquisa futura, não um requisito do MVP.
