# 29Е.3 — интеграция обработчиков аварии

Три теста используют настоящие классы Machine, MotionFaultRuntime, AutoSessionService,
CalibrationSessionService и RollerHomingService, но имитируют аппаратные приводы.

- Ошибка команды RUN приводит к persistent latch и уведомлению всех сценариев.
- Сбой обработчика AUTO не мешает CALIBRATION и HOME получить аварию.
- Подготовленный AUTO запрещает программное завершение восстановления; автоматический RUN не выполняется.

Ограничения: тесты не проверяют физическую остановку, аппаратную E-STOP или
все возможные межпоточные расписания. Проверка `complete_motion_fault_recovery`
не является выполнением полного HTTP acknowledge.

Запуск:

```bash
docker compose exec backend python -m pytest -q tests/test_motion_fault_integrated_sessions.py
docker compose exec backend python -m pytest -q
```
