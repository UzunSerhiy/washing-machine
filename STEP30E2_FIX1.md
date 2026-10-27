# Шаг 30Е.2 — исправление тестовых двойников и проверки поколений AUTO

Исправлен `FakePhysicalMachine`: реализован контракт `capture_session_generation`, `require_session_generation`, передача `session_generation` при RUN и имитация fault/recovery с увеличением поколения. В четырёх тестах аварийного RUN обновлены подменяемые функции, чтобы принимать новый именованный параметр.

Добавлены четыре теста: stale start, stale resume, stale tick, fault во время async prepare. Тесты не обращаются к оборудованию.

## Установка

```bash
unzip -o ~/Downloads/washing-machine-step30e2-fix1.zip -d .
docker compose exec backend python -m pytest -q tests/services/machine/auto/test_session_service.py tests/services/machine/auto/test_home_lifecycle.py tests/services/machine/auto/test_step30e2_session_epoch.py
docker compose exec backend python -m pytest -q
```

Ожидается 879 тестов (875 + 4), если другие файлы не менялись.

Локально: 45 существующих тестов AUTO/HOME и 4 новых пройдены. Полный набор локально не запускается из-за отсутствия `pymodbus` и `asyncpg`; проверить в Docker. Коммит не делать до полного прогона.

Важно: AUTO-исправление не покрывает HOME и CALIBRATION. Программные тесты не заменяют аппаратные interlock/E-STOP и не разрешают испытания вращения валов.
