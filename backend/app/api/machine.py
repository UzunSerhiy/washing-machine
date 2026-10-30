from fastapi import APIRouter, HTTPException, status

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from pydantic import BaseModel

from app.db.database import AsyncSessionLocal
from app.models.machine import Machine
from app.schemas.machine import (
    MachineDriveResponse,
    MachineResponse,
    MachineOperationResponse,
    ManualSpeedRequest,
    MaterialModeRequest,
    CalibrationStartRequest,
    CalibrationSessionResponse,
    CalibrationJogRequest,
    CalibrationMarkRequest,
    CalibrationNextRequest,
    AutoSpeedSettingsResponse,
    AutoSpeedRequest,
)
from app.services.drives.service import DriveService
from app.services.machine.service import MachineService
from app.services.machine.operation_service import MachineOperationService
from app.services.machine.calibration.session_service import CalibrationSessionService
from app.models.material_profile import MaterialProfile
from app.services.machine.calibration.repository import CalibrationRepository
from app.services.speed.auto_settings import AutoSpeedSettingsService
from app.services.machine.operation import AutoStage
from app.services.machine.calibration.homing import HomingState
from app.services.machine.sensors.fake_reference import FakeRollerReferenceSensor
from app.services.machine.operation import OperationMode

from app.services.machine.auto.session_service import AutoSessionService
from app.core.config import settings

router = APIRouter(
    prefix="/api/machine",
    tags=["machine"],
)


class FakeReferenceRequest(BaseModel):
    triggered: bool


class FakeReferenceConnectionRequest(BaseModel):
    connected: bool


class CalibrationHomeRequest(BaseModel):
    frequency_hz: float
    position_confirmed: bool


class RollerHomeRequest(BaseModel):
    position_confirmed: bool
    frequency_hz: float = 10.0


def get_drive_service() -> DriveService:
    from app.main import drive_service

    return drive_service


def get_machine_service() -> MachineService:
    from app.main import machine_service

    if machine_service is None:
        raise RuntimeError("Machine service is not initialized")

    return machine_service


def get_machine_operation_service() -> MachineOperationService:
    from app.main import machine_operation_service

    if machine_operation_service is None:
        raise RuntimeError("Machine operation service is not initialized")

    return machine_operation_service


def get_auto_session_service() -> AutoSessionService:
    from app.main import auto_session_service

    if auto_session_service is None:
        raise RuntimeError("AUTO session service is not initialized")

    return auto_session_service


def get_calibration_session_service() -> CalibrationSessionService:
    from app.main import calibration_session_service

    if calibration_session_service is None:
        raise RuntimeError("Calibration session service is not initialized")

    return calibration_session_service


def build_calibration_session_response(
    service: CalibrationSessionService,
) -> CalibrationSessionResponse:
    session = service.get_current()

    return CalibrationSessionResponse(
        active=True,
        material_profile_id=session.material_profile_id,
        position_turns=session.position_turns,
        running=session.player.running,
        paused=session.player.paused,
        direction=session.player.direction,
        frequency_hz=session.player.frequency_hz,
        washing_stop_turns=session.machine_calibration.washing_stop_turns,
        material_start_turns=session.machine_calibration.material_start_turns,
        material_end_turns=session.winding_calibration.material_end_turns,
        water_start_turns=session.machine_calibration.water_start_turns,
        brush_running=session.player.brush_running,
        brush_frequency_hz=session.player.brush_frequency_hz,
        stage=session.stage,
        saved=service.saved,
        auto_mode=service.auto_mode,
        editing=service.editing,
        edit_target=service.edit_target,
        edit_adjusting=service.edit_adjusting,
    )


def stop_auto_before_mode_change():
    auto_service = get_auto_session_service()

    if auto_service.get_status()["status"] == "FAULT":
        raise HTTPException(
            status_code=409,
            detail="AUTO controller is in FAULT state",
        )

    if auto_service.get_status()["status"] != "IDLE":
        try:
            auto_service.stop()
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


def get_roller_homing_service():
    from app.main import roller_homing_service

    if roller_homing_service is None:
        raise HTTPException(
            status_code=503,
            detail="Roller homing service is not initialized",
        )

    return roller_homing_service


