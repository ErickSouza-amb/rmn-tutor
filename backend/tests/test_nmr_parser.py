from app.nmr_engine.parser import parse_peak_text


def _tuples(result):
    return [(p.id, p.ppm, p.integral, p.multiplicity, p.j_hz) for p in result.peaks]


def test_csv_with_header_dot_decimal():
    r = parse_peak_text("ppm,integral,mult,J\n1.26,3,t,7.1\n4.12,2,q,7.1\n2.05,3,s")
    assert r.errors == []
    assert _tuples(r) == [
        ("P1", 4.12, 2.0, "q", [7.1]),
        ("P2", 2.05, 3.0, "s", None),
        ("P3", 1.26, 3.0, "t", [7.1]),
    ]


def test_semicolon_with_decimal_comma():
    r = parse_peak_text("4,12;2;q;7,1\n1,26;3;t;7,1")
    assert r.errors == []
    assert _tuples(r)[0] == ("P1", 4.12, 2.0, "q", [7.1])


def test_space_separated_decimal_comma():
    r = parse_peak_text("4,12 2 q 7,1")
    assert _tuples(r) == [("P1", 4.12, 2.0, "q", [7.1])]


def test_integral_with_h_suffix_and_j_marker():
    r = parse_peak_text("4.12 2H q J = 7.1 Hz")
    assert _tuples(r) == [("P1", 4.12, 2.0, "q", [7.1])]


def test_j_marker_without_integral_is_not_integral():
    r = parse_peak_text("4.12 J = 7.1")
    assert _tuples(r) == [("P1", 4.12, None, None, [7.1])]


def test_literature_single_line_ptbr():
    text = "RMN de 1H (400 MHz, CDCl3) δ 4,12 (q, J = 7,1 Hz, 2H), 2,05 (s, 3H), 1,26 (t, J = 7,1 Hz, 3H)."
    r = parse_peak_text(text)
    assert r.errors == []
    assert _tuples(r) == [
        ("P1", 4.12, 2.0, "q", [7.1]),
        ("P2", 2.05, 3.0, "s", None),
        ("P3", 1.26, 3.0, "t", [7.1]),
    ]


def test_literature_range_and_two_j():
    r = parse_peak_text("7,30–7,10 (m, 5H)\n7.94 (dd, J = 8.0, 2.0 Hz, 1H)")
    assert r.errors == []
    by_ppm = {p.ppm: p for p in r.peaks}
    assert by_ppm[7.2].multiplicity == "m"
    assert by_ppm[7.2].note == "faixa 7.1–7.3 ppm"
    assert by_ppm[7.94].j_hz == [8.0, 2.0]


def test_broad_singlet_aliases():
    r = parse_peak_text("2.00 (br s, 1H)\n1.90 1 s largo")
    assert [p.multiplicity for p in r.peaks] == ["br_s", "br_s"]


def test_bad_line_reports_line_number_and_keeps_others():
    r = parse_peak_text("4.12 2 q 7.1\nabc def\n18.0 1 s")
    assert len(r.peaks) == 1
    assert [e.line for e in r.errors] == [2, 3]
    assert "fora do intervalo" in r.errors[1].message


def test_comments_and_blank_lines_ignored():
    r = parse_peak_text("# meus picos\n\n4.12 2 q 7.1\n")
    assert len(r.peaks) == 1 and r.errors == []


def test_limit_of_200_peaks():
    text = "\n".join(f"{1 + i * 0.01:.2f} 1 s" for i in range(201))
    r = parse_peak_text(text)
    assert len(r.peaks) == 200
    assert r.errors[-1].line == 0


def test_source_is_propagated():
    r = parse_peak_text("1.0 3 s", source="exercise")
    assert r.peaks[0].source == "exercise"
