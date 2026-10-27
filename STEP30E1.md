# Шаг 30Е.1 — атомарный барьер поколения сессии

Это инфраструктурный патч, **не завершённая защита AUTO/HOME/CALIBRATION**.

- `capture_session_generation()` создаёт токен при отсутствии аварийной блокировки.
- `require_session_generation()` проверяет токен.
- `start_brush`, `start_roller_forward`, `start_roller_reverse` принимают необязательный `session_generation`.
- Проверка токена и отправка RUN выполняются под одной блокировкой Machine.
- Старый токен не становится действительным после успешного acknowledge.

В этом подэтапе существующие вызовы AUTO/HOME/CALIBRATION ещё не передают токен.
Следующий подэтап должен привязать токены к жизненному циклу каждой операции,
проверить ожидания и исключить повторное создание токена старой сессией.

## Проверка

```bash
docker compose exec backend python -m pytest -q tests/test_step30e1_session_epoch_gate.py
docker compose exec backend python -m pytest -q
```

Только моки. Не проверять на вращающихся валах.
