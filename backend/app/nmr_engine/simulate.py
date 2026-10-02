from dataclasses import dataclass, field
from math import comb

import numpy as np

from app.nmr_engine.models import Peak

DEFAULT_FREQUENCY_MHZ = 400.0
DEFAULT_FWHM_HZ = 1.2
BROAD_FWHM_HZ = {"m": 8.0, "br_s": 12.0}
SPLIT_COUNTS: dict[str, tuple[int, ...]] = {
    "s": (),
    "d": (1,),
    "t": (2,),
    "q": (3,),
    "quint": (4,),
    "sext": (5,),
    "sept": (6,),
    "dd": (1, 1),
    "dt": (1, 2),
    "td": (2, 1),
    "ddd": (1, 1, 1),
}


@dataclass
class SimResult:
    x: list[float]
    y: list[float]
    warnings: list[str] = field(default_factory=list)


def multiplet_lines(
    center_ppm: float, multiplicity: str | None, j_hz: list[float] | None, frequency_mhz: float
) -> tuple[list[tuple[float, float]], bool]:
    single = [(center_ppm, 1.0)]
    counts = SPLIT_COUNTS.get(str(multiplicity)) if multiplicity else None
    if not counts:
        return single, True
    js = j_hz or []
    if len(js) < len(counts):
        return single, False
    lines = single
    for n, j in zip(counts, js):
        new: list[tuple[float, float]] = []
        for pos, w in lines:
            for k in range(n + 1):
                offset_ppm = (k - n / 2) * j / frequency_mhz
                new.append((pos + offset_ppm, w * comb(n, k) / 2**n))
        lines = new
    return lines, True


def _lorentzian(x: np.ndarray, x0: float, fwhm: float) -> np.ndarray:
    g = fwhm / 2
    return (g / np.pi) / ((x - x0) ** 2 + g**2)


def simulate_spectrum(peaks: list[Peak], frequency_mhz: float | None) -> SimResult:
    warnings: list[str] = []
    freq = frequency_mhz or DEFAULT_FREQUENCY_MHZ
    if not frequency_mhz:
        warnings.append("Frequência não informada; simulação feita com 400 MHz.")
    if not peaks:
        x = np.linspace(0.0, 12.0, 241)
        return SimResult(x=[round(float(v), 5) for v in x], y=[0.0] * len(x), warnings=warnings)

    components: list[tuple[float, float, float]] = []
    missing_integral = False
    for p in peaks:
        area = p.integral if p.integral is not None else 1.0
        missing_integral |= p.integral is None
        mult = str(p.multiplicity) if p.multiplicity else None
        fwhm_ppm = BROAD_FWHM_HZ.get(mult or "", DEFAULT_FWHM_HZ) / freq
        lines, ok = multiplet_lines(p.ppm, mult, p.j_hz, freq)
        if not ok:
            warnings.append(f"{p.id}: multiplicidade '{mult}' sem J suficiente; desenhado como linha única.")
        components.extend((pos, area * w, fwhm_ppm) for pos, w in lines)
    if missing_integral:
        warnings.append("Há picos sem integral; foi usada integral 1 para desenhá-los.")

    positions = [c[0] for c in components]
    lo = min(min(positions) - 0.5, -0.2)
    hi = max(max(positions) + 0.5, 10.0)
    parts = [np.arange(lo, hi, 0.01)]
    for pos, _, fw in components:
        parts.append(np.arange(pos - 25 * fw, pos + 25 * fw, fw / 6))
    x = np.unique(np.round(np.concatenate(parts), 5))
    x = x[(x >= lo) & (x <= hi)]
    y = np.zeros_like(x)
    for pos, area, fw in components:
        y += area * _lorentzian(x, pos, fw)
    y = y / y.max()
    if len(x) > 20000:
        idx = np.linspace(0, len(x) - 1, 20000).astype(int)
        x, y = x[idx], y[idx]
    return SimResult(
        x=[float(v) for v in x],
        y=[round(float(v), 5) for v in y],
        warnings=warnings,
    )
