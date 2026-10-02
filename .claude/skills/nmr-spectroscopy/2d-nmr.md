# RMN 2D: COSY, HSQC e HMBC

> **Fora do MVP; referência para fases futuras.** O enum `Experiment` (`backend/app/nmr_engine/models.py`) já tem `COSY`, `HSQC` e `HMBC`, mas nenhuma checagem nem exercício os usa. Os valores de J citados são **aproximados**.

## Visão geral
| Experimento | Correlaciona | Distância típica | Principal uso |
|---|---|---|---|
| COSY | ¹H–¹H | ²J e ³J; às vezes mais | montar as cadeias de H acoplados |
| HSQC (e HSQC editado) | ¹H–¹³C | ¹J (ligação direta) | saber qual H está em qual C; o editado indica CH/CH₃ vs. CH₂ |
| HMBC | ¹H–¹³C | ²J e ³J; às vezes ⁴J | ligar fragmentos através de C quaternários e heteroátomos |

## COSY
- O espectro de ¹H aparece nos dois eixos. A diagonal reproduz o 1D, e os picos fora da diagonal (cross peaks) indicam H acoplados por J. O espectro é simétrico: um pico em (δa, δb) tem par em (δb, δa) (LibreTexts *Intro. Org. Spectroscopy* 7.3; SDSU).
- Mostra principalmente ²J e ³J. Acoplamentos de longo alcance podem ficar fracos ou ausentes. O TOCSY estende a correlação a todo o sistema de spins, e o NOESY correlaciona H próximos no espaço (LibreTexts 7.3).
- Cuidados:
  - Sinais sobrepostos perto da diagonal escondem cross peaks.
  - Um cross peak ausente não prova que não há acoplamento, porque J pequeno ou sinal largo podem enfraquecê-lo.
  - OH e NH em troca rápida em geral não aparecem correlacionados.
- Aplicação a exercícios futuros: o COSY confirma o emparelhamento que, no 1D, se infere pelo J igual (o q e o t do ex02 deveriam ter um cross peak entre si).

## HSQC e HSQC editado
- Correlação de **uma ligação** ¹H–¹³C: cada cross peak mostra um H ligado diretamente a um C (LibreTexts 7.4; SDSU; Facey 2007).
- Carbonos quaternários **não aparecem**. Um C presente no ¹³C sem pico no HSQC não tem H ligado, como o C=O em cerca de 171 ppm no exemplo da LibreTexts 7.4. H em heteroátomo (OH, NH) também não aparece no HSQC ¹H–¹³C.
- No HSQC editado (multiplicidade), CH e CH₃ têm uma fase e CH₂ tem fase oposta. É a mesma informação do DEPT-135, com mais sensibilidade (Facey 2007; SDSU; Columbia). Confira a convenção de cores e fases do arquivo antes de interpretar.
- CH₂ diastereotópicos aparecem como dois H no mesmo δC, um sinal útil para detectar diastereotopia que o ranking topológico de `environments.py` não vê.

## HMBC
- Correlações ¹H–¹³C de longo alcance, normalmente por 2 ou 3 ligações e às vezes 4, sobretudo através de sistemas conjugados (LibreTexts 7.4). O experimento costuma ser otimizado para J_CH de longo alcance em torno de 7–8 Hz, numa faixa útil de cerca de 3–10 Hz (SDSU).
- É o experimento que liga fragmentos através de C quaternários (C=O, C aromático substituído) e heteroátomos.

