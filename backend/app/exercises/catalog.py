from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from app.nmr_engine.models import Peak, renumber

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = BASE_DIR / "images"


class Exercise(BaseModel):
    id: str
    title: str
    difficulty: int
    experiment: str = "1H"
    metadata: dict
    answer_smiles: str
    answer_name: str
    reviewed: bool = False
    reviewed_by: str | None = None
    sources: list[str] = Field(default_factory=list)
    notes: str | None = None
    peaks: list[Peak]

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "difficulty": self.difficulty,
            "experiment": self.experiment,
            "metadata": self.metadata,
            "reviewed": self.reviewed,
            "notes": self.notes,
        }


def _load_file(path: Path) -> Exercise:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw_peaks = data.pop("peaks")
    peaks = [Peak(id=f"P{i + 1}", source="exercise", **p) for i, p in enumerate(raw_peaks)]
    return Exercise(peaks=renumber(peaks), **data)


@lru_cache
def load_exercises() -> dict[str, Exercise]:
    items = [_load_file(p) for p in sorted(DATA_DIR.glob("*.yaml"))]
    items.sort(key=lambda e: (e.difficulty, e.id))
    return {e.id: e for e in items}


def get_exercise(exercise_id: str) -> Exercise | None:
    return load_exercises().get(exercise_id)


def exercise_image_path(exercise_id: str) -> Path:
    return IMAGES_DIR / f"{exercise_id}.png"
