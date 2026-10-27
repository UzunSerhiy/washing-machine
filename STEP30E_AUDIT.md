# Шаг №30Е — аудит защиты длительных операций (v41)

Статус: аудит; **не патч безопасности**. Изменений рабочего кода нет.

## Проверено в исходниках

- `backend/app/services/machine/machine.py`: `_motion_ticket()` берётся на входе в `start_brush`, `start_roller_forward`, `start_roller_reverse`; `_execute_motion()` сравнивает поколение под `_roller_lock`. Защита действует на отдельный вызов RUN.
- `backend/app/services/machine/auto/session_service.py`: `prepare()` — асинхронная операция, `start()` вызывает `prepared.controller.apply()`, `tick()` — `prepared.controller.update()`. У `PreparedAutoStage` отсутствует привязка к поколению аварии.
- `backend/app/services/machine/roller_homing_service.py`: `start()` меняет состояние HOME, затем вызывает `machine.start_roller_reverse()`; локальная синхронизация `_state_lock` не является тем же lock, что `_roller_lock` машины.
- `backend/app/services/machine/calibration/session_service.py`: есть `_motion_fault` и методы `start()`, `start_auto_wind()`; нет единого session generation token.
- `backend/app/services/machine/calibration/player.py`: jog и brush вызывают отдельные методы `Machine`, каждый получает новый ticket.

## Риск

Старый автоматический сценарий может инициировать *новый* вызов `Machine.start_*` после успешного подтверждения аварии и получить новое поколение, несмотря на то что сценарий был подготовлен до аварии. Поэтому защита №30Д для ручных RUN не доказывает безопасность AUTO/HOME/CALIBRATION.

## Требования к патчу

1. Привязывать каждую подготовленную/запущенную автоматическую сессию к поколению `Machine`.
2. Проверять токен сессии на каждом переходе и перед каждым движением; не создавать новый токен для старого сценария.
3. Согласовать порядок блокировок и исключить дедлоки между HOME, Machine и восстановлением.
4. После аварии очищать/инвалидировать сессии; после подтверждения требовать новую команду оператора.
5. Проверять `prepare` с `await`, `start`, `tick`, HOME `start/tick`, CALIBRATION jog/auto, паузу/возобновление, повторную аварию.
6. Тестировать на mock-приводах и гонках; не проводить аппаратные RUN до закрытия риска.

Следующий этап: реализация атомарного session-generation контракта и интеграционных тестов, с полным прогоном существующих 867 тестов.
