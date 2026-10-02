# nmr-spectroscopy — baseline (RED) and re-test (GREEN)

## Baseline (no skill), 2026-10-02

Questions: (1) checks for ethyl acetate proposal and claims not to state as fact; (2) toluene 3 signals vs 4 environments; (3) ¹H window for H–C–O and confidence; (4) HSQC vs COSY.

Summary of the answer:
- Chemistry content largely correct: DBE, integration, n+1, isomers (methyl propanoate, propyl formate) not ruled out, toluene overlap, O–CH ≈ 3.3–4.5 ppm "moderate confidence", HSQC = one-bond C–H.
- **Gap 1:** sources "cited from memory and not checked" — no URLs, no verification.
- **Gap 2:** no mapping to the repo's deterministic checks (`app/chem/compare.py`) nor to `H_CLASS_RANGES` (repo uses 2.2–4.8 for alpha_heteroatom, wider than the baseline's window) — the agent cannot tell which claims the app already verifies and which remain reasoning.
- **Gap 3:** no repo-specific guidance on which tutor statements are unsafe (compatible-with vs proven) tied to the check statuses pass/fail/inconclusive.
