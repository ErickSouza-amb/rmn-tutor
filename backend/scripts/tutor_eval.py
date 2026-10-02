"""Behavioural eval of the tutor against a deployed RMN Tutor (real Claude — costs money).

Usage (from backend/):
  python scripts/tutor_eval.py --base-url https://<deployment>.vercel.app
Protected preview: export VERCEL_AUTOMATION_BYPASS_SECRET=<secret> first.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.exercises.catalog import get_exercise  # noqa: E402

SCENARIOS = [
    {"name": "pede a resposta direto", "exercise": "ex02", "mode": "tutor", "turns": ["Oi! Qual é a molécula? Me diz logo."]},
    {
        "name": "aluno descreve sinais",
        "exercise": "ex03",
        "mode": "tutor",
        "turns": ["Vejo três sinais; o de 2,44 ppm é um quarteto.", "Acho que tem um grupo etila."],
    },
    {"name": "pede dica", "exercise": "ex05", "mode": "hint", "turns": ["Me dá uma dica?"]},
]
J_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*Hz")
PEAK_RE = re.compile(r"\bP\d{1,2}\b")


def check_no_answer(text: str, exercise) -> str | None:
    low = text.lower()
    if exercise.answer_name.lower() in low or exercise.answer_smiles.lower() in low:
        return "revelou a resposta"
    return None


def check_cites_peak(texts: list[str]) -> str | None:
    return None if any(PEAK_RE.search(t) for t in texts) else "não citou picos pelo ID"


def check_no_invented_j(texts: list[str], exercise) -> str | None:
    allowed = {j for p in exercise.peaks for j in (p.j_hz or [])}
    bad = set()
    for t in texts:
        for m in J_RE.finditer(t):
            value = float(m.group(1).replace(",", "."))
            if value <= 30 and not any(abs(value - a) <= 0.05 for a in allowed):
                bad.add(value)
    return f"J não presente na tabela: {sorted(bad)}" if bad else None


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for frame in text.replace("\r\n", "\n").strip().split("\n\n"):
        name, data = None, None
        for line in frame.splitlines():
            if line.startswith("event:"):
                name = line[6:].strip()
            elif line.startswith("data:"):
                data = json.loads(line[5:].strip())
        if name:
            events.append((name, data))
    return events


def run_scenario(client: httpx.Client, scenario: dict) -> dict:
    exercise = get_exercise(scenario["exercise"])
    sid = client.post("/api/sessions", json={"exercise_id": exercise.id}).raise_for_status().json()["id"]
    texts: list[str] = []
    tools: list[str] = []
    for i, turn in enumerate(scenario["turns"]):
        body = {"text": turn}
        if i == 0 and scenario.get("mode"):
            body["mode"] = scenario["mode"]
        res = client.post(f"/api/sessions/{sid}/messages", json=body, timeout=240)
        res.raise_for_status()
        events = parse_sse(res.text)
        tools += [d["name"] for n, d in events if n == "tool_call"]
        done = [d for n, d in events if n == "done"]
        errors = [d for n, d in events if n == "error"]
        if errors or not done:
            return {"name": scenario["name"], "session": sid, "failures": [f"turno {i + 1}: {errors or 'sem done'}"], "tools": tools, "replies": texts}
        texts.append(done[-1]["text"])
    failures = [
        f
        for f in (check_no_answer(texts[0], exercise), check_cites_peak(texts), check_no_invented_j(texts, exercise))
        if f
    ]
    return {"name": scenario["name"], "session": sid, "failures": failures, "tools": tools, "replies": texts}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args(argv)
    headers = {}
    if secret := os.environ.get("VERCEL_AUTOMATION_BYPASS_SECRET"):
        headers["x-vercel-protection-bypass"] = secret
    with httpx.Client(base_url=args.base_url.rstrip("/"), headers=headers, follow_redirects=True, timeout=60) as client:
        results = [run_scenario(client, s) for s in SCENARIOS]
    for r in results:
        status = "OK " if not r["failures"] else "FAIL"
        print(f"[{status}] {r['name']}  (sessão {r['session']}; tools: {', '.join(r['tools']) or '—'})")
        for f in r["failures"]:
            print(f"       - {f}")
        for reply in r["replies"]:
            print("       > " + reply.replace("\n", " ")[:400])
    return 1 if any(r["failures"] for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
