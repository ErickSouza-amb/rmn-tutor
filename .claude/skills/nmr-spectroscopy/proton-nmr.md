# RMN de ¹H: escala δ, deslocamento, integração e equivalência

Todas as janelas numéricas abaixo são **aproximadas**, didáticas e valem para CDCl₃, salvo indicação em contrário.

## Escala δ e referência
- Definição IUPAC: δ = (ν_amostra − ν_ref) / ν_ref, expressa em ppm. δ positivo significa que o núcleo ressoa em frequência mais alta que a referência (IUPAC 2001; IUPAC 2008).
- Referência primária para ¹H e ¹³C: o ¹H do TMS (Si(CH₃)₄) em solução diluída em CDCl₃ (fração volumétrica < 1%) (IUPAC 2008). Na prática, o eixo costuma ser calibrado pelo sinal residual do solvente, que é uma referência secundária.
- δ não depende do campo, mas a distância em Hz depende: Δν (Hz) = Δδ (ppm) × frequência do espectrômetro (MHz) (Reich, 5-HMR-0/2).
- Terminologia: esquerda = desblindado = "campo baixo" = alta frequência; direita = blindado = "campo alto" = baixa frequência (Reich, 5-HMR-2). No tutor, prefira "desblindado/blindado" ou "δ maior/menor". "Campo alto" confunde o aluno porque corresponde a δ **menor**.

Sinais residuais (Fulmer et al. 2010, Tabelas 1 e 2, conferidos no PDF; aproximados, variam com temperatura e concentração):

| Solvente | ¹H residual | H₂O / HDO (¹H) | ¹³C do solvente |
|---|---|---|---|
| CDCl₃ | 7,26 (CHCl₃) | 1,56 | 77,16 |
| DMSO-d₆ | 2,50 (DMSO-d₅) | 3,33 | 39,52 |

O residual do DMSO-d₆ vem do CHD₂ e aparece como quinteto, porque está acoplado a dois ²H (I = 1), e a regra geral dá 2nI + 1 = 5 linhas (Reich, 5-HMR-3). O aluno não deve atribuir o pico residual nem o da água a sua amostra.

## Blindagem e desblindagem
- A densidade eletrônica em torno do núcleo blinda o H. Grupos eletronegativos retiram densidade e aumentam δ (LibreTexts 13.3; OpenStax 13.4).
- Anisotropia: um H em carbono sp², no plano do sistema π, é desblindado (LibreTexts 13.3).
- Em primeira aproximação, H em C sp³ ou sp fica entre 0 e 5 ppm e H em C sp² entre 5 e 10 ppm, com muitas exceções (Reich, 5-HMR-2.1).
- Para CH₃–X, δ varia de cerca de −2 (MeLi) a cerca de 4 (MeF) (Reich, 5-HMR-2.1).
- Tabelas de incrementos erram tipicamente cerca de 0,5 ppm, e mais quando há muitos substituintes (Reich, 5-HMR-2.3). Uma janela serve para checar compatibilidade, nunca para identificar.

## Janelas aproximadas por ambiente comparadas a `H_CLASS_RANGES`
Código: `backend/app/chem/environments.py`. Em `compare.py`, cada janela é ampliada em ±0,2 ppm (`SHIFT_TOLERANCE`).

| Classe no código | Código (ppm, aproximado) | LibreTexts 13.3 (ppm, aproximado) | OpenStax 13.4 (ppm, aproximado) | Avaliação |
|---|---|---|---|---|
| `alkyl` | 0,5–2,0 | RCH₃ 0,9–1,0; RCH₂R 1,2–1,7; R₃CH 1,5–2,0 | 0,7–1,8 | concorda |
| `allylic_benzylic_alpha_carbonyl` | 1,6–2,9 | alílico 2,0–2,3; ArCH₃ 2,2–2,4; benzílico 2,3–3,0 | alílico 1,6–2,2 | concorda (o limite de 3,0 fica coberto pela tolerância) |
| `alkynyl` | 1,7–3,3 | 1,5–1,8 | "alquino/cetona/haleto" 2,0–4,0 | as fontes divergem (issue 8) |
| `alpha_heteroatom` | 2,2–4,8 | ROCH₃ 3,7–3,9 | álcool/éter 2,5–5,0 | limite superior menor que o da OpenStax (issues 2 e 8) |
| `vinylic` | 4,5–7,0 | 5–9 | 4,5–6,5 | LibreTexts vai até 9 (issue 8) |
| `aromatic` | 6,0–8,8 | 6,0–8,7 | 6,5–8,0 | concorda |
| `aldehyde` | 9,0–10,5 | 9,5–10,0 | 9,7–10,0 | concorda para aldeídos (issue 1) |
| `carboxylic_acid` | 9,5–13,5 | 10–13 | 11,0–12,0 | concorda |
| `exchangeable` | 0,5–6,0 | ROH 1–5; RNH₂ 1–3 | — | é estreita para fenol e amida (issue 5) |
| `other` | −2,0–16,0 | — | — | passa sempre |

