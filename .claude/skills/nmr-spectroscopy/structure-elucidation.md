# Elucidação estrutural com ¹H: fluxo do tutor, exemplo e limites

Este arquivo é a referência química do fluxo pedagógico. O comportamento do tutor está na skill `nmr-tutor`. Toda janela numérica aqui é **aproximada**.

## Fluxo de trabalho
fórmula → IDH → contagem de sinais → integrais → multiplicidades → fragmentos → montagem → checagem

1. **Fórmula.** Vem de `metadata.molecular_formula`. Se faltar, diga isso. Nunca invente a fórmula.
2. **IDH** (grau de insaturação) = (2C + 2 + N − X − H) / 2. O e S não entram na conta. Cada unidade é um anel ou uma ligação π, e uma ligação tripla conta 2 (LibreTexts 7.3). No código, é `degrees_of_unsaturation` em `app/chem/formula.py`, que conta P junto com N.
3. **Contagem de sinais.** Dá um **mínimo** de ambientes de H, porque sinais se sobrepõem, e o número real pode ser maior. H diastereotópicos ou rotação lenta podem gerar mais sinais do que a topologia prevê.
4. **Integrais.** Normalize pela fórmula: escala = H da fórmula / soma das integrais (`proton-nmr.md`). As razões são relativas, e OH/NH podem distorcer a soma.
5. **Multiplicidades.** Pela regra n+1, quando há primeira ordem, a multiplicidade indica o número de H **vizinhos**, não o número de H do grupo. J iguais emparelham sinais (`coupling.md`).
6. **Fragmentos.** Combine δ (janela aproximada), integral e multiplicidade em peças como CH₃CH₂–X, CH₃–C(=O) ou Ar–H. Cada peça é hipótese.
7. **Montagem.** Junte as peças respeitando a fórmula, o IDH e os átomos que sobraram. Liste **todas** as montagens possíveis, não só a primeira.
8. **Checagem.** Confronte cada candidato com **todos** os dados, inclusive os que `compare.py` não verifica (multiplicidade, J e atribuição de cada sinal a um grupo). Depois rode `compare_structure_with_data` e leia cada check com seus limites (tabela em `SKILL.md`).

## Exemplo trabalhado: ex02 (dados de `backend/app/exercises/data/ex02.yaml`, não revisados)
Dados: C₄H₈O₂, 400 MHz, CDCl₃. Picos: 4,12 (2H, q, J 7,1), 2,05 (3H, s), 1,26 (3H, t, J 7,1).

| Passo | O que os dados permitem dizer | O que **não** permitem dizer |
|---|---|---|
| IDH | (2·4 + 2 − 8)/2 = 1, ou seja, um anel ou uma ligação π | que há uma C=O |
| Sinais | pelo menos 3 ambientes de H | que há exatamente 3 grupos |
| Integrais | 2 + 3 + 3 = 8 = H da fórmula, razão 2:3:3 | atribuição dos grupos |
| q e t com J igual (7,1 Hz) | compatível com um par CH₂–CH₃ acoplado: o CH₂ vê 3 H e o CH₃ vê 2 H | que estão ligados entre si sem COSY; é a hipótese mais simples |
| s 3H | CH₃ sem H vicinal com acoplamento resolvido | o que está ligado a esse CH₃ |
| δ 4,12 (q) | na janela aproximada de H em C ligado a heteroátomo (2,2–4,8) | que o heteroátomo é O de éster |
| δ 2,05 (s) | na janela aproximada de CH₃ α-carbonila/alílico (1,6–2,9) | que existe carbonila |
| δ 1,26 (t) | na janela aproximada de alquila (0,5–2,0) | — |

- **Contabilidade de átomos.** CH₃CH₂ e CH₃ somam C₃H₈. Sobram 1 C e 2 O, e o IDH 1 tem de estar nesse resto. A peça C(=O)O é **uma** forma compatível de usar o resto, não a única.
- **Candidatos e confronto.**
  - CH₃C(=O)OCH₂CH₃: o OCH₂ quarteto fica desblindado e o CH₃ singleto fica na janela α-carbonila. Todos os sinais são explicados, então é compatível.
  - CH₃CH₂C(=O)OCH₃: exigiria um OCH₃ **singleto** perto de 3,7 (LibreTexts 13.3: ROCH₃ em 3,7–3,9) e um CH₂ **quarteto** na janela α-carbonila. Nos dados, o singleto está em 2,05 e o quarteto em 4,12. É menos compatível.
  - CH₃OCH₂C(=O)CH₃: não tem H vicinais acoplados, e esperaria só singletos. É incompatível com o q e o t.
- **Conclusão segura.** "Os dados são compatíveis com acetato de etila; propanoato de metila e metoxiacetona explicam pior a posição e a multiplicidade dos sinais. Sem ¹³C, IV ou 2D, é uma hipótese bem suportada, não uma prova."
- Os valores do ex02 coincidem com os da literatura para acetato de etila em CDCl₃ (Fulmer 2010: 4,12 q, 2,05 s, 1,26 t). Use isso só para revisar o exercício, **nunca** como argumento para o aluno nem como fonte de resposta.

