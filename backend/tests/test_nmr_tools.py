import json

from app.nmr_engine.models import Peak
from app.nmr_tools.registry import TOOL_NAMES, ToolContext, execute_tool, tool_definitions
from app.nmr_tools.state_ops import ChemState

PEAKS = [
    Peak(id="P1", ppm=4.12, integral=2, multiplicity="q", j_hz=[7.1], source="exercise"),
    Peak(id="P2", ppm=2.05, integral=3, multiplicity="s", source="exercise"),
    Peak(id="P3", ppm=1.26, integral=3, multiplicity="t", j_hz=[7.1], source="exercise"),
]
META = {"frequency_mhz": 400, "solvent": "CDCl3", "molecular_formula": "C4H8O2"}


def ctx(**kw):
    base = dict(peaks=PEAKS, metadata=META, chem_state=ChemState(), assist_mode="tutor", has_image=True)
    base.update(kw)
    return ToolContext(**base)


def _contains_key(obj, key):
    if isinstance(obj, dict):
        return key in obj or any(_contains_key(v, key) for v in obj.values())
    if isinstance(obj, list):
        return any(_contains_key(v, key) for v in obj)
    return False


def test_definitions_are_fixed_and_clean():
    defs = tool_definitions()
    assert [d["name"] for d in defs] == TOOL_NAMES
    assert len(TOOL_NAMES) == 13
    for d in defs:
        assert d["input_schema"]["type"] == "object"
        assert d["description"]
        assert not _contains_key(d["input_schema"], "title")
    assert json.dumps(defs, sort_keys=True) == json.dumps(tool_definitions(), sort_keys=True)


def test_envelope_shape():
    r = execute_tool("get_peak_list", {}, ctx()).result
    assert set(r) >= {"ok", "tool", "version", "data", "warnings", "limitations"}
    assert r["ok"] and r["version"] == "1" and len(r["data"]["peaks"]) == 3


def test_metadata_tool():
    r = execute_tool("get_spectrum_metadata", {}, ctx()).result
    assert r["data"]["degrees_of_unsaturation"] == 1
    assert r["data"]["image_available"] is True
    r2 = execute_tool("get_spectrum_metadata", {}, ctx(metadata={})).result
    assert "molecular_formula" in r2["warnings"][0]


def test_image_only_session_numeric_tools_not_available():
    c = ctx(peaks=[])
    for name, args in [
        ("get_peak_list", {}),
        ("get_peaks_in_region", {"ppm_start": 0, "ppm_end": 10}),
        ("get_peak", {"ppm": 2.0}),
        ("get_integration", {"ppm_start": 0, "ppm_end": 10}),
    ]:
        r = execute_tool(name, args, c).result
        assert r["ok"] and r["data"]["status"] == "not_available", name


def test_region_and_peak():
    r = execute_tool("get_peaks_in_region", {"ppm_start": 6, "ppm_end": 8}, ctx()).result
    assert r["data"]["peaks"] == [] and r["warnings"]
    r = execute_tool("get_peak", {"ppm": 2.07}, ctx()).result
    assert r["data"]["peak"]["id"] == "P2"
    r = execute_tool("get_peak", {"peak_id": "P1", "ppm": 4.1}, ctx()).result
    assert r["ok"] is False and r["error"]["code"] == "invalid_input"


def test_integration_normalized():
    r = execute_tool("get_integration", {"ppm_start": 3.5, "ppm_end": 4.5}, ctx()).result
    assert r["data"]["normalized_h"] == 2.0 and r["limitations"]
    no_int = [Peak(id="P1", ppm=4.0)]
    r2 = execute_tool("get_integration", {"ppm_start": 3, "ppm_end": 5}, ctx(peaks=no_int)).result
    assert r2["data"]["status"] == "not_available"


def test_delta_and_j():
    r = execute_tool("calculate_delta", {"peak_a": "P1", "peak_b": "P3"}, ctx()).result
    assert r["data"]["delta_ppm"] == 2.86 and r["data"]["delta_hz"] == 1144.0
    r = execute_tool("calculate_j", {"peak_id": "P1"}, ctx()).result
    assert r["data"]["j_hz"] == [7.1]
    r = execute_tool("calculate_j", {"peak_id": "P2"}, ctx()).result
    assert r["data"]["status"] == "not_available" and r["limitations"]
    r = execute_tool("calculate_delta", {"peak_a": "P1", "peak_b": "P9"}, ctx()).result
    assert r["ok"] is False and r["error"]["code"] == "unknown_peak"


def test_chem_tools():
    assert execute_tool("validate_smiles", {"smiles": "C1CC"}, ctx()).result["data"]["valid"] is False
    assert execute_tool("molecular_formula", {"smiles": "CCOC(C)=O"}, ctx()).result["data"]["formula"] == "C4H8O2"
    assert execute_tool("degrees_of_unsaturation", {}, ctx()).result["data"]["degrees_of_unsaturation"] == 1
    out = execute_tool("compare_structure_with_data", {"smiles": "CCOC(C)=O"}, ctx())
    assert out.result["ok"] and out.structure_check["formula"] == "C4H8O2"
    bad = execute_tool("molecular_formula", {"smiles": "C1CC"}, ctx()).result
    assert bad["ok"] is False and bad["error"]["code"] == "invalid_smiles"


def test_update_session_state():
    out = execute_tool(
        "update_session_state",
        {"ops": [{"op": "add_hypothesis", "text": "etila em éster", "by": "student", "evidence": ["P1"]}]},
        ctx(),
    )
    assert out.result["ok"] and out.new_state.hypotheses[0].id == "H1"
    bad = execute_tool("update_session_state", {"ops": [{"op": "add_signal_note", "peak_id": "P9", "interpretation": "x"}]}, ctx())
    assert bad.result["ok"] is False and bad.new_state is None


def test_check_against_answer_guarded():
    answer = "CCOC(C)=O"
    r = execute_tool("check_against_answer", {"smiles": answer}, ctx(answer_smiles=answer)).result
    assert r["error"]["code"] == "mode_not_allowed"
    r = execute_tool("check_against_answer", {"smiles": "CCC(=O)OC"}, ctx(answer_smiles=answer, assist_mode="verify")).result
    assert r["data"] == {"same_structure": False}
    r = execute_tool("check_against_answer", {"smiles": "CCOC(C)=O"}, ctx(answer_smiles=answer, assist_mode="solution")).result
    assert r["data"] == {"same_structure": True}
    r = execute_tool("check_against_answer", {"smiles": answer}, ctx(assist_mode="verify")).result
    assert r["error"]["code"] == "not_available_for_session"


def test_unknown_tool_and_bad_input():
    assert execute_tool("rm_rf", {}, ctx()).result["error"]["code"] == "unknown_tool"
    assert execute_tool("get_peaks_in_region", {"ppm_start": "x"}, ctx()).result["error"]["code"] == "invalid_input"
    assert execute_tool("get_peaks_in_region", "not a dict", ctx()).result["error"]["code"] == "invalid_input"