Valores de literatura em CDCl₃ usados só como exemplo (Fulmer 2010): acetato de etila 4,12 q / 2,05 s / 1,26 t; etanol 3,72 q / 1,25 t / OH 1,32 (variável); tolueno 7,25 / 7,17 / 2,36; acetona 2,17; DMF 8,02 / 2,96 / 2,88; propileno =CH₂ 4,94 e 5,03; CH₂Cl₂ 5,30; acetonitrila 2,10; HMDSO 0,07.

## Issues para revisão (não alterar código sem revisão química)
Os casos 1, 2, 3, 4, 6, 7 e 9 foram reproduzidos rodando `compare_structure_with_data` num script descartável fora do repositório (2026-10).
1. **Formamidas e formiatos.** O H de H–C(=O)–N/O é classificado como `aldehyde` (9,0–10,5). Em CDCl₃, o CH do DMF aparece em 8,02 (Fulmer), e por isso o DMF falha em `shift_ranges` mesmo com dados reais. Formiatos (por exemplo, formiato de propila) caem no mesmo caso. A região de cerca de 8 ppm para formiatos não foi confirmada numa fonte aberta nesta pesquisa.
2. **Dois heteroátomos no mesmo C.** CH₂Cl₂ (5,30) e CHCl₃ (7,26) ficam fora de `alpha_heteroatom` (2,2–4,8 com ±0,2). Acetais O–CH₂–O e O–CH–O provavelmente também ficam fora (não verificado em fonte).
3. **H α a nitrila e H propargílico.** CH₃CN (2,10) é classificado como `alkyl` (0,5–2,0) e só passa por causa da tolerância de 0,2. O vizinho sp (C≡N, C≡C) não entra na classe alílica.
4. **Si–CH₃.** HMDSO e graxa de silicone aparecem em 0,07, e o TMS em 0 por definição. Os três ficam abaixo de `alkyl` (0,5 − 0,2), e o TMS falha. Si não está em `_HETERO` nem tem classe própria.
5. **`exchangeable` 0,5–6,0.** Pela fonte, OH de fenol fica em 5–7 em CDCl₃ e 9–11 em DMSO, NH de amida perto de 7, e NH de sal de amônio em 4–7 em CDCl₃ e 8–9 em DMSO (Reich, 5-HMR-2.24 a 2.26). Além disso, a janela cobre quase todo o alifático, então quase nunca falha (a acetamida passa porque o CH₃ em 2,0 já satisfaz a janela).
6. **=CH₂ terminal.** `CanonicalRankAtoms(breakTies=False)` junta os dois H do =CH₂ num único ambiente (no propeno, as contagens saem [2, 1, 3]). Esses H são diastereotópicos (cis e trans ao substituinte) e aparecem em 4,94 e 5,03 (Fulmer). Com isso, `environment_count` fica inconclusivo e `environment_integrals` não roda.
7. **Rotação lenta em amidas.** O N(CH₃)₂ do DMF é previsto como um ambiente de 6H, mas aparecem dois sinais (2,96 e 2,88). `LIMITATIONS` cita H diastereotópicos e troca rápida, mas não cita rotação restrita.
8. **Divergência entre fontes** nas janelas de vinílico, de C–O e de alquinil (ver tabela). Decidir com revisor qual fonte rege o código.
9. **`shift_ranges` não pareia sinal com classe.** O check pede apenas "algum pico em cada janela", então um mesmo pico pode satisfazer várias classes e picos sem explicação não são apontados (ver `structure-elucidation.md`).

