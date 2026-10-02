import re
from dataclasses import dataclass, field

from app.nmr_engine.models import MAX_PEAKS, PPM_MAX, PPM_MIN, Peak, renumber

_MULT_ALIASES = {
    "s": "s", "singlet": "s", "singleto": "s",
    "d": "d", "doublet": "d", "dubleto": "d", "dupleto": "d",
    "t": "t", "triplet": "t", "tripleto": "t",
    "q": "q", "quartet": "q", "quarteto": "q",
    "quint": "quint", "quintet": "quint", "quinteto": "quint", "p": "quint",
    "sext": "sext", "sextet": "sext", "sexteto": "sext",
    "sept": "sept", "septet": "sept", "septeto": "sept", "hept": "sept", "hepteto": "sept",
    "m": "m", "multiplet": "m", "multipleto": "m",
    "dd": "dd", "dt": "dt", "td": "td", "ddd": "ddd",
    "br_s": "br_s", "brs": "br_s", "bs": "br_s", "sl": "br_s",
}
_J_MARKERS = {"j", "j=", "j:", "=", "hz"}
_NUM = r"-?\d+(?:[.,]\d+)?"
_LIT_ITER = re.compile(
    rf"(?P<a>{_NUM})(?:\s*[-–—]\s*(?P<b>{_NUM}))?\s*(?:ppm)?\s*\((?P<inner>[^)]*)\)", re.I
)
_INTEGRAL_RE = re.compile(rf"^(?P<n>{_NUM})\s*H$", re.I)
_J_RE = re.compile(rf"^J\s*[=:]?\s*(?P<n>{_NUM})\s*(?:Hz)?$", re.I)
_BARE_J_RE = re.compile(rf"^(?P<n>{_NUM})\s*(?:Hz)?$", re.I)
_HEADER_RE = re.compile(r"ppm|δ|delta|desloc|mult|integr", re.I)


@dataclass
class ParseError:
    line: int
    message: str


@dataclass
class ParseResult:
    peaks: list[Peak] = field(default_factory=list)
    errors: list[ParseError] = field(default_factory=list)


def _num(s: str) -> float:
    return float(s.replace(",", "."))


def _try_num(s: str) -> float | None:
    return _num(s) if re.fullmatch(_NUM, s) else None


def _normalize_tokens(text: str) -> str:
    text = re.sub(r"\bbr\.?\s+s\b", "br_s", text, flags=re.I)
    return re.sub(r"\bs\s+(?:largo|br)\b", "br_s", text, flags=re.I)


def _parse_literature(m: re.Match) -> dict:
    a = _num(m["a"])
    note = None
    if m["b"] is not None:
        b = _num(m["b"])
        ppm = round((a + b) / 2, 3)
        note = f"faixa {min(a, b):g}–{max(a, b):g} ppm"
    else:
        ppm = a
    integral = None
    mult = None
    js: list[float] = []
    in_j = False
    for tok in re.split(r",\s+|;\s*", m["inner"].strip()):
        tok = tok.strip().rstrip(".")
        if not tok:
            continue
        key = tok.lower()
        if key in _MULT_ALIASES and mult is None:
            mult, in_j = _MULT_ALIASES[key], False
        elif im := _INTEGRAL_RE.match(tok):
            integral, in_j = _num(im["n"]), False
        elif jm := _J_RE.match(tok):
            js.append(_num(jm["n"]))
            in_j = True
        elif in_j and (bm := _BARE_J_RE.match(tok)):
            js.append(_num(bm["n"]))
        else:
            raise ValueError(f"termo não reconhecido: '{tok}'")
    return {"ppm": ppm, "integral": integral, "multiplicity": mult, "j_hz": js or None, "note": note}


def _split_fields(line: str) -> list[str]:
    if ";" in line or "\t" in line:
        fields = [f.strip() for f in re.split(r"[;\t]", line)]
        return [f.replace(",", ".") if re.fullmatch(r"-?\d+,\d+", f) else f for f in fields]
    if re.search(r"\d\.\d", line):
        return [f for f in re.split(r"[,\s]+", line.strip()) if f]
    line = re.sub(r"(?<=\d),(?=\d)", ".", line)
    return [f for f in re.split(r"[,\s]+", line.strip()) if f]


def _parse_fields(fields: list[str]) -> dict:
    fields = [f for f in fields if f not in ("", "-", "—")]
    if not fields:
        raise ValueError("linha vazia")
    ppm = _try_num(fields[0])
    if ppm is None:
        raise ValueError(f"δ (ppm) ausente ou inválido: '{fields[0]}'")
    integral = None
    mult = None
    js: list[float] = []
    saw_j = False
    for f in fields[1:]:
        key = f.lower()
        if key in _J_MARKERS:
            saw_j = True
            continue
        if key in _MULT_ALIASES and mult is None:
            mult = _MULT_ALIASES[key]
            continue
        if im := _INTEGRAL_RE.match(f):
            integral = _num(im["n"])
            continue
        if jm := _J_RE.match(f):
            js.append(_num(jm["n"]))
            continue
        v = _try_num(re.sub(r"(?i)hz$", "", f).strip())
        if v is not None:
            if not saw_j and integral is None and mult is None and not js:
                integral = v
            else:
                js.append(v)
            continue
        raise ValueError(f"termo não reconhecido: '{f}'")
    return {"ppm": ppm, "integral": integral, "multiplicity": mult, "j_hz": js or None, "note": None}


def _build_peak(d: dict, source: str, index: int) -> Peak:
    if not (PPM_MIN <= d["ppm"] <= PPM_MAX):
        raise ValueError(f"δ = {d['ppm']:g} fora do intervalo [-2, 16] ppm")
    if d["integral"] is not None and not (0 < d["integral"] <= 1000):
        raise ValueError("a integral deve ser maior que zero")
    if d["j_hz"]:
        if len(d["j_hz"]) > 4:
            raise ValueError("no máximo 4 constantes J por pico")
        if any(not (0 < j <= 30) for j in d["j_hz"]):
            raise ValueError("J deve estar entre 0 e 30 Hz")
    return Peak(
        id=f"P{index}",
        ppm=round(d["ppm"], 4),
        integral=d["integral"],
        multiplicity=d["multiplicity"],
        j_hz=d["j_hz"],
        source=source,
        note=d["note"],
    )


def parse_peak_text(text: str, source: str = "user") -> ParseResult:
    result = ParseResult()
    raw: list[Peak] = []
    for line_no, original in enumerate(text.splitlines(), start=1):
        line = _normalize_tokens(original.strip())
        if not line or line.startswith("#"):
            continue
        try:
            matches = list(_LIT_ITER.finditer(line))
            if matches:
                items = [_parse_literature(m) for m in matches]
            elif re.match(r"^[^\d\-]", line) and _HEADER_RE.search(line):
                continue
            else:
                items = [_parse_fields(_split_fields(line))]
            built = [_build_peak(d, source, len(raw) + i + 1) for i, d in enumerate(items)]
            raw.extend(built)
        except ValueError as exc:
            result.errors.append(ParseError(line_no, str(exc)))
    if len(raw) > MAX_PEAKS:
        result.errors.append(
            ParseError(0, f"limite de {MAX_PEAKS} picos excedido; apenas os {MAX_PEAKS} primeiros foram mantidos")
        )
        raw = raw[:MAX_PEAKS]
    result.peaks = renumber(raw)
    return result
