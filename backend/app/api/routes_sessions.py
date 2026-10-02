from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Identity, get_db, get_identity, load_session
from app.api.schemas import (
    CreateSessionIn,
    SessionOut,
    SessionSummary,
    SpectrumOut,
    StructureCheckIn,
    UpdateSessionIn,
    session_out,
)
from app.chem.compare import compare_structure_with_data, same_structure
from app.chem.rdkit_tools import SmilesError
from app.config import get_settings
from app.errors import ApiError
from app.exercises.catalog import exercise_image_path, get_exercise
from app.nmr_engine.models import Peak, PeakList, renumber
from app.nmr_engine.simulate import simulate_spectrum
from app.nmr_tools.state_ops import ChemState, ProposedStructure
from app.store import repo
from app.store.blob import get_blob_store
from app.store.images import ImageError, normalize_image
from app.store.models import SessionRow
from app.store.repo import as_aware
from app.tutor.context import has_image_marker

router = APIRouter()


def _peaks_json(peaks: list[Peak]) -> list[dict]:
    return [p.model_dump(mode="json") for p in peaks]


@router.post("/sessions", status_code=201)
async def create_session(
    body: CreateSessionIn,
    identity: Identity = Depends(get_identity),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if body.exercise_id:
        exercise = get_exercise(body.exercise_id)
        if exercise is None:
            raise ApiError(404, "exercise_not_found", "Exercício não encontrado.")
        peaks = _peaks_json(exercise.peaks)
        metadata = dict(exercise.metadata)
        title = body.title or exercise.title
    else:
        PeakList(peaks=body.peaks)
        peaks = _peaks_json(renumber(body.peaks))
        metadata = body.metadata.model_dump(exclude_none=True)
        title = body.title or "Espectro de ¹H"
    row = await repo.create_session(
        db,
        owner_uid=identity.uid,
        title=title,
        experiment=body.experiment,
        metadata=metadata,
        peaks=peaks,
        exercise_id=body.exercise_id,
        chem_state=ChemState().model_dump(),
    )
    return {"id": str(row.id)}


@router.get("/sessions")
async def list_sessions(
    identity: Identity = Depends(get_identity), db: AsyncSession = Depends(get_db)
) -> list[SessionSummary]:
    rows = await repo.list_sessions(db, identity.uid)
    return [
        SessionSummary(id=r.id, title=r.title, exercise_id=r.exercise_id, updated_at=as_aware(r.updated_at))
        for r in rows
    ]


@router.get("/sessions/{session_id}")
async def get_session(row: SessionRow = Depends(load_session), db: AsyncSession = Depends(get_db)) -> SessionOut:
    return session_out(row, await repo.list_messages(db, row.id))


@router.patch("/sessions/{session_id}")
async def update_session(
    body: UpdateSessionIn, row: SessionRow = Depends(load_session), db: AsyncSession = Depends(get_db)
) -> SessionOut:
    if row.exercise_id and (body.peaks is not None or body.metadata is not None):
        raise ApiError(409, "exercise_read_only", "Picos e metadados de exercícios não podem ser alterados.")
    if body.peaks is not None:
        try:
            PeakList(peaks=body.peaks)
        except ValueError as exc:
            raise ApiError(422, "invalid_peaks", "IDs de pico duplicados.") from exc
        # keep IDs: the tutor's notes and hypotheses cite them (only creation renumbers)
        row.peaks = _peaks_json(sorted(body.peaks, key=lambda p: -p.ppm))
    if body.metadata is not None:
        row.meta = body.metadata.model_dump(exclude_none=True)
    if body.assist_mode is not None:
        row.assist_mode = body.assist_mode
    if body.title is not None:
        row.title = body.title
    row = await repo.save(db, row)
    return session_out(row, await repo.list_messages(db, row.id))


@router.post("/sessions/{session_id}/image")
async def upload_image(
    file: UploadFile = File(...), row: SessionRow = Depends(load_session), db: AsyncSession = Depends(get_db)
) -> dict:
    if row.exercise_id:
        raise ApiError(409, "exercise_read_only", "Sessões de exercício já têm imagem.")
    if any(has_image_marker(m.content) for m in await repo.list_messages(db, row.id)):
        raise ApiError(
            409, "image_locked", "A imagem já foi enviada ao tutor nesta conversa; crie uma nova sessão para trocá-la."
        )
    settings = get_settings()
    data = await file.read(settings.max_upload_bytes + 1)
    try:
        normalized, media_type = normalize_image(data, settings.max_upload_bytes)
    except ImageError as exc:
        raise ApiError(422, "invalid_image", str(exc)) from exc
    store = get_blob_store()
    old_blob = row.image_blob
    ext = "jpg" if media_type == "image/jpeg" else "png"
    try:
        new_blob = await store.put(f"sessions/{row.id}/spectrum.{ext}", normalized, media_type)
    except Exception as exc:
        raise ApiError(502, "storage_unavailable", "Não foi possível salvar a imagem. Tente novamente.") from exc
    row.image_blob, row.image_media_type = new_blob, media_type
    await repo.save(db, row)
    if old_blob and old_blob != new_blob:
        try:
            await store.delete(old_blob)
        except Exception:
            pass  # orphaned blob is harmless; the session already points at the new one
    return {"ok": True, "media_type": media_type}


@router.get("/sessions/{session_id}/image")
async def get_image(row: SessionRow = Depends(load_session)):
    if row.exercise_id:
        return FileResponse(exercise_image_path(row.exercise_id), media_type="image/png")
    if not row.image_blob:
        raise ApiError(404, "image_not_found", "Esta sessão não tem imagem.")
    data = await get_blob_store().get(row.image_blob)
    return Response(
        content=data,
        media_type=row.image_media_type or "image/png",
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.get("/sessions/{session_id}/spectrum")
async def get_spectrum(row: SessionRow = Depends(load_session)) -> SpectrumOut:
    peaks = [Peak.model_validate(p) for p in row.peaks or []]
    sim = simulate_spectrum(peaks, (row.meta or {}).get("frequency_mhz"))
    return SpectrumOut(x=sim.x, y=sim.y, warnings=sim.warnings)


@router.post("/sessions/{session_id}/structure-check")
async def structure_check(
    body: StructureCheckIn, row: SessionRow = Depends(load_session), db: AsyncSession = Depends(get_db)
) -> dict:
    peaks = [Peak.model_validate(p) for p in row.peaks or []]
    try:
        result = compare_structure_with_data(body.smiles, peaks, (row.meta or {}).get("molecular_formula"))
    except SmilesError as exc:
        raise ApiError(422, "invalid_smiles", str(exc)) from exc
    exercise = get_exercise(row.exercise_id) if row.exercise_id else None
    if exercise and row.assist_mode in ("verify", "solution"):
        result["matches_answer"] = same_structure(body.smiles, exercise.answer_smiles)
    check = await repo.add_structure_check(db, row.id, body.smiles, result, commit=False)
    state = ChemState.model_validate(row.chem_state or {})
    state.proposed_structures.append(ProposedStructure(smiles=body.smiles, check_id=str(check.id)))
    row.chem_state = state.model_dump()
    await repo.save(db, row)
    return {**result, "check_id": str(check.id)}
