import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from .. import simulation_service, supabase_client, transcription
from ..auth_dependency import get_current_user
from ..models import (
    StartSimulationRequest,
    StartSimulationResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    SimulationDetail,
)
from ..rbac import require_active_user

router = APIRouter(prefix="/simulations", tags=["simulations"])


@router.post("/start", response_model=StartSimulationResponse)
async def start(
    body: StartSimulationRequest,
    user: dict = Depends(get_current_user),
    _active: dict = Depends(require_active_user),
):
    try:
        result = await run_in_threadpool(
            simulation_service.start_simulation, user["sub"], body.application_id
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return result


@router.post("/{simulation_id}/answer", response_model=SubmitAnswerResponse)
async def answer(
    simulation_id: str,
    body: SubmitAnswerRequest,
    user: dict = Depends(get_current_user),
    _active: dict = Depends(require_active_user),
):
    try:
        return await run_in_threadpool(
            simulation_service.submit_answer, simulation_id, user["sub"], body.answer
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/{simulation_id}/answer-audio", response_model=SubmitAnswerResponse)
async def answer_audio(
    simulation_id: str,
    audio: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    _active: dict = Depends(require_active_user),
):
    audio_bytes = await audio.read()
    try:
        transcript = await run_in_threadpool(
            transcription.transcribe, audio_bytes, audio.filename or "answer.webm"
        )
    except Exception as exc:
        supabase_client.log_error("simulations_answer_audio", str(exc))
        raise HTTPException(502, "Transcription failed, please try again") from exc

    if not transcript:
        raise HTTPException(422, "No speech was detected in the recording")

    try:
        result = await run_in_threadpool(
            simulation_service.submit_answer, simulation_id, user["sub"], transcript
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

    result["transcript"] = transcript
    return result


@router.post("/{simulation_id}/feedback")
async def feedback(
    simulation_id: str,
    user: dict = Depends(get_current_user),
    _active: dict = Depends(require_active_user),
):
    try:
        return await run_in_threadpool(
            simulation_service.generate_feedback, simulation_id, user["sub"]
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        supabase_client.log_error("simulations_feedback", str(exc))
        raise HTTPException(502, "AI feedback returned an unreadable result, please retry") from exc


@router.get("/{simulation_id}", response_model=SimulationDetail)
async def get(simulation_id: str, user: dict = Depends(get_current_user)):
    simulation = supabase_client.get_simulation(simulation_id, user["sub"])
    if simulation is None:
        raise HTTPException(404, "Simulation not found")

    feedback_report = None
    if simulation.get("feedback_report"):
        feedback_report = json.loads(simulation["feedback_report"])

    return SimulationDetail(
        id=simulation["id"],
        application_id=simulation["application_id"],
        persona_role_title=simulation["persona_details"]["role_title"],
        chat_history=simulation["chat_history"],
        feedback_report=feedback_report,
    )
