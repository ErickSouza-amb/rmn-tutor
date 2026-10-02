"""Render didactic PNGs for the exercise catalog (dev-only; needs matplotlib).

Run from backend/:  python scripts/render_exercise_images.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from app.exercises.catalog import IMAGES_DIR, load_exercises  # noqa: E402
from app.nmr_engine.simulate import SPLIT_COUNTS, multiplet_lines, simulate_spectrum  # noqa: E402

INK = "#1f2937"


def _style(ax) -> None:
    ax.set_yticks([])
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)


def render(exercise) -> Path:
    meta = exercise.metadata
    freq = meta.get("frequency_mhz") or 400
    sim = simulate_spectrum(exercise.peaks, freq)
    # zoom only on resolved first-order multiplets (broad "m" lines gain nothing from a zoom)
    zoom = [p for p in exercise.peaks if p.multiplicity and SPLIT_COUNTS.get(str(p.multiplicity))]
    if zoom:
        fig = plt.figure(figsize=(10, 5.8), dpi=150)
        gs = fig.add_gridspec(2, len(zoom), height_ratios=[2.2, 1], hspace=0.45)
        ax = fig.add_subplot(gs[0, :])
    else:
        fig, ax = plt.subplots(figsize=(10, 4), dpi=150)
    ax.plot(sim.x, sim.y, color=INK, linewidth=0.8)
    ax.set_xlim(10.5, -0.3)
    ax.set_ylim(-0.03, 1.18)
    ax.set_xlabel("δ (ppm)")
    _style(ax)
    last_ppm, level = None, 0
    for p in sorted(exercise.peaks, key=lambda q: -q.ppm):
        if p.integral is None:
            continue
        level = 1 - level if last_ppm is not None and abs(last_ppm - p.ppm) < 0.4 else 0
        ax.annotate(f"{p.integral:g}H", (p.ppm, 1.08 - 0.08 * level), ha="center", fontsize=8, color="#374151")
        last_ppm = p.ppm
    ax.set_title(
        f"RMN de ¹H ({freq:g} MHz, {meta.get('solvent', '?')}) — {exercise.title} — dados simulados",
        fontsize=9,
    )
    for i, p in enumerate(zoom):
        lines, _ = multiplet_lines(p.ppm, str(p.multiplicity), p.j_hz, freq)
        span = max(pos for pos, _ in lines) - min(pos for pos, _ in lines)
        half = max(0.04, span / 2 + 0.025)
        zax = fig.add_subplot(gs[1, i])
        xs = [x for x in sim.x if p.ppm - half <= x <= p.ppm + half]
        ys = [y for x, y in zip(sim.x, sim.y) if p.ppm - half <= x <= p.ppm + half]
        zax.plot(xs, ys, color=INK, linewidth=0.8)
        zax.set_xlim(p.ppm + half, p.ppm - half)
        zax.tick_params(labelsize=7)
        zax.set_title(f"ampliação {p.ppm:.2f} ppm", fontsize=8)
        _style(zax)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    out = IMAGES_DIR / f"{exercise.id}.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


if __name__ == "__main__":
    for ex in load_exercises().values():
        print(render(ex))