async def get_enabled_material_profile(
    material_profile_id: int,
) -> MaterialProfile:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(MaterialProfile).where(
                MaterialProfile.id == material_profile_id,
                MaterialProfile.is_enabled.is_(True),
            )
        )

        profile = result.scalar_one_or_none()

    if profile is None:
        raise HTTPException(status_code=404, detail="Material profile not found")

    return profile


@router.get("", response_model=MachineResponse)
async def get_machine():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Machine).options(selectinload(Machine.drives)).where(Machine.id == 1)
        )

        machine = result.scalar_one_or_none()

    if machine is None:
        raise HTTPException(
            status_code=404,
            detail="Machine not found",
        )

    drive_service = get_drive_service()

    drives = []

    for db_drive in machine.drives:
        if not db_drive.is_enabled:
            continue

        drive = drive_service.get_drive(db_drive.id)

        drives.append(
            MachineDriveResponse(
                id=db_drive.id,
                name=db_drive.name,
                address=db_drive.address,
                type=db_drive.type,
                position=db_drive.position,
                enabled=db_drive.is_enabled,
                status=drive.get_status(),
                frequency_hz=drive.get_frequency(),
                fault=drive.get_fault(),
            )
        )

    return MachineResponse(
        id=machine.id,
        name=machine.name,
        description=machine.description,
        is_active=machine.is_active,
        drives=drives,
    )


@router.get("/operation", response_model=MachineOperationResponse)
def get_machine_operation():
    service = get_machine_operation_service()
    state = service.state

    return MachineOperationResponse(
        mode=state.mode,
        auto_stage=state.auto_stage,
        material_profile_id=state.material_profile_id,
        roller_speed_percent=state.roller_speed_percent,
        brush_speed_percent=state.brush_speed_percent,
        roller_running=state.roller_running,
        brush_running=state.brush_running,
        running=state.running,
        paused=state.paused,
    )


class ModeSelectionRequest(BaseModel):
    mode: OperationMode


@router.post("/mode/select")
def select_mode_without_session(request: ModeSelectionRequest):
    operation = get_machine_operation_service()
    with operation._mode_lock:
        if get_calibration_session_service().active:
            raise HTTPException(status_code=409, detail="Finish CALIBRATION session first")
        if get_auto_session_service().get_status()["status"] != "IDLE":
            raise HTTPException(status_code=409, detail="Finish AUTO session first")
        try:
            operation.select_idle_mode(request.mode)
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"mode": operation.state.mode}


@router.get("/manual/session")
def manual_session_status():
    return {"active": get_machine_operation_service().manual_session_active}


@router.post("/manual/session/start")
def manual_session_start():
    operation = get_machine_operation_service()
    try:
        operation.begin_manual_session()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"active": True}


@router.post("/manual/session/end")
def manual_session_end():
    operation = get_machine_operation_service()
    try:
        operation.end_manual_session()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"active": False}


@router.put(
    "/manual/roller/speed",
    response_model=MachineOperationResponse,
)
def set_manual_roller_speed(request: ManualSpeedRequest):
    service = get_machine_operation_service()

    try:
        service.set_manual_roller_speed(request.speed_percent)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return service.state


@router.put("/manual/brush/speed", response_model=MachineOperationResponse)
def set_manual_brush_speed(request: ManualSpeedRequest):
    service = get_machine_operation_service()

    try:
        service.set_manual_brush_speed(request.speed_percent)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return service.state


@router.post("/start")
def start_machine():
    service = get_machine_service()

    service.start()

    return {
        "status": "started",
    }


@router.post("/stop")
def stop_machine():
    service = get_machine_service()

    service.stop()

    return {
        "status": "stopped",
    }


@router.post(
    "/mode/manual",
    response_model=MachineOperationResponse,
)
def set_manual_mode():
    stop_auto_before_mode_change()
    service = get_machine_operation_service()

    service.set_manual_mode()

    return service.state


