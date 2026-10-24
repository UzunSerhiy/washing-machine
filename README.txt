ЭТАП 1 — water_start_turns (backend only)

Из корня ~/Projects/washing-machine:
  cp -a backend backend.backup-water-stage1
  unzip -o /путь/к/washing-water-stage1.zip
  docker compose exec -T backend alembic current
  docker compose exec -T backend alembic upgrade head
  docker compose exec -T backend python -m compileall -q app

ПРИМЕЧАНИЯ:
- Включение воды автоматически НЕ реализовано на этом этапе.
- Точка необязательна для старых записей; перед включением AUTO с водой нужна отдельная проверка, что она задана.
- CalibrationSession.set_point(WATER_START) принимает точку в READY_TO_UNWIND при остановленном роллере.
- Для реального UI и API понадобится обновить текущий обработчик mark, сериализацию статуса и кнопку в calibration/page.tsx.
- Не запускайте AUTO с новой логикой воды до следующего этапа.