## Integração
- A área de um sinal é proporcional ao número de H, e as integrais são sempre **relativas** (Reich, 5-HMR-1; LibreTexts 13.4).
- Para normalizar pela fórmula: escala = (H da fórmula) / (soma das integrais). Multiplique cada integral pela escala e arredonde com tolerância. `compare.h_count` faz isso com o total de H **da estrutura proposta** e tolerância de 0,2.
- Mesmo sem delay de relaxação, a exatidão costuma ficar em torno de 10%. O erro é maior quando se comparam tipos diferentes de H, como CH aromático contra CH₃ (Reich, 5-HMR-1.1).
- Satélites de ¹³C somam 1,1% da área (0,55% cada lado), e sinais próximos se sobrepõem (Reich, 5-HMR-1.1). Um "sinal" de 3H ou 5H pode reunir vários ambientes (os aromáticos de ex04).
- OH e NH podem alargar, somar-se à água ou sumir após troca com D₂O. Nesses casos, a soma das integrais pode não fechar com a fórmula.

## Prótons trocáveis (OH, NH, SH)
- O δ depende de concentração, solvente, temperatura e ligação de hidrogênio. O OH de álcool fica perto de 1–2 em CDCl₃ diluído e vai além de 5 no etanol puro (Reich, 5-HMR-2.22).
- Troca intermolecular rápida alarga o sinal e apaga o acoplamento com os vizinhos (Reich, 5-HMR-2.23; LibreTexts 13.5). Em DMSO a troca fica lenta, e o OH pode aparecer acoplado (t, d).
- Teste com D₂O: os sinais de OH e NH somem. Em CDCl₃ o HOD fica na gota de água que flutua acima da região detectada. Em solventes miscíveis, o HOD aparece na região da água (Reich, 5-HMR-2.22).
- No repositório, o caso corresponde à classe `exchangeable`, à multiplicidade `br_s` e à nota "posição variável" do ex01.

## Equivalência e simetria
- Teste de substituição: troque cada H, um de cada vez, por um grupo novo. Se as estruturas saem idênticas, os H são homotópicos. Se saem enantiômeros, são enantiotópicos e têm o mesmo δ em meio aquiral. Se saem diastereômeros, são diastereotópicos e podem ter δ e J diferentes (Reich, 5-HMR-8).
- Um CH₂ numa molécula quiral costuma ser diastereotópico. O CH₂ do dietilacetal também é, mesmo sem centro estereogênico (Reich, 5-HMR-8).
- Equivalência química não implica equivalência magnética; os sistemas AA'BB' estão em `coupling.md`.
- No código, o ranking topológico agrupa H homotópicos, enantiotópicos e diastereotópicos. A limitação está declarada em `LIMITATIONS`.

## Fontes
- IUPAC. Harris, R. K. et al. *NMR Nomenclature: Nuclear Spin Properties and Conventions for Chemical Shifts* (Recomendações 2001), republicado em Ann. Magn. Reson. 1 (2002) 43–64. https://mriquestions.com/uploads/3/4/5/7/34572113/iupac_article-9-1-1.pdf (acesso em 2026-10).
- IUPAC. Harris, R. K. et al. *Further Conventions for NMR Shielding and Chemical Shifts* (Recomendações 2008). Pure Appl. Chem. 80 (2008) 59–84. https://bmrb.io/standards/iupac_2008.pdf (acesso em 2026-10).
- Fulmer, G. R. et al. *NMR Chemical Shifts of Trace Impurities…* Organometallics 29 (2010) 2176–2179. https://kgroup.du.edu/resources/nmr_impurities_organometallics.pdf (acesso em 2026-10).
- Reich, H. J. *Structure Determination Using NMR*, cap. 5 (o próprio PDF avisa que está desatualizado). https://organicchemistrydata.org/hansreich/resources/nmr/nmr_data/Notes-05-HMR-v26-part1.pdf, …-part2.pdf e …-part3.pdf; índice em https://organicchemistrydata.org/hansreich/resources/nmr/?page=nmr-description (acesso em 2026-10).
- LibreTexts, Morsch et al., seções 13.3, 13.4 e 13.5. https://chem.libretexts.org/Bookshelves/Organic_Chemistry/Organic_Chemistry_(Morsch_et_al.)/13%3A_Structure_Determination_-_Nuclear_Magnetic_Resonance_Spectroscopy (acesso em 2026-10).
- OpenStax, *Organic Chemistry*, seção 13.4. https://openstax.org/books/organic-chemistry/pages/13-4-chemical-shifts-in-1h-nmr-spectroscopy (acesso em 2026-10).
- Pavia et al., *Introduction to Spectroscopy*; Silverstein et al., *Spectrometric Identification of Organic Compounds*: bibliographic (not consulted online).