@router.post("/mode/auto", response_model=MachineOperationResponse)
async def set_auto_mode(request: MaterialModeRequest):
    await get_enabled_material_profile(request.material_profile_id)

    stop_auto_before_mode_change()
    service = get_machine_operation_service()

    try:
        service.set_auto_mode(request.material_profile_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return service.state


@router.post("/mode/calibration", response_model=MachineOperationResponse)
async def set_calibration_mode(request: MaterialModeRequest):
    await get_enabled_material_profile(request.material_profile_id)

    stop_auto_before_mode_change()
    service = get_machine_operation_service()
    try:
        service.set_calibration_mode(request.material_profile_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return service.state


@router.post(
    "/manual/roller/forward",
    response_model=MachineOperationResponse,
)
def start_manual_roller_forward():
    service = get_machine_operation_service()

    try:
        service.start_manual_roller_forward()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return service.state


@router.post("/manual/roller/reverse", response_model=MachineOperationResponse)
def start_manual_roller_reverse():
    service = get_machine_operation_service()

    try:
        service.start_manual_roller_reverse()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return service.state


@router.post("/manual/roller/stop", response_model=MachineOperationResponse)
def stop_manula_roller():
    service = get_machine_operation_service()

    try:
        service.stop_manual_roller()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return service.state


@router.post("/manual/brush/start", response_model=MachineOperationResponse)
def start_manual_brush():
    service = get_machine_operation_service()

    try:
        service.start_manual_brush()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return service.state


@router.post("/manual/brush/stop", response_model=MachineOperationResponse)
def stop_manual_brush():
    service = get_machine_operation_service()

    try:
        service.stop_manual_brush()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return service.state


@router.get(
    "/calibration",
    response_model=CalibrationSessionResponse,
)
def get_calibration():
    service = get_calibration_session_service()

    if not service.active:
        return CalibrationSessionResponse(active=False)

    service.tick()  # update estimated roller position on each frontend poll
    return build_calibration_session_response(service)


@router.get("/calibration/saved/{material_profile_id}")
async def get_saved_calibration(material_profile_id: int):
    """Read-only saved points for selecting a calibration editing workflow."""
    await get_enabled_material_profile(material_profile_id)
    async with AsyncSessionLocal() as db:
        machine = (await db.execute(select(Machine).where(Machine.is_active.is_(True)))).scalars().first()
        if machine is None:
            raise HTTPException(status_code=404, detail="Active machine not found")
        try:
            data = await CalibrationRepository().load(db, machine.id, material_profile_id)
        except RuntimeError:
            return {"exists": False, "material_profile_id": material_profile_id}
        return {
            "exists": True,
            "material_profile_id": material_profile_id,
            "material_start_turns": data.material_start_turns,
            "material_end_turns": data.material_end_turns,
            "water_start_turns": data.water_start_turns,
            "washing_stop_turns": data.washing_stop_turns,
        }


class EditNavigationRequest(BaseModel):
    point: str
    frequency_hz: float = 5.0
    brush_frequency_hz: float = 15.0


@router.post("/calibration/edit/start", response_model=CalibrationSessionResponse)
async def start_saved_calibration_edit(request: CalibrationStartRequest):
    await get_enabled_material_profile(request.material_profile_id)
    operation = get_machine_operation_service()
    service = get_calibration_session_service()
    async with AsyncSessionLocal() as db:
        machine = (await db.execute(select(Machine).where(Machine.is_active.is_(True)))).scalars().first()
        if machine is None:
            raise HTTPException(status_code=404, detail="Active machine not found")
        try:
            data = await CalibrationRepository().load(db, machine.id, request.material_profile_id)
            if data.water_start_turns is None:
                raise ValueError("Saved Water Start is missing")
            with operation._mode_lock:
                operation.set_calibration_mode(request.material_profile_id)
                service.start_edit(request.material_profile_id, data)
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return build_calibration_session_response(service)


@router.post("/calibration/edit/navigate", response_model=CalibrationSessionResponse)
def navigate_saved_calibration(request: EditNavigationRequest):
    from app.services.machine.calibration.points import CalibrationPoint
    try:
        point = CalibrationPoint(request.point)
        get_calibration_session_service().edit_navigate(point, request.frequency_hz, request.brush_frequency_hz)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return build_calibration_session_response(get_calibration_session_service())


@router.post("/calibration/edit/adjust", response_model=CalibrationSessionResponse)
def begin_saved_point_adjustment():
    service = get_calibration_session_service()
    try:
        service.edit_begin_adjust()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return build_calibration_session_response(service)


@router.post("/calibration/edit/point", response_model=CalibrationSessionResponse)
def save_adjusted_point():
    service = get_calibration_session_service()
    try:
        service.edit_save_point()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return build_calibration_session_response(service)


@router.post("/calibration/edit/save")
async def commit_saved_calibration_edit():
    service = get_calibration_session_service()
    try:
        session = service.edit_prepare_commit()
        async with AsyncSessionLocal() as db:
            machine = (await db.execute(select(Machine).where(Machine.is_active.is_(True)))).scalars().first()
            if machine is None:
                raise RuntimeError("Active machine not found")
            await CalibrationRepository().save(db, machine.id, session)
            await db.commit()
        service.edit_mark_committed()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "saved", "position_preserved": True}


@router.post("/calibration/start", response_model=CalibrationSessionResponse)
async def start_calibration(request: CalibrationStartRequest):
    await get_enabled_material_profile(request.material_profile_id)

    operation_service = get_machine_operation_service()

    service = get_calibration_session_service()
    try:
        with operation_service._mode_lock:
            operation_service.set_calibration_mode(request.material_profile_id)
            service.start(request.material_profile_id)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return build_calibration_session_response(service)


@router.post("/calibration/finish-session")
def finish_calibration_session():
    service = get_calibration_session_service()
    try:
        service.finish_saved_session()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "finished"}