### Armadilhas do HMBC
1. **²J e ³J não se distinguem.** As magnitudes de ²J_CH e ³J_CH se sobrepõem, então um cross peak não diz quantas ligações separam H e C (Facey 2017).
2. **Correlações ausentes.** Alguns J_CH de longo alcance, inclusive de duas ligações, são quase zero. O ³J_CH depende do ângulo diedro e fica pequeno perto de 90°. Ausência de correlação não prova distância grande (Facey 2017).
3. **⁴J aparece**, especialmente em sistemas conjugados ou aromáticos, e pode induzir montagens erradas (Facey 2017; LibreTexts 7.4).
4. **Resíduos de ¹J.** O filtro de uma ligação nem sempre remove a correlação direta, que aparece como um "dubleto" largo (separação ≈ ¹J_CH) centrado no δH do H ligado. Não confundir com correlação de longo alcance. Este item vem de conhecimento geral e não foi verificado numa fonte aberta nesta pesquisa; o ¹J_CH típico é de cerca de 115–135 Hz (Reich, 5-HMR-1.1).
5. Use o HMBC para **confirmar ou rejeitar** atribuições já propostas, não como primeira fonte de conectividade (SDSU). Experimentos como H2BC ajudam a separar o ²J (Facey 2017).

## Fluxo sugerido para fases futuras
1. Pelo 1D de ¹H e pela fórmula: IDH, número de sinais, integrais e multiplicidades.
2. Pelo HSQC (editado): qual H está em qual C e quais C são CH, CH₂, CH₃ ou quaternários.
3. Pelo COSY: os fragmentos de H contíguos.
4. Pelo HMBC: a ligação entre fragmentos através de quaternários e heteroátomos, mantendo as armadilhas acima em mente.
5. Confrontar a estrutura com **todos** os dados. Uma correlação inexplicada é motivo para revisar a hipótese.

Exemplo conceitual com o ex02 (hipotético, sem dados 2D no repositório): se fosse acetato de etila, seria de esperar HMBC do CH₃ singleto e do OCH₂ para o mesmo C=O. Num propanoato de metila, a correlação esperada seria do OCH₃. Sem o espectro, isso é previsão e não pode ser apresentado como observação.

Sugestões de modelo de dados (não implementadas): representar cross peaks como pares (δ₁, δ₂) com tipo de experimento e, no HSQC editado, a fase. Nenhum valor deve vir da imagem; a regra do CLAUDE.md vale também para 2D.

## Fontes
- LibreTexts, *Introduction to Organic Spectroscopy*, 7.3 *Two Dimensional Homonuclear NMR Spectroscopy*. https://chem.libretexts.org/Bookshelves/Organic_Chemistry/Introduction_to_Organic_Spectroscopy/07:_Two-Dimensional_NMR_Spectroscopy/7.03:_Two_Dimensional_Homonuclear_Spectroscopy (acesso em 2026-10).
- LibreTexts, *Introduction to Organic Spectroscopy*, 7.4 *Two Dimensional Heteronuclear NMR Spectroscopy*. https://chem.libretexts.org/Bookshelves/Organic_Chemistry/Introduction_to_Organic_Spectroscopy/07:_Two-Dimensional_NMR_Spectroscopy/7.04:_Two_Dimensional_Heteronuclear_NMR_Spectroscopy (acesso em 2026-10).
- San Diego State University NMR Facility, *Common 2D (COSY, HSQC, HMBC)*. https://nmr.sdsu.edu/index.php/nmr-seminar/7-common-2d-cosy-hsqc-hmbc/ (acesso em 2026-10).
- Facey, G. (University of Ottawa NMR Facility Blog), *HSQC and Edited HSQC Spectra*, 2007. http://u-of-o-nmr-facility.blogspot.com/2007/11/hsqc-and-edited-hsqc-spectra.html (acesso em 2026-10).
- Facey, G. (University of Ottawa NMR Facility Blog), *HMBC vs. H2BC*, 2017. http://u-of-o-nmr-facility.blogspot.com/2017/04/hmbc-vs-h2bc.html (acesso em 2026-10).
- Decatur, J. (Columbia University NMR Core), *Carbon, Deuterium and Heteronuclear NMR using Topspin* (sobre HSQC editado vs. DEPT). https://nmr.chem.columbia.edu/sites/default/files/content/Carbon%20and%20Hetereonuclear%20NMR.pdf (acesso em 2026-10).
- Claridge, T. D. W., *High-Resolution NMR Techniques in Organic Chemistry*: bibliographic (not consulted online).
