---
name: nmr-spectroscopy
description: Use when implementing or reviewing anything in RMN Tutor that depends on NMR chemistry — peak models, shift windows, multiplicity/J logic, structure checks, exercises, tutor prompts — or when judging whether a chemistry claim is safe to state as fact.
---

# Espectroscopia de RMN: referência química

Base química para código, exercícios e prompts. Toda janela numérica é **aproximada**. O conteúdo ainda não foi revisado por especialista (`docs/exercises/REVIEW.md`).

## Mapa
| Arquivo | Abra quando |
|---|---|
| `proton-nmr.md` | mexer em `H_CLASS_RANGES`, integrais, OH/NH, solventes ou equivalência. Lista as **issues para revisão** |
| `carbon-nmr.md` | lidar com ¹³C ou DEPT |
| `coupling.md` | lidar com multiplicidade, `j_hz`, n+1, segunda ordem ou o AA'BB' do ex05 |
| `2d-nmr.md` | COSY, HSQC ou HMBC (fora do MVP) |
| `structure-elucidation.md` | fluxo do tutor, exemplo ex02, erros comuns, isômeros que enganam as checagens |

## Afirmações seguras vs. inseguras
| Segura (compatibilidade) | Insegura (veredito) |
|---|---|
| "Um quarteto de 2H em 4,1 ppm é compatível com OCH₂CH₃" | "Portanto o composto é acetato de etila" |
| "C₄H₈O₂ tem IDH 1: um anel ou uma ligação π" | "Há uma C=O" |
| "Integrais 2:3:3 somam os 8 H da fórmula" | "Há exatamente três grupos" |
| "q e t com o mesmo J sugerem CH₂ e CH₃ vizinhos" | "J = 7,1 Hz", lido na imagem |
| "Todas as checagens passaram; ainda há isômeros possíveis" | "A estrutura está correta" |

## Checagens de `backend/app/chem/compare.py`
| Check | Química | pass / fail / inconclusive | NÃO prova | Limites |
|---|---|---|---|---|
| `formula` | fórmula RDKit da estrutura = fórmula informada | mesma composição / difere / sem fórmula ou fórmula ilegível | conectividade | isômeros passam |
| `h_count` | integrais reescaladas para o total de H **da estrutura**, cada uma a ≤ 0,2 de um inteiro ≥ 1 | razões inteiras / alguma fracionária ou < 1 / sem picos ou integral faltando | que as integrais casem com os ambientes | não compara com a fórmula; OH/NH distorcem |
| `environment_count` | nº de classes topológicas de H = nº de sinais | iguais / — (nunca falha) / diferentes | estrutura correta | ignora diastereotopia, rotação lenta e sobreposição |
| `environment_integrals` | contagens ordenadas de H por ambiente = integrais arredondadas | iguais / diferentes / contagens ou integrais incompletas | qual sinal pertence a qual grupo | não pareia por δ |
| `shift_ranges` | cada classe prevista tem ≥ 1 pico em `H_CLASS_RANGES` ± 0,2 | todas cobertas / falta alguma / sem picos | que todo pico foi explicado | não é 1:1; só CDCl₃; formiatos falham falsamente |

Nenhuma checagem avalia multiplicidade ou J. Com os dados do ex02, propanoato de metila e metoxiacetona passam nas cinco (`structure-elucidation.md`).

## Fontes
- IUPAC, Recomendações 2001 e 2008 sobre deslocamento químico: https://mriquestions.com/uploads/3/4/5/7/34572113/iupac_article-9-1-1.pdf, https://bmrb.io/standards/iupac_2008.pdf (acesso em 2026-10).
- Reich, H. J., *Structure Determination Using NMR*: https://organicchemistrydata.org/hansreich/resources/nmr/?page=nmr-description (acesso em 2026-10).
- LibreTexts, Morsch et al., cap. 13: https://chem.libretexts.org/Bookshelves/Organic_Chemistry/Organic_Chemistry_(Morsch_et_al.)/13%3A_Structure_Determination_-_Nuclear_Magnetic_Resonance_Spectroscopy (acesso em 2026-10).
- Código lido: `backend/app/chem/compare.py`, `environments.py`, `formula.py`; `backend/app/exercises/data/ex01–ex05.yaml`.
- Fontes detalhadas no fim de cada arquivo de referência.