@router.post("/calibration/cancel")
def cancel_calibration():
    service = get_calibration_session_service()

    try:
        service.cancel()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    operation_service = get_machine_operation_service()
    operation_service.set_manual_mode()

    return {
        "status": "cancelled",
    }


@router.post(
    "/calibration/jog/forward",
    response_model=CalibrationSessionResponse,
)
def calibration_jog_forward(request: CalibrationJogRequest):
    service = get_calibration_session_service()

    try:
        service.jog_forward(request.frequency_hz, request.brush_frequency_hz)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return build_calibration_session_response(service)


@router.post("/calibration/jog/reverse", response_model=CalibrationSessionResponse)
def calibration_jog_reverse(request: CalibrationJogRequest):
    service = get_calibration_session_service()

    try:
        service.jog_reverse(request.frequency_hz, request.brush_frequency_hz)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return build_calibration_session_response(service)


@router.post("/calibration/next", response_model=CalibrationSessionResponse)
def calibration_next(request: CalibrationNextRequest):
    service = get_calibration_session_service()
    try:
        service.next_step(request.roller_frequency_hz, request.brush_frequency_hz)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return build_calibration_session_response(service)


@router.post("/calibration/auto-wind", response_model=CalibrationSessionResponse)
def calibration_auto_wind():
    service = get_calibration_session_service()
    try:
        service.start_auto_wind()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return build_calibration_session_response(service)


@router.post("/calibration/return-zero", response_model=CalibrationSessionResponse)
def calibration_return_zero():
    service = get_calibration_session_service()
    try:
        service.start_return_to_zero()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return build_calibration_session_response(service)


@router.post("/calibration/resume", response_model=CalibrationSessionResponse)
def calibration_resume(request: CalibrationNextRequest):
    service = get_calibration_session_service()
    try:
        service.resume_auto(request.brush_frequency_hz)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return build_calibration_session_response(service)


@router.post("/calibration/pause", response_model=CalibrationSessionResponse)
def calibration_pause():
    service = get_calibration_session_service()

    try:
        service.pause()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return build_calibration_session_response(service)


@router.post("/calibration/stop", response_model=CalibrationSessionResponse)
def calibration_stop():
    service = get_calibration_session_service()

    try:
        service.stop()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return build_calibration_session_response(service)


@router.post("/calibration/reset-position", response_model=CalibrationSessionResponse)
def calibration_reset_position():
    service = get_calibration_session_service()

    try:
        service.reset_position()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return build_calibration_session_response(service)


@router.post("/calibration/mark", response_model=CalibrationSessionResponse)
def mark_calibration_point(
    request: CalibrationMarkRequest,
):
    service = get_calibration_session_service()

    try:
        service.mark(request.point, request.brush_frequency_hz)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return build_calibration_session_response(service)


