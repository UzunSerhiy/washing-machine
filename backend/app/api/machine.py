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
        brush_running=session.player.brush_running,
        brush_frequency_hz=session.player.brush_frequency_hz,
        stage=session.stage,
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

    return build_calibration_session_response(service)


@router.post("/calibration/start", response_model=CalibrationSessionResponse)
async def start_calibration(request: CalibrationStartRequest):
    await get_enabled_material_profile(request.material_profile_id)

    operation_service = get_machine_operation_service()

    try:
        operation_service.set_calibration_mode(
            request.material_profile_id,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    service = get_calibration_session_service()

    try:
        service.start(request.material_profile_id)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return build_calibration_session_response(service)


@router.post("/calibration/cancel")
def cancel_calibration():
    service = get_calibration_session_service()

    service.cancel()

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
        service.jog_forward(request.frequency_hz)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return build_calibration_session_response(service)


@router.post("/calibration/jog/reverse", response_model=CalibrationSessionResponse)
def calibration_jog_reverse(request: CalibrationJogRequest):
    service = get_calibration_session_service()

    try:
        service.jog_reverse(request.frequency_hz)
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
        service.mark(request.point)
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
            service.finish()

        except (ValueError, RuntimeError) as exc:
            await db.rollback()
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

    operation_service = get_machine_operation_service()
    operation_service.set_manual_mode()

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
    service = get_calibration_session_service()

    if service.homing is None:
        return {"available": False, "state": None, "error": None}

    return {
        "available": True,
        "state": service.homing.state,
        "error": service.homing.error,
    }


@router.post("/calibration/home")
def start_calibration_home(request: CalibrationHomeRequest):
    if settings.DRIVE_MODE != "fake":
        raise HTTPException(
            status_code=403,
            detail="Homing is currently available only in fake mode",
        )

    service = get_calibration_session_service()

    if not request.position_confirmed:
        raise HTTPException(
            status_code=400,
            detail="Operator must confirm roller position within 0..1 revolution",
        )

    try:
        service.start_homing(request.frequency_hz)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "state": service.homing.state,
        "error": service.homing.error,
    }


@router.post("/calibration/home/cancel")
def cancel_calibration_home():
    service = get_calibration_session_service()

    if service.homing is None:
        raise HTTPException(status_code=400, detail="Homing is not configured")

    if service.homing.state == HomingState.SEARCHING:
        service.stop()

    return {
        "state": service.homing.state,
        "error": service.homing.error,
    }


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

    roller_reference_sensor.set_connected(request.connected)
    return roller_reference_sensor.read()