## Erros comuns de estudantes
- Contar os próprios H, ou H equivalentes, no n+1, ou confundir multiplicidade com integral ("quarteto = 4 H").
- Ler integrais como números absolutos sem normalizar pela fórmula, ou exigir inteiros exatos.
- Supor que número de sinais = número de C ou número de grupos, esquecendo simetria e sobreposição.
- Pular o IDH, ou concluir "C=O" só porque IDH = 1.
- Tratar uma janela de δ como valor exato, ou tratar δ fora da janela como impossível.
- Esperar que o OH acople ou fique sempre no mesmo δ. Esquecer o teste com D₂O.
- Atribuir à amostra o residual do solvente (CDCl₃ 7,26) ou a água (1,56).
- Confundir "campo alto" com "δ alto".
- Ler o AA'BB' de um p-dissubstituído como dois dubletos de primeira ordem com J verdadeiro (ex05).
- Medir J na imagem (`coupling.md`).
- Concluir a estrutura porque "todas as checagens passaram".

## Limites de inferência: isômeros que passam nas checagens grosseiras
Resultados de `compare_structure_with_data` com os picos do ex02 e a fórmula C₄H₈O₂, rodados num script descartável fora do repositório (2026-10):

| Candidato (SMILES) | formula | h_count | env_count | env_integrals | shift_ranges |
|---|---|---|---|---|---|
| acetato de etila `CCOC(C)=O` | pass | pass | pass | pass | pass |
| propanoato de metila `CCC(=O)OC` | pass | pass | pass | pass | pass |
| metoxiacetona `COCC(C)=O` | pass | pass | pass | pass | pass |
| formiato de propila `CCCOC=O` | pass | pass | inconclusive | inconclusive | fail |
| formiato de isopropila `CC(C)OC=O` | pass | pass | pass | fail | fail |
| 1,4-dioxano `C1COCCO1` | pass | pass | inconclusive | inconclusive | pass |

Por que três isômeros passam em tudo:
- `environment_integrals` compara multiconjuntos ordenados ([2, 3, 3]) e não pareia sinal com grupo.
- `shift_ranges` só pede algum pico em cada janela. No propanoato de metila, o 4,12 "cobre" o OCH₃, o 2,05 cobre o CH₂ e o 1,26 cobre o CH₃, embora a atribuição seja internamente inconsistente (o 3H singleto teria de ser o OCH₃).
- Nenhum check olha multiplicidade nem J. A metoxiacetona teria só singletos.

Formiato de propila: com os picos do ex02 ele falha corretamente, porque tem 4 ambientes contra 3 sinais. Com dados plausíveis próprios (cerca de 8,05 / 4,10 / 1,70 / 0,96, valores ilustrativos não verificados em fonte), passa em quatro checks e **falha** em `shift_ranges`, porque o H do formiato cai na classe `aldehyde` (9,0–10,5). É um falso negativo (issue 1 em `proton-nmr.md`). O 1,4-dioxano mostra que `shift_ranges` = pass não significa "dados explicados".

O que discriminaria esses candidatos: a atribuição sinal a sinal (δ do OCH₃ contra o do OCH₂, multiplicidades), o DEPT-135 e o ¹³C (CH₂ ligado a O contra CH₃ ligado a O) e o HMBC (qual grupo correlaciona com o C=O). O `check_against_answer` compara com o gabarito por InChIKey e não substitui o raciocínio.

## Fontes
- LibreTexts, Morsch et al., 7.3 *Calculating Degree of Unsaturation*. https://chem.libretexts.org/Bookshelves/Organic_Chemistry/Organic_Chemistry_(Morsch_et_al.)/07:_Alkenes-_Structure_and_Reactivity/7.03:_Calculating_Degree_of_Unsaturation (acesso em 2026-10).
- LibreTexts, Morsch et al., 13.3 a 13.5 (deslocamento, integração, desdobramento). https://chem.libretexts.org/Bookshelves/Organic_Chemistry/Organic_Chemistry_(Morsch_et_al.)/13%3A_Structure_Determination_-_Nuclear_Magnetic_Resonance_Spectroscopy (acesso em 2026-10).
- Reich, H. J. *Structure Determination Using NMR*, Notes 5-HMR (desatualizado segundo o próprio PDF). https://organicchemistrydata.org/hansreich/resources/nmr/nmr_data/Notes-05-HMR-v26-part1.pdf (acesso em 2026-10).
- Fulmer, G. R. et al. Organometallics 29 (2010) 2176–2179. https://kgroup.du.edu/resources/nmr_impurities_organometallics.pdf (acesso em 2026-10).
- Pavia et al., *Introduction to Spectroscopy*; Silverstein et al., *Spectrometric Identification of Organic Compounds*: bibliographic (not consulted online).