@router.post("/calibration/complete")
async def complete_calibration():
    service = get_calibration_session_service()

    try:
        calibration_session = service.complete()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    async with AsyncSessionLocal() as db:
        machine_result = await db.execute(
            select(Machine).where(Machine.is_active.is_(True))
        )
        machine = machine_result.scalars().first()

        if machine is None:
            raise HTTPException(
                status_code=404,
                detail="Active machine not found",
            )

        repository = CalibrationRepository()

        try:
            await repository.save(
                db=db,
                machine_id=machine.id,
                calibration_session=calibration_session,
            )

            await db.commit()
            service.mark_saved()

        except (ValueError, RuntimeError) as exc:
            await db.rollback()
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

    # Keep calibration mode and position tracker alive for optional auto winding.
    return {
        "status": "completed",
        "machine_id": machine.id,
        "material_profile_id": calibration_session.material_profile_id,
    }


@router.post(
    "/calibration/brush/start",
    response_model=CalibrationSessionResponse,
)
def calibration_brush_start(request: CalibrationJogRequest):
    service = get_calibration_session_service()

    try:
        service.start_brush(request.frequency_hz)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return build_calibration_session_response(service)


@router.post(
    "/calibration/brush/stop",
    response_model=CalibrationSessionResponse,
)
def calibration_brush_stop():
    service = get_calibration_session_service()

    try:
        service.stop_brush()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return build_calibration_session_response(service)


@router.get("/calibration/home")
def get_calibration_home():
    # Compatibility endpoint: shared HOME is the only source of reference state.
    return get_roller_homing_service().get_status()


@router.post("/calibration/home")
def start_calibration_home(request: CalibrationHomeRequest):
    raise HTTPException(
        status_code=409,
        detail="Use /api/machine/home for roller homing",
    )


# def start_calibration_home(request: CalibrationHomeRequest):
#     if settings.DRIVE_MODE != "fake":
#         raise HTTPException(
#             status_code=403,
#             detail="Homing is currently available only in fake mode",
#         )
#
#     service = get_calibration_session_service()
#
#     if not request.position_confirmed:
#         raise HTTPException(
#             status_code=400,
#             detail="Operator must confirm roller position within 0..1 revolution",
#         )
#
#     try:
#         service.start_homing(request.frequency_hz)
#     except (ValueError, RuntimeError) as exc:
#         raise HTTPException(status_code=400, detail=str(exc)) from exc
#
#     return {
#         "state": service.homing.state,
#         "error": service.homing.error,
#     }


@router.post("/calibration/home/cancel")
def cancel_calibration_home():
    raise HTTPException(
        status_code=409,
        detail="Use /api/machine/home for roller homing",
    )
    # service = get_calibration_session_service()
    #
    # if service.homing is None:
    #     raise HTTPException(status_code=400, detail="Homing is not configured")
    #
    # if service.homing.state == HomingState.SEARCHING:
    #     service.stop()
    #
    # return {
    #     "state": service.homing.state,
    #     "error": service.homing.error,
    # }


@router.get(
    "/auto/{stage}/speed",
    response_model=AutoSpeedSettingsResponse,
)
async def get_auto_speed_settings(stage: AutoStage):
    service = AutoSpeedSettingsService()

    try:
        async with AsyncSessionLocal() as session:
            settings = await service.load(
                session=session,
                machine_id=1,
                stage=stage,
            )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return AutoSpeedSettingsResponse(
        stage=settings.stage,
        speed_percent=settings.mode_speed_percent,
        brush_speed_percent=settings.brush_speed_percent,
    )


@router.put(
    "/auto/{stage}/speed",
    response_model=AutoSpeedSettingsResponse,
)
async def set_auto_speed(
    stage: AutoStage,
    request: AutoSpeedRequest,
):
    service = AutoSpeedSettingsService()

    try:
        async with AsyncSessionLocal() as session:
            settings = await service.set_mode_speed(
                session=session,
                machine_id=1,
                stage=stage,
                speed_percent=request.speed_percent,
            )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return AutoSpeedSettingsResponse(
        stage=settings.stage,
        speed_percent=settings.mode_speed_percent,
        brush_speed_percent=settings.brush_speed_percent,
    )


@router.put(
    "/auto/{stage}/brush-speed",
    response_model=AutoSpeedSettingsResponse,
)
async def set_auto_brush_speed(
    stage: AutoStage,
    request: AutoSpeedRequest,
):
    service = AutoSpeedSettingsService()

    try:
        async with AsyncSessionLocal() as session:
            settings = await service.set_brush_speed(
                session=session,
                machine_id=1,
                stage=stage,
                speed_percent=request.speed_percent,
            )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return AutoSpeedSettingsResponse(
        stage=settings.stage,
        speed_percent=settings.mode_speed_percent,
        brush_speed_percent=settings.brush_speed_percent,
    )


