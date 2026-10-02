# RMN de ¹³C e DEPT

O MVP do RMN Tutor checa apenas ¹H. Este arquivo serve de referência para quem for usar `Experiment.C13` ou `Experiment.DEPT` (`backend/app/nmr_engine/models.py`) ou escrever prompts sobre ¹³C. Todas as janelas são **aproximadas**.

## Fundamentos
- A abundância natural do ¹³C é de cerca de 1,1%. Por isso não se observa acoplamento ¹³C–¹³C num espectro de rotina (LibreTexts 13.10).
- A faixa de δ vai de cerca de 0 a 220 ppm em relação ao TMS, contra cerca de 0 a 12 ppm no ¹H. Sobreposição é bem menos comum que no ¹H (LibreTexts 13.10; OpenStax 13.11).
- Referência secundária pelo solvente (Fulmer 2010): CDCl₃ em 77,16 e DMSO-d₆ em 39,52. O CDCl₃ aparece como tripleto 1:1:1 por acoplamento a um ²H (I = 1, 2nI + 1 = 3; Reich, 5-HMR-3).
- C ligado a átomo eletronegativo e C sp² sobem de δ. Carbonilas ficam mais à esquerda (LibreTexts 13.10).

## Janelas aproximadas de δ (ppm)
| Tipo de carbono | UW–Madison (tabela de lab., aproximado) | LibreTexts "Interpreting C-13" (aproximado) |
|---|---|---|
| C=O de aldeído ou cetona | 200–215 | cetona 205–220; aldeído 190–200 |
| C=O de éster, amida ou ácido | 165–180 | ácido ou éster 170–185 |
| Aromático (benzeno substituído) | 120–140 | 125–150 |
| Alqueno | 110–130 | 115–140 |
| Nitrila (C≡N) | 115–125 | — |
| Alquino | 60–80 | — |
| C–O (álcool, éter, éster alquílico) | 55–80 | RCH₂OH 50–65 |
| C–N (amina) | 40–70 | RCH₂NH₂ 37–45 |
| C–Cl / C–Br / C–F | 40–70 / 30–60 / 80–95 | RCH₂Cl 40–45 |
| Alcano | 10–60 | RCH₃ 10–15; R₂CH₂ 16–25; R₃CH 25–35; CH₃CO 20–30 |

A OpenStax (Fig. 13.18) agrupa em faixas mais largas: C=O 160–220; aromático, alqueno e nitrila 110–160. As fontes divergem em alguns pontos, por exemplo no alquino. Em código, trate qualquer janela de ¹³C como heurística.

Exemplo, só para ilustrar (Fulmer 2010, acetato de etila em CDCl₃): 171,36 (C=O), 60,49 (OCH₂), 21,04 (CH₃CO) e 14,19 (CH₃). Os quatro valores caem nas janelas acima.

## Desacoplamento de banda larga (¹H-broadband)
- Irradiar todos os ¹H durante a aquisição remove o acoplamento C–H, e todo sinal vira singleto (LibreTexts 13.10).
- O espectro de rotina é desacoplado **e** tem NOE, porque o desacoplador fica ligado o tempo todo (Columbia, Decatur).
- Consequências: o número de sinais estima o número de ambientes de carbono (ainda pode haver coincidência), e o espectro não informa quantos H há em cada C. Essa informação vem do DEPT ou do HSQC editado.

## Por que as integrais de ¹³C não são confiáveis
1. **NOE desigual.** Com desacoplamento, carbonos que têm H recebem aumento de sinal por NOE, e carbonos sem H recebem pouco ou nenhum (Columbia; Oxford).
2. **Relaxação (T₁).** O T₁ do ¹³C vai de cerca de 0,1 s até dezenas de segundos em carbonos quaternários. Com intervalos curtos entre pulsos, esses sinais saturam e encolhem (Oxford).
3. **Resultado prático.** Carbonos quaternários e C=O aparecem pequenos, e a área não indica quantos carbonos há (OpenStax 13.11; LibreTexts 13.10).
4. **Como obter ¹³C quantitativo.** Usa-se desacoplamento *inverse-gated* (sem NOE) e delay de relaxação de pelo menos 5×T₁ do sinal mais lento, de 2 a 60 s ou mais (Oxford; Columbia).

Regra para o repositório: nunca derivar número de carbonos da área de um ¹³C de rotina e nunca aplicar a ¹³C algo como `h_count`. Se um modelo de pico de ¹³C for criado, `integral` deve ser opcional e marcado como não quantitativo.

## DEPT
DEPT transfere polarização do ¹H para o ¹³C, então só detecta carbonos que têm H ligado.

| Experimento | CH₃ | CH₂ | CH | C quaternário |
|---|---|---|---|---|
| DEPT-90 | ausente | ausente | positivo | ausente |
| DEPT-135 | positivo | **negativo** | positivo | ausente |

