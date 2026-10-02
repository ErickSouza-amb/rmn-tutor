import numpy as np
import pytest

from app.nmr_engine.models import Peak
from app.nmr_engine.simulate import multiplet_lines, simulate_spectrum


def test_singlet_single_line():
    lines, ok = multiplet_lines(2.0, "s", None, 400)
    assert lines == [(2.0, 1.0)] and ok


def test_quartet_binomial_pattern():
    lines, ok = multiplet_lines(4.0, "q", [8.0], 400)
    assert ok
    positions = [round(p, 4) for p, _ in lines]
    weights = [w for _, w in lines]
    assert positions == [3.97, 3.99, 4.01, 4.03]
    assert weights == pytest.approx([1 / 8, 3 / 8, 3 / 8, 1 / 8])


def test_dd_uses_two_couplings():
    lines, ok = multiplet_lines(7.0, "dd", [8.0, 2.0], 400)
    assert ok and len(lines) == 4
    assert sum(w for _, w in lines) == pytest.approx(1.0)


def test_missing_j_falls_back_to_single_line():
    lines, ok = multiplet_lines(1.0, "t", None, 400)
    assert lines == [(1.0, 1.0)] and not ok
    lines, ok = multiplet_lines(1.0, "dd", [7.0], 400)
    assert len(lines) == 1 and not ok


def _area(x, y, lo, hi):
    x = np.asarray(x)
    y = np.asarray(y)
    mask = (x >= lo) & (x <= hi)
    return np.trapezoid(y[mask], x[mask])


def test_area_proportional_to_integral():
    peaks = [Peak(id="P1", ppm=5.0, integral=3, multiplicity="s"), Peak(id="P2", ppm=2.0, integral=1, multiplicity="s")]
    sim = simulate_spectrum(peaks, 400)
    a1 = _area(sim.x, sim.y, 4.5, 5.5)
    a2 = _area(sim.x, sim.y, 1.5, 2.5)
    assert a1 / a2 == pytest.approx(3.0, rel=0.05)
    assert max(sim.y) == pytest.approx(1.0)
    assert sim.x == sorted(sim.x)
    assert len(sim.x) <= 20000


def test_warnings_for_missing_data():
    peaks = [Peak(id="P1", ppm=1.2, multiplicity="t")]
    sim = simulate_spectrum(peaks, None)
    text = " ".join(sim.warnings)
    assert "400 MHz" in text
    assert "P1" in text and "J" in text
    assert "integral" in text


def test_empty_peaks_gives_flat_baseline():
    sim = simulate_spectrum([], 400)
    assert len(sim.x) > 10 and max(sim.y) == 0.0