# -------------------------------------------------
# AUTO SESSION
# -------------------------------------------------


def require_fake_auto():
    if settings.DRIVE_MODE != "fake":
        raise HTTPException(
            status_code=403,
            detail="AUTO HTTP control is currently enabled only in fake mode",
        )


@router.get("/auto/session")
def get_auto_session():
    service = get_auto_session_service()
    return service.get_status()


@router.post("/auto/prepare")
async def prepare_auto():
    require_fake_auto()
    service = get_auto_session_service()

    try:
        async with AsyncSessionLocal() as session:
            await service.prepare(session=session)
    except (ValueError, RuntimeError, NotImplementedError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return service.get_status()


@router.post("/auto/start")
def start_auto():
    require_fake_auto()
    service = get_auto_session_service()

    try:
        service.start()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return service.get_status()


@router.post("/auto/pause")
def pause_auto():
    require_fake_auto()
    service = get_auto_session_service()

    try:
        service.pause()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return service.get_status()


@router.post("/auto/resume")
def resume_auto():
    require_fake_auto()
    service = get_auto_session_service()

    try:
        service.resume()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return service.get_status()


@router.post("/auto/stop")
def stop_auto():
    require_fake_auto()
    service = get_auto_session_service()

    try:
        service.stop()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return service.get_status()


# -------------------------------------------------
# emulatod microbutton start0point
# -------------------------------------------------


@router.get("/sensors/roller-reference")
def get_roller_reference():
    from app.main import roller_reference_sensor

    if roller_reference_sensor is None:
        raise HTTPException(status_code=503, detail="Sensor is not initialized")

    return roller_reference_sensor.read()


class IOOutputRequest(BaseModel):
    enabled: bool


@router.put("/io/{device}")
def set_io_output(device: str, request: IOOutputRequest):
    from app.main import machine_io_controller

    if device not in ("water", "light"):
        raise HTTPException(
            status_code=404,
            detail=f"Unknown IO device: {device}",
        )

    if machine_io_controller is None:
        raise HTTPException(
            status_code=503,
            detail="Machine IO controller is unavailable",
        )

    try:
        machine_io_controller.set_output(
            device=device,
            enabled=request.enabled,
        )

    except TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    return {
        "device": device,
        "requested": request.enabled,
        "status": "command_confirmed",
    }


@router.get("/io/diagnostics")
def get_io_diagnostics():
    from app.main import machine_io_controller

    if machine_io_controller is None:
        raise HTTPException(
            status_code=503,
            detail="Machine IO controller is unavailable",
        )

    return machine_io_controller.status()


@router.post("/sensors/roller-reference/test-pause")
def test_pause_roller_reference(duration_ms: int = 1000):
    if settings.DRIVE_MODE != "fake":
        raise HTTPException(
            status_code=403,
            detail="Test PAUSE is disabled in real drive mode",
        )

    from app.main import roller_reference_sensor
    from app.services.machine.sensors.serial_reference import (
        SerialRollerReferenceSensor,
    )

    if not isinstance(roller_reference_sensor, SerialRollerReferenceSensor):
        raise HTTPException(
            status_code=409,
            detail="Serial reference sensor is not active",
        )

    try:
        roller_reference_sensor.send_test_pause(duration_ms)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "status": "sent",
        "command": f"PAUSE {duration_ms}",
        "sensor": roller_reference_sensor.read(),
    }


@router.post("/sensors/roller-reference/fake")
def set_fake_roller_reference(request: FakeReferenceRequest):
    if settings.DRIVE_MODE != "fake":
        raise HTTPException(
            status_code=403,
            detail="Fake sensor control is disabled in real mode",
        )

    from app.main import roller_reference_sensor

    if roller_reference_sensor is None:
        raise HTTPException(status_code=503, detail="Sensor is not initialized")

    if not isinstance(roller_reference_sensor, FakeRollerReferenceSensor):
        raise HTTPException(
            status_code=409,
            detail="Fake sensor controls are unavailable in serial mode",
        )

    roller_reference_sensor.set_triggered(request.triggered)

    return roller_reference_sensor.read()


