from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.machine_calibration import MachineCalibrationSettings
from app.models.winding_calibration import WindingCalibration as WindingCalibrationModel
from app.services.machine.calibration.session import CalibrationSession
from app.services.machine.calibration.data import CalibrationData
from app.models.winding_parameters import WindingParameters
from app.services.winding.thickness import MaterialThicknessCalculator
from app.models.machine import Machine


class CalibrationRepository:
    async def save(
        self,
        db: AsyncSession,
        machine_id: int,
        calibration_session: CalibrationSession,
    ) -> None:
        calibration_session.validate()

        await self._save_machine_calibration(
            db=db,
            machine_id=machine_id,
            calibration_session=calibration_session,
        )

        await self._save_winding_calibration(
            db=db,
            calibration_session=calibration_session,
        )

    async def load(
        self,
        db: AsyncSession,
        machine_id: int,
        material_profile_id: int,
    ) -> CalibrationData:
        machine_result = await db.execute(
            select(MachineCalibrationSettings).where(
                MachineCalibrationSettings.machine_id == machine_id
            )
        )

        machine_calibration = machine_result.scalar_one_or_none()

        if machine_calibration is None:
            raise RuntimeError("Machine calibration not found")

        winding_result = await db.execute(
            select(WindingCalibrationModel).where(
                WindingCalibrationModel.material_profile_id == material_profile_id
            )
        )

        winding_calibration = winding_result.scalar_one_or_none()

        if winding_calibration is None:
            raise RuntimeError("Material calibration not found")

        if machine_calibration.washing_stop_turns is None:
            raise RuntimeError("Washing stop point is not calibrated")

        if machine_calibration.material_start_turns is None:
            raise RuntimeError("Material start point is not calibrated")

        if winding_calibration.material_end_turns is None:
            raise RuntimeError("Material end point is not calibrated")

        return CalibrationData(
            machine_id=machine_id,
            material_profile_id=material_profile_id,
            washing_stop_turns=machine_calibration.washing_stop_turns,
            material_start_turns=machine_calibration.material_start_turns,
            material_end_turns=winding_calibration.material_end_turns,
            water_start_turns=machine_calibration.water_start_turns,
        )

    async def _save_machine_calibration(
        self,
        db: AsyncSession,
        machine_id: int,
        calibration_session: CalibrationSession,
    ) -> None:
        result = await db.execute(
            select(MachineCalibrationSettings).where(
                MachineCalibrationSettings.machine_id == machine_id
            )
        )

        model = result.scalar_one_or_none()

        if model is None:
            model = MachineCalibrationSettings(machine_id=machine_id)
            db.add(model)

        model.material_start_turns = (
            calibration_session.machine_calibration.material_start_turns
        )
        model.washing_stop_turns = (
            calibration_session.machine_calibration.washing_stop_turns
        )
        model.water_start_turns = (
            calibration_session.machine_calibration.water_start_turns
        )

    async def _save_winding_calibration(
        self,
        db: AsyncSession,
        calibration_session: CalibrationSession,
    ) -> None:
        material_profile_id = calibration_session.material_profile_id

        result = await db.execute(
            select(WindingCalibrationModel).where(
                WindingCalibrationModel.material_profile_id == material_profile_id
            )
        )

        model = result.scalar_one_or_none()

        if model is None:
            model = WindingCalibrationModel(material_profile_id=material_profile_id)
            db.add(model)

        model.material_end_turns = (
            calibration_session.winding_calibration.material_end_turns
        )

    async def save_geometry(
        self,
        db: AsyncSession,
        machine_id: int,
        material_profile_id: int,
        final_diameter_mm: float,
    ) -> float:

        machine = await db.get(Machine, machine_id)
        if machine is None:
            raise RuntimeError("Machine not found")

        core_diameter_mm = machine.roller_core_diameter_mm
        if core_diameter_mm is None or core_diameter_mm <= 0:
            raise ValueError("Invalid roller core diameter")

        machine_calibration = (
            await db.execute(
                select(MachineCalibrationSettings).where(
                    MachineCalibrationSettings.machine_id == machine_id
                )
            )
        ).scalar_one_or_none()

        winding_calibration = (
            await db.execute(
                select(WindingCalibrationModel).where(
                    WindingCalibrationModel.material_profile_id == material_profile_id
                )
            )
        ).scalar_one_or_none()

        if machine_calibration is None or winding_calibration is None:
            raise RuntimeError("Save positional calibration first")

        start = machine_calibration.material_start_turns
        end = winding_calibration.material_end_turns

        if start is None or end is None or end <= start:
            raise ValueError("Invalid material calibration points")

        turns = end - start

        thickness = MaterialThicknessCalculator(
            core_diameter_mm=core_diameter_mm
        ).calculate(
            final_diameter_mm=final_diameter_mm,
            turns=turns,
        )

        parameters = (
            await db.execute(
                select(WindingParameters).where(
                    WindingParameters.material_profile_id == material_profile_id
                )
            )
        ).scalar_one_or_none()

        if parameters is None:
            parameters = WindingParameters(material_profile_id=material_profile_id)
            db.add(parameters)

        parameters.core_diameter_mm = core_diameter_mm
        parameters.material_thickness_mm = thickness
        parameters.calibration_turns = turns
        parameters.calibration_final_diameter_mm = final_diameter_mm

        await db.flush()
        return thickness
