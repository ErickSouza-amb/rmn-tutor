from app.nmr_engine.models import Peak
from app.nmr_engine.queries import delta_between, find_peak, integrate_region, peaks_in_region

PEAKS = [
    Peak(id="P1", ppm=4.12, integral=2, multiplicity="q", j_hz=[7.1]),
    Peak(id="P2", ppm=2.05, integral=3, multiplicity="s"),
    Peak(id="P3", ppm=1.26, integral=3, multiplicity="t", j_hz=[7.1]),
]


def test_peaks_in_region_any_order_inclusive():
    assert [p.id for p in peaks_in_region(PEAKS, 4.12, 2.0)] == ["P1", "P2"]
    assert peaks_in_region(PEAKS, 6, 8) == []


def test_find_peak_by_id_and_ppm():
    assert find_peak(PEAKS, peak_id="P3").ppm == 1.26
    assert find_peak(PEAKS, ppm=2.03).id == "P2"
    assert find_peak(PEAKS, ppm=3.0) is None
    assert find_peak(PEAKS, peak_id="P9") is None


def test_integrate_region_normalized_by_formula():
    r = integrate_region(PEAKS, 0, 5, total_h=8)
    assert r["sum"] == 8.0
    assert r["scale_h_per_unit"] == 1.0
    assert r["normalized_h"] == 8.0
    r2 = integrate_region(PEAKS, 3.5, 4.5, total_h=16)
    assert r2["peak_ids"] == ["P1"] and r2["normalized_h"] == 4.0


def test_integrate_region_missing_integrals():
    peaks = PEAKS + [Peak(id="P4", ppm=7.0)]
    r = integrate_region(peaks, 6, 8, total_h=8)
    assert r["sum"] is None
    assert r["missing_integrals"] == ["P4"]
    r_all = integrate_region(peaks, 0, 5, total_h=8)
    assert r_all["sum"] == 8.0
    assert r_all["normalized_h"] is None  # P4 lacks integral → no global scale


def test_delta_between():
    assert delta_between(PEAKS[0], PEAKS[2], 400) == {"delta_ppm": 2.86, "delta_hz": 1144.0}
    assert delta_between(PEAKS[0], PEAKS[2], None)["delta_hz"] is None