@router.post("/sensors/roller-reference/fake/connection")
def set_fake_roller_reference_connection(
    request: FakeReferenceConnectionRequest,
):
    if settings.DRIVE_MODE != "fake":
        raise HTTPException(
            status_code=403,
            detail="Fake sensor control is disabled in real mode",
        )

    from app.main import roller_reference_sensor

    if roller_reference_sensor is None:
        raise HTTPException(
            status_code=503,
            detail="Sensor is not initialized",
        )

    if not isinstance(roller_reference_sensor, FakeRollerReferenceSensor):
        raise HTTPException(
            status_code=409,
            detail="Fake sensor controls are unavailable in serial mode",
        )

    roller_reference_sensor.set_connected(request.connected)
    return roller_reference_sensor.read()


class CalibrationGeometryRequest(BaseModel):
    final_diameter_mm: float


@router.post("/calibration/geometry")
async def save_calibration_geometry(
    request: CalibrationGeometryRequest,
):
    from math import isfinite

    service = get_calibration_session_service()

    if not service.active or not service.saved:
        raise HTTPException(
            status_code=409,
            detail="Save positional calibration first",
        )

    calibration = service.get_current()

    try:
        calibration = service.require_geometry_ready()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if not isfinite(request.final_diameter_mm):
        raise HTTPException(
            status_code=422,
            detail="Final diameter must be finite",
        )

    async with AsyncSessionLocal() as db:
        machine = (
            (await db.execute(select(Machine).where(Machine.is_active.is_(True))))
            .scalars()
            .first()
        )

        if machine is None:
            raise HTTPException(
                status_code=404,
                detail="Active machine not found",
            )

        repository = CalibrationRepository()

        try:
            thickness = await repository.save_geometry(
                db=db,
                machine_id=machine.id,
                material_profile_id=calibration.material_profile_id,
                final_diameter_mm=request.final_diameter_mm,
            )
            await db.commit()
        except (ValueError, RuntimeError) as exc:
            await db.rollback()
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

    service.mark_geometry_saved()

    return {
        "status": "saved",
        "material_profile_id": calibration.material_profile_id,
        "final_diameter_mm": request.final_diameter_mm,
        "material_thickness_mm": thickness,
    }


################################################################
# Homing routes
################################################################


class Point0JogRequest(BaseModel):
    direction: str
    frequency_hz: float = 5.0


_point0_jog_service = None


def get_point0_jog_service():
    global _point0_jog_service
    from app.services.machine.point0_jog_service import Point0JogService
    operation = get_machine_operation_service()
    if _point0_jog_service is None or _point0_jog_service.machine is not operation.machine:
        _point0_jog_service = Point0JogService(operation.machine)
    return _point0_jog_service


def require_point0_idle_sessions():
    operation = get_machine_operation_service()
    if get_calibration_session_service().active:
        raise RuntimeError('Finish CALIBRATION session before Point0 positioning')
    if get_auto_session_service().get_status()['status'] != 'IDLE':
        raise RuntimeError('Finish AUTO session before Point0 positioning')
    if operation.state.running or operation.state.paused or operation.state.roller_running or operation.state.brush_running:
        raise RuntimeError('Stop current machine operation before Point0 positioning')
    home = get_roller_homing_service()
    if home.searching or home.get_status().get('awaiting_stop_confirmation') or home.faulted:
        raise RuntimeError('HOME is active or faulted')


@router.get('/point0/jog')
def point0_jog_status():
    return get_point0_jog_service().status()


@router.post('/point0/jog')
def point0_jog_start(request: Point0JogRequest):
    operation = get_machine_operation_service()
    try:
        with operation._mode_lock:
            require_point0_idle_sessions()
            # Any positioning pulse invalidates the previous zero reference.
            get_roller_homing_service().invalidate()
            return get_point0_jog_service().start(request.direction, request.frequency_hz)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post('/point0/jog/stop')
def point0_jog_stop():
    try:
        return get_point0_jog_service().stop()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/home")
def get_roller_home():
    service = get_roller_homing_service()
    return service.get_status()


