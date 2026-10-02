# Acoplamento spin-spin (J) e multiplicidade

Todo valor de J abaixo é **aproximado**. Os campos correspondentes no código são `Peak.multiplicity` (enum `Multiplicity`: s, d, t, q, quint, sext, sept, m, dd, dt, td, ddd, br_s) e `Peak.j_hz` (no máximo 4 valores), em `backend/app/nmr_engine/models.py`. Nenhuma checagem de `compare.py` usa esses campos.

## O que é J
- J é um acoplamento escalar transmitido pelas ligações e medido em Hz. Não depende do campo e é mútuo (J_AX = J_XA) (Reich, 5-HMR-3.1; LibreTexts 13.5).
- Consequência prática: dois multipletos acoplados entre si têm o mesmo J, e isso é o principal argumento para emparelhar sinais (o q e o t de 7,1 Hz no ex02).
- Em ppm, um multipleto fica mais estreito em campo maior, porque J em Hz é fixo e o mesmo valor ocupa menos ppm (Reich, 5-HMR-0.4).

## Regra n+1 e quando ela vale
- n vizinhos com o **mesmo** J geram n + 1 linhas. A forma geral é 2nI + 1 (Reich, 5-HMR-3.6; LibreTexts 13.5).
- H equivalentes não desdobram uns aos outros. OH e NH em troca rápida em geral não acoplam com os vizinhos (LibreTexts 13.5).
- Vizinhos com J diferentes geram o **produto** dos padrões (d de d, d de t, …), não a soma (Reich, 5-HMR-3.8).
- Validade, que é o critério de primeira ordem (Reich, 5-HMR-3.7):
  - É preciso Δν ≫ J, com Δν em Hz. Com Δν/J menor que cerca de 5 aparecem efeitos de segunda ordem. Até cerca de Δν > 3J ainda dá para analisar como primeira ordem, mas com distorção. A inclinação quase desaparece perto de Δν = 10J.
  - Os parceiros de acoplamento não podem estar fortemente acoplados entre si. Se estiverem, ocorre acoplamento virtual, e o multipleto pode parecer de primeira ordem sem dar os J verdadeiros.
- Multipletos de primeira ordem são centrossimétricos, e toda linha tem uma parceira a J Hz de distância (Reich, 5-HMR-3.9). O inverso não vale: nem todo multipleto simétrico é de primeira ordem.

## Intensidades (triângulo de Pascal)
| n vizinhos equivalentes | Padrão | Intensidades |
|---|---|---|
| 0 | s | 1 |
| 1 | d | 1:1 |
| 2 | t | 1:2:1 |
| 3 | q | 1:3:3:1 |
| 4 | quint | 1:4:6:4:1 |
| 5 | sext | 1:5:10:10:5:1 |
| 6 | sept | 1:6:15:20:15:6:1 |

A razão de intensidade entre a 1ª e a 2ª linha é 1/n (Reich, 5-HMR-3.8). Em septetos e acima, as linhas externas podem sumir no ruído, e um "quinteto" observado pode ser na verdade um septeto.

## Faixas típicas aproximadas (Hz)
| Tipo | Valor aproximado (Hz) | Fonte |
|---|---|---|
| ²J geminal em sp³ (acíclico) | −10 a −13 (módulo); de −15 a −10 | Reich 5-HMR-4.1; ISU |
| ²J geminal em =CH₂ | 0–3 | ISU |
| ³J vicinal em alquila com rotação livre | 6–8, tipicamente cerca de 7 | Reich 5-HMR-3.6 e 5.1; ISU |
| ³J em alqueno, cis | cerca de 10 (6–12; extremos 3–19) | Reich 5-HMR-5.13; ISU |
| ³J em alqueno, trans | cerca de 17 (12–18; extremos 12–24) | Reich 5-HMR-5.13; ISU |
| ³J aromático orto | 7–9 (ISU: 6–10) | Reich 5-HMR-3.3; ISU |
| ⁴J aromático meta | 2–3 (ISU: 1–3) | Reich 5-HMR-3.3; ISU |
| ⁵J aromático para | < 1, em geral não resolvido | Reich 5-HMR-3.3 |
| ³J de aldeído (H–C–CHO) | 2–3 | ISU |
| ⁴J e acima | em geral < 0,5; até cerca de 3 com ligações π no caminho | Reich 5-HMR-3.6 |

Substituintes eletronegativos diminuem o ³J (Reich, 5-HMR-5.1). Num alqueno, ³J trans > ³J cis quase sem exceção (Reich, 5-HMR-5.13). Os J de ex01 a ex03 (7,0 a 7,3 Hz) estão na faixa vicinal alquílica.

