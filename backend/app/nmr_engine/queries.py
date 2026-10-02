from app.nmr_engine.models import Peak


def peaks_in_region(peaks: list[Peak], ppm_start: float, ppm_end: float) -> list[Peak]:
    lo, hi = sorted((ppm_start, ppm_end))
    return [p for p in peaks if lo <= p.ppm <= hi]


def find_peak(
    peaks: list[Peak],
    *,
    peak_id: str | None = None,
    ppm: float | None = None,
    tolerance_ppm: float = 0.05,
) -> Peak | None:
    if peak_id is not None:
        return next((p for p in peaks if p.id == peak_id), None)
    if ppm is None:
        return None
    candidates = [p for p in peaks if abs(p.ppm - ppm) <= tolerance_ppm]
    return min(candidates, key=lambda p: abs(p.ppm - ppm), default=None)


def integrate_region(
    peaks: list[Peak], ppm_start: float, ppm_end: float, total_h: int | None
) -> dict:
    region = peaks_in_region(peaks, ppm_start, ppm_end)
    missing = [p.id for p in region if p.integral is None]
    region_sum = None if missing or not region else round(sum(p.integral for p in region), 4)
    scale = None
    normalized = None
    all_have = bool(peaks) and all(p.integral is not None for p in peaks)
    if total_h and all_have and region_sum is not None:
        scale = round(total_h / sum(p.integral for p in peaks), 6)
        normalized = round(region_sum * scale, 3)
    return {
        "peak_ids": [p.id for p in region],
        "sum": region_sum,
        "missing_integrals": missing,
        "normalized_h": normalized,
        "scale_h_per_unit": scale,
    }


def delta_between(a: Peak, b: Peak, frequency_mhz: float | None) -> dict:
    delta_ppm = round(abs(a.ppm - b.ppm), 4)
    delta_hz = round(delta_ppm * frequency_mhz, 2) if frequency_mhz else None
    return {"delta_ppm": delta_ppm, "delta_hz": delta_hz}