@router.post("/home")
def start_roller_home(request: RollerHomeRequest):
    service = get_roller_homing_service()
    operation = get_machine_operation_service()

    try:
        # Selecting AUTO/CALIBRATION is fine; an active work session is not.
        if get_calibration_session_service().active:
            raise RuntimeError("Finish CALIBRATION session before Point0 HOME")
        if get_auto_session_service().get_status()["status"] != "IDLE":
            raise RuntimeError("Finish AUTO session before Point0 HOME")
        jog = get_point0_jog_service().status()
        if jog['active'] or jog['stopping'] or jog['owner'] == 'point0':
            raise RuntimeError('Finish Point0 positioning and confirm STOP before HOME')
        operation.start_home(
            service,
            position_confirmed=request.position_confirmed,
            frequency_hz=request.frequency_hz,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    return service.get_status()


@router.post("/home/acknowledge-fault")
def acknowledge_roller_home_fault(operator_confirmed_stopped: bool = False):
    """Operator acknowledgement after physical E-stop release and VFD RESET.

    This endpoint never resets the drive or starts movement.
    """
    service = get_roller_homing_service()
    try:
        service.acknowledge_fault(operator_confirmed_stopped=operator_confirmed_stopped)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return service.get_status()


@router.post("/home/cancel")
def cancel_roller_home():
    service = get_roller_homing_service()

    try:
        service.cancel()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    return service.get_status()

@router.get("/readiness")
def get_machine_readiness():
    """Read-only snapshot. Does not authorize motion or reset faults."""
    from app.services.machine.readiness_diagnostics import get_readiness_snapshot

    from app.main import machine as active_machine

    return get_readiness_snapshot(
        get_drive_service(), get_roller_homing_service(),
        motion_fault_reason=(active_machine.motion_fault_latched if active_machine is not None else "Machine not initialized"),
    )


@router.get("/motion-fault")
def get_motion_fault_diagnostics():
    """Read-only software latch diagnostics; does not authorize motion."""
    from app.main import machine as active_machine, motion_fault_runtime

    if active_machine is None:
        raise HTTPException(status_code=503, detail="Machine is not initialized")
    reason = active_machine.motion_fault_latched
    runtime = motion_fault_runtime
    from app.main import auto_session_service, calibration_session_service, roller_homing_service
    services_available = (settings.DRIVE_MODE == "real" and runtime is not None
                          and all(service is not None for service in (
                              auto_session_service, calibration_session_service, roller_homing_service)))
    recovery_available = bool(reason is not None and services_available)
    return {
        "latched": reason is not None,
        "reason": reason,
        "monitor_running": runtime.running if runtime is not None else False,
        "last_poll_error": runtime.last_poll_error if runtime is not None else None,
        "monitor_last_fault": runtime.last_fault if runtime is not None else None,
        "last_notification_error": getattr(runtime, "last_notification_error", None),
        "recovery_available": recovery_available,
        "recovery_note": ("Acknowledgement endpoint is available; physical RESET, operator confirmation "
                          "and stopped-drive verification are still required" if recovery_available
                          else "Recovery endpoint unavailable or no software fault latched"),
        "diagnostic_only": True,
    }


class MotionFaultAcknowledgeRequest(BaseModel):
    operator_confirmed_stopped: bool


@router.post("/motion-fault/acknowledge")
async def acknowledge_motion_fault(request: MotionFaultAcknowledgeRequest):
    """Software acknowledgement only; physical E-STOP/RESET is independent."""
    from app.main import machine, motion_fault_runtime
    from app.services.machine.motion_fault_recovery import MotionFaultRecoveryService
    from app.main import drive_service, auto_session_service, calibration_session_service, roller_homing_service

    if settings.DRIVE_MODE != "real" or any(s is None for s in (
        machine, motion_fault_runtime, auto_session_service, calibration_session_service, roller_homing_service
    )):
        raise HTTPException(status_code=503, detail="Real recovery services unavailable")
    recovery = MotionFaultRecoveryService(machine, drive_service, auto_session_service,
                                          calibration_session_service, roller_homing_service)
    try:
        result = await motion_fault_runtime.acknowledge_exclusive(
            recovery, operator_confirmed_stopped=request.operator_confirmed_stopped
        )
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"acknowledged": True, "drives_verified": result.drive_ids,
            "stop_samples": result.consecutive_stop_samples, "homed": False,
            "automatic_restart": False}