Leitura combinada (LibreTexts/OpenStax 13.12; LibreTexts *Intro. Org. Spectroscopy* 6.4):
1. O espectro broadband mostra todos os carbonos.
2. O DEPT-90 mostra só os CH.
3. No DEPT-135, os picos negativos são CH₂. Os positivos que não estão no DEPT-90 são CH₃. Os carbonos que estão no broadband e somem no DEPT-135 são quaternários (incluindo C=O sem H).

Cuidados:
- O DEPT-90 real só **favorece** os CH; podem sobrar picos residuais de CH₂ e CH₃ (Columbia).
- Variantes como a DEPTQ mantêm os quaternários, com fase oposta. Antes de interpretar, confira a variante e a convenção de fase usadas (Columbia).
- O HSQC editado dá a mesma informação de multiplicidade com mais sensibilidade (Columbia; ver `2d-nmr.md`).
- Um sinal ausente no DEPT não prova que o carbono é quaternário se a relação sinal-ruído estiver baixa.

## Afirmações seguras para o tutor
- Seguro: "Um sinal em cerca de 170 ppm é compatível com C=O de éster, ácido ou amida."
- Seguro: "O pico negativo no DEPT-135 indica CH₂."
- Inseguro: "O pico maior tem dois carbonos." Em ¹³C, a área não conta carbonos.
- Inseguro: "Há 4 carbonos porque há 4 sinais." Pode haver simetria ou coincidência.

## Fontes
- LibreTexts, Morsch et al., 13.10 *Characteristics of ¹³C NMR Spectroscopy*. https://chem.libretexts.org/Bookshelves/Organic_Chemistry/Organic_Chemistry_(Morsch_et_al.)/13:_Structure_Determination_-_Nuclear_Magnetic_Resonance_Spectroscopy/13.10:_Characteristics_of_C_NMR_Spectroscopy (acesso em 2026-10).
- LibreTexts (OpenStax), 13.12 *DEPT ¹³C NMR Spectroscopy*. https://chem.libretexts.org/Bookshelves/Organic_Chemistry/Organic_Chemistry_(OpenStax)/13:_Structure_Determination_-_Nuclear_Magnetic_Resonance_Spectroscopy/13.12:_DEPT_C_NMR_Spectroscopy (acesso em 2026-10).
- LibreTexts, *Introduction to Organic Spectroscopy* 6.4 (DEPT). https://chem.libretexts.org/Bookshelves/Organic_Chemistry/Introduction_to_Organic_Spectroscopy/06:_Carbon-13_NMR_Spectroscopy/6.04:_DEPT_C-13_NMR_Spectroscopy (acesso em 2026-10).
- LibreTexts, *Interpreting C-13 NMR Spectra*. https://chem.libretexts.org/Bookshelves/Physical_and_Theoretical_Chemistry_Textbook_Maps/Supplemental_Modules_(Physical_and_Theoretical_Chemistry)/Spectroscopy/Magnetic_Resonance_Spectroscopies/Nuclear_Magnetic_Resonance/NMR:_Structural_Assignment/Interpreting_C-13_NMR_Spectra (acesso em 2026-10).
- OpenStax, *Organic Chemistry* 13.11. https://openstax.org/books/organic-chemistry/pages/13-11-characteristics-of-13c-nmr-spectroscopy (acesso em 2026-10).
- University of Wisconsin–Madison, *¹³C NMR Chemical Shift Table* (apostila de laboratório). https://www2.chem.wisc.edu/deptfiles/OrgLab/handouts/13-C%20NMR%20Chemical%20Shift%20Table.pdf (acesso em 2026-10).
- Decatur, J. (Columbia University NMR Core), *Carbon, Deuterium and Heteronuclear NMR using Topspin*, v. 7.6. https://nmr.chem.columbia.edu/sites/default/files/content/Carbon%20and%20Hetereonuclear%20NMR.pdf (acesso em 2026-10).
- University of Oxford, Chemistry NMR Facility, *Quantitative NMR Spectroscopy* (2017). https://nmr.chem.ox.ac.uk/files/quantitativenmrpdf (acesso em 2026-10).
- Fulmer, G. R. et al. Organometallics 29 (2010) 2176–2179. https://kgroup.du.edu/resources/nmr_impurities_organometallics.pdf (acesso em 2026-10).
- Reich, H. J., Notes 5-HMR-3. https://organicchemistrydata.org/hansreich/resources/nmr/nmr_data/Notes-05-HMR-v26-part2.pdf (acesso em 2026-10).
- Silverstein et al., *Spectrometric Identification of Organic Compounds*; Claridge, *High-Resolution NMR Techniques in Organic Chemistry*: bibliographic (not consulted online).
