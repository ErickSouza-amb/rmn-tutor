import rdkit
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.schemas import ParseErrorOut, ParsePeaksIn, ParsePeaksOut
from app.config import get_settings
from app.exercises.catalog import load_exercises
from app.nmr_engine.parser import parse_peak_text

router = APIRouter()


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict:
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {"status": "ok", "version": get_settings().app_version, "rdkit": rdkit.__version__, "db": db_status}


@router.get("/exercises")
async def exercises() -> list[dict]:
    return [ex.public_dict() for ex in load_exercises().values()]


@router.post("/peaks/parse")
async def parse_peaks(body: ParsePeaksIn) -> ParsePeaksOut:
    result = parse_peak_text(body.text)
    return ParsePeaksOut(
        peaks=result.peaks, errors=[ParseErrorOut(line=e.line, message=e.message) for e in result.errors]
    )