## Nomenclatura dd, dt, td, ddd
- **dd**: dois J diferentes, cada um com 1 H. Dá 4 linhas de mesma intensidade, se J₁ ≠ J₂.
- **dt**: um J grande com 1 H e um J pequeno com 2 H equivalentes (dubleto de tripletos).
- **td**: um J grande com 2 H equivalentes e um J pequeno com 1 H (tripleto de dubletos).
- **ddd**: três J diferentes, 8 linhas.
- Convenção usual, não normativa nas fontes consultadas: as letras seguem J em ordem decrescente, e os valores são listados na mesma ordem. Sugestão para o repositório: manter `j_hz` alinhado com as letras de `multiplicity`. Confira o parser antes de depender disso.
- Uma coincidência de J (J₁ ≈ J₂) faz um dd parecer t. "Aparente t" é uma descrição segura.

## Inclinação (*roofing*) e efeitos de segunda ordem
- Quando Δν/J diminui, as linhas internas de dois multipletos acoplados crescem e as externas encolhem. O multipleto "aponta" para o parceiro, o que ajuda a emparelhar sinais (Reich, 5-HMR-9/10).
- Num AB, J se mede diretamente, mas os δ precisam ser calculados (Reich, 5-HMR-7).
- Equivalência química sem equivalência magnética produz AA'BB' ou AA'XX'. Os casos comuns são X–CH₂CH₂–Y e benzenos p-dissubstituídos com substituintes diferentes (Reich, 5-HMR-15).
- Um multipleto simétrico de 4H em geral **não** é de primeira ordem, e o mais provável é AA'BB' (Reich, 5-HMR-3.9).

### Por que o ex05 aparece como dois dubletos
- A 4'-metoxiacetofenona tem anel p-dissubstituído, que forma um sistema AA'XX' / AA'BB'. Em AA'XX', cada metade do espectro tem um "dubleto" com 50% da intensidade e separação N = |J_AX + J_AX'|, mais dois quartetos "ab" menores. Quando J_AA' ≈ J_XX', como costuma ocorrer em p-dissubstituídos, um desses quartetos colapsa (Reich, 5-HMR-14.1).
- Conta para o ex05 a 400 MHz: Δδ = 7,94 − 6,93 = 1,01 ppm, ou cerca de 404 Hz. Com isso Δν/J ≈ 45, o sistema fica perto do limite AA'XX', e o aspecto é de "dois dubletos" com linhas extras pequenas.
- Assim, o `j_hz: [8.9]` do ex05 é a separação aparente N (orto + para), não um ³J puro, e `d` é uma simplificação didática já declarada em `notes`. O tutor deve dizer "aparência de dubleto, típica de anel p-dissubstituído", nunca "cada H tem exatamente um vizinho".

## Como J é medido
- J (Hz) = separação entre linhas adjacentes (ppm) × frequência do espectrômetro (MHz). Isso decorre da definição de δ (Reich, 5-HMR-2.1; LibreTexts 13.5). Exemplo a 400 MHz: 7,1 Hz = 0,0178 ppm.
- O valor só é confiável em multiplete de primeira ordem bem resolvido, analisado por árvore de acoplamento, removendo primeiro o menor J (Reich, 5-HMR-3.14).
- **Não meça J a partir da imagem de baixa resolução.** A 400 MHz, 7 Hz ocupa cerca de 0,018 ppm. Numa imagem de cerca de 10 ppm em cerca de 1000 px, 1 px corresponde a cerca de 0,01 ppm, ou cerca de 4 Hz, que é um erro da ordem do próprio J. Somam-se alargamento de linha, compressão, eixo mal calibrado e frequência às vezes desconhecida. Regra do repositório (CLAUDE.md): J vem de `j_hz` ou das ferramentas determinísticas, e a imagem é só contexto visual. Sem `j_hz`, o tutor diz que o dado não está disponível.

## Fontes
- Reich, H. J. *Structure Determination Using NMR*, Notes 5-HMR-3 a 5 (acoplamento) e 5-HMR-7 a 15 (Pople, segunda ordem, AA'XX'/AA'BB'); o PDF avisa que está desatualizado. https://organicchemistrydata.org/hansreich/resources/nmr/nmr_data/Notes-05-HMR-v26-part2.pdf e https://organicchemistrydata.org/hansreich/resources/nmr/nmr_data/Notes-05-HMR-v26-part3.pdf (acesso em 2026-10).
- Iowa State University, Chemical Instrumentation Facility, *NMR Coupling Constants*. https://www.cif.iastate.edu/nmr/nmr-tutorials/couplingconstants (acesso em 2026-10).
- LibreTexts, Morsch et al., 13.5 *Spin-Spin Splitting in ¹H NMR Spectra*. https://chem.libretexts.org/Bookshelves/Organic_Chemistry/Organic_Chemistry_(Morsch_et_al.)/13%3A_Structure_Determination_-_Nuclear_Magnetic_Resonance_Spectroscopy/13.05%3A_Spin-Spin_Splitting_in_H_NMR__Spectra (acesso em 2026-10).
- Pavia et al., *Introduction to Spectroscopy*; Claridge, *High-Resolution NMR Techniques in Organic Chemistry*: bibliographic (not consulted online).
